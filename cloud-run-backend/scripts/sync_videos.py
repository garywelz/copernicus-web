#!/usr/bin/env python3
"""
Sync Videos from Science Video Database to Firestore

Reads videos from the Science Video Database PostgreSQL,
generates embeddings from transcripts, and syncs them to CopernicusAI Firestore.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from services.embedding_service import get_embedding_service
from utils.logging import structured_logger
import logging

logger = logging.getLogger(__name__)

# Try to import psycopg2 for PostgreSQL connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 not available. Install with: pip install psycopg2-binary")


def get_database_url() -> str:
    """Get database URL from environment or Secrets Manager."""
    # Try environment variable first
    database_url = os.getenv("SCIENCEVIDDB_DATABASE_URL")
    if database_url:
        return database_url
    
    # Try Secrets Manager
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = "regal-scholar-453620-r7"
        secret_name = f"projects/{project_id}/secrets/scienceviddb-database-url/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"Could not get database URL from Secrets Manager: {e}")
        raise ValueError("SCIENCEVIDDB_DATABASE_URL environment variable not set and Secrets Manager access failed")


def get_all_videos(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all videos from Science Video Database."""
    if not PSYCOPG2_AVAILABLE:
        raise ImportError("psycopg2 is required to access Science Video Database")
    
    database_url = get_database_url()
    
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    v.id,
                    v.source_id,
                    v.source,
                    v.title,
                    v.description,
                    v.published_at,
                    v.duration,
                    v.view_count,
                    v.thumbnail_url,
                    v.video_url,
                    v.disciplines,
                    v.tags,
                    v.transcript_available,
                    v.metadata,
                    c.channel_name,
                    c.channel_url,
                    c.channel_id as youtube_channel_id
                FROM videos v
                JOIN channels c ON v.channel_id = c.id
                ORDER BY v.published_at DESC
            """
            if limit:
                query += f" LIMIT {limit}"
            
            cur.execute(query)
            videos = [dict(row) for row in cur.fetchall()]
            return videos
    finally:
        conn.close()


def get_video_transcript(video_id: str) -> str:
    """Get transcript text for a video."""
    database_url = get_database_url()
    
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT text, start_time, end_time
                FROM transcript_segments
                WHERE video_id = %s
                ORDER BY start_time ASC
            """, (video_id,))
            
            segments = cur.fetchall()
            # Combine segments into full transcript
            transcript = " ".join([seg['text'] for seg in segments])
            return transcript
    finally:
        conn.close()


def convert_video_to_firestore_format(video: Dict[str, Any], transcript: Optional[str] = None) -> Dict[str, Any]:
    """Convert PostgreSQL video to Firestore format."""
    return {
        "video_id": video["id"],
        "source_id": video["source_id"],
        "source": video["source"],
        "title": video["title"],
        "description": video.get("description") or "",
        "published_at": video["published_at"].isoformat() if video.get("published_at") else None,
        "duration": video.get("duration"),
        "view_count": video.get("view_count"),
        "thumbnail_url": video.get("thumbnail_url"),
        "video_url": video.get("video_url"),
        "disciplines": video.get("disciplines") or [],
        "tags": video.get("tags") or [],
        "transcript_available": video.get("transcript_available", False),
        "transcript": transcript or "",
        "channel_name": video.get("channel_name"),
        "channel_url": video.get("channel_url"),
        "youtube_channel_id": video.get("youtube_channel_id"),
        "metadata": video.get("metadata") or {},
        "created_at": datetime.utcnow().isoformat(),
    }


def create_text_for_video_embedding(video_data: Dict[str, Any]) -> str:
    """Create text representation of video for embedding."""
    parts = []
    
    if video_data.get("title"):
        parts.append(video_data["title"])
    
    if video_data.get("description"):
        parts.append(video_data["description"])
    
    if video_data.get("transcript"):
        # Use first 2000 chars of transcript to stay within token limits
        parts.append(video_data["transcript"][:2000])
    
    if video_data.get("disciplines"):
        parts.append(f"Disciplines: {', '.join(video_data['disciplines'])}")
    
    if video_data.get("tags"):
        parts.append(f"Tags: {', '.join(video_data['tags'][:10])}")  # First 10 tags
    
    return "\n".join(parts)


def sync_videos(
    dry_run: bool = False,
    limit: Optional[int] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Sync videos from Science Video Database to Firestore.
    
    Args:
        dry_run: If True, don't actually write to Firestore
        limit: Maximum number of videos to sync (None for all)
        skip_existing: Skip videos that already exist in Firestore
    
    Returns:
        Dictionary with sync statistics
    """
    stats = {
        "total_in_postgres": 0,
        "already_in_firestore": 0,
        "synced": 0,
        "failed": 0,
        "with_transcripts": 0,
        "with_embeddings": 0,
        "errors": []
    }
    
    # Initialize Firestore client
    try:
        # Get GCP project ID from environment or use default
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        firestore_db = firestore.Client(project=gcp_project_id, database="copernicusai")
        print(f"✅ Connected to Firestore (project: {gcp_project_id}, database: copernicusai)")
    except Exception as e:
        print(f"❌ Failed to initialize Firestore: {e}")
        print("   Make sure GCP credentials are set up correctly")
        sys.exit(1)
    
    # Get embedding service
    try:
        embedding_service = get_embedding_service()
        embedding_available = True
    except Exception as e:
        logger.warning(f"Embedding service not available: {e}")
        embedding_service = None
        embedding_available = False
        print("⚠️  Embedding service not available. Videos will be synced without embeddings.")
    
    try:
        # Get all videos from PostgreSQL
        print("📹 Fetching videos from Science Video Database...")
        videos = get_all_videos(limit=limit)
        stats["total_in_postgres"] = len(videos)
        
        print(f"\n📊 Found {stats['total_in_postgres']} videos")
        print(f"   Dry run: {dry_run}")
        print(f"   Limit: {limit or 'None (all)'}")
        print(f"   Skip existing: {skip_existing}\n")
        
        # Check existing videos in Firestore
        firestore_videos_ref = firestore_db.collection('science_videos')
        existing_video_ids = set()
        
        if skip_existing:
            print("🔍 Checking existing videos in Firestore...")
            for doc in firestore_videos_ref.stream():
                existing_video_ids.add(doc.id)
            print(f"   Found {len(existing_video_ids)} existing videos\n")
        
        # Sync each video
        for i, video in enumerate(videos, 1):
            video_id = video["id"]
            
            # Skip if already exists
            if skip_existing and video_id in existing_video_ids:
                stats["already_in_firestore"] += 1
                if i % 20 == 0:
                    print(f"   Progress: {i}/{len(videos)} (skipped {stats['already_in_firestore']} existing)")
                continue
            
            try:
                # Get transcript if available
                transcript = None
                if video.get("transcript_available"):
                    try:
                        transcript = get_video_transcript(video_id)
                        if transcript:
                            stats["with_transcripts"] += 1
                    except Exception as e:
                        logger.warning(f"Could not get transcript for video {video_id}: {e}")
                
                # Convert to Firestore format
                video_data = convert_video_to_firestore_format(video, transcript=transcript)
                
                # Generate embedding
                has_embedding = False
                if embedding_available and embedding_service:
                    try:
                        text = create_text_for_video_embedding(video_data)
                        if text and text.strip():
                            embedding = embedding_service.embed_text(text)
                            if embedding:
                                # Convert to Vector type for Firestore vector search
                                from google.cloud.firestore_v1.vector import Vector
                                video_data["embedding"] = Vector(embedding)
                                video_data["embedding_model"] = "text-embedding-004"
                                video_data["embedding_updated"] = datetime.utcnow().isoformat()
                                has_embedding = True
                                stats["with_embeddings"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for video {video_id}: {e}")
                
                # Write to Firestore
                if not dry_run:
                    firestore_videos_ref.document(video_id).set(video_data)
                
                stats["synced"] += 1
                
                if i % 10 == 0:
                    status = "✅" if has_embedding else "⚠️"
                    print(f"   {status} Progress: {i}/{len(videos)} synced ({stats['synced']} new, {stats['already_in_firestore']} skipped)")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Video {video_id} ({video.get('title', 'Unknown')[:50]}): {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(f"Failed to sync video {video_id}", error=str(e))
                if stats["failed"] <= 5:  # Only print first 5 errors
                    print(f"   ❌ {error_msg}")
        
        print(f"\n✅ Sync complete!")
        print(f"   Total in PostgreSQL: {stats['total_in_postgres']}")
        print(f"   Already in Firestore: {stats['already_in_firestore']}")
        print(f"   Synced: {stats['synced']}")
        print(f"   With transcripts: {stats['with_transcripts']}")
        print(f"   With embeddings: {stats['with_embeddings']}")
        print(f"   Failed: {stats['failed']}")
        
        if stats["errors"] and len(stats["errors"]) > 5:
            print(f"\n⚠️  {len(stats['errors'])} errors occurred (showing first 5):")
            for error in stats["errors"][:5]:
                print(f"   - {error}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync videos from Science Video Database to Firestore")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to Firestore")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to sync")
    parser.add_argument("--no-skip-existing", action="store_true", help="Don't skip videos that already exist")
    parser.add_argument("--database-url", type=str, help="Science Video Database URL (or set SCIENCEVIDDB_DATABASE_URL env var)")
    
    args = parser.parse_args()
    
    if args.database_url:
        os.environ["SCIENCEVIDDB_DATABASE_URL"] = args.database_url
    
    print("="*70)
    print("VIDEO SYNC: Science Video Database → Firestore")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to Firestore\n")
    
    if not PSYCOPG2_AVAILABLE:
        print("\n❌ psycopg2 is required. Install with: pip install psycopg2-binary\n")
        return 1
    
    stats = sync_videos(
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=not args.no_skip_existing
    )
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to actually sync.")
    
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

