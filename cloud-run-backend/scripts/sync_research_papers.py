#!/usr/bin/env python3
"""
Sync Research Papers from PostgreSQL to Firestore

Reads papers from the research metadata PostgreSQL database,
generates embeddings, and syncs them to CopernicusAI Firestore.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add research metadata database to path
research_metadata_path = Path(__file__).parent.parent.parent / "copernicusai-research-metadata"
if research_metadata_path.exists():
    sys.path.insert(0, str(research_metadata_path))
else:
    # Try alternative path
    alt_path = Path("/home/gdubs/copernicusai-research-metadata")
    if alt_path.exists():
        sys.path.insert(0, str(alt_path))
    else:
        print(f"⚠️  Warning: Could not find copernicusai-research-metadata directory")
        print(f"   Tried: {research_metadata_path}")
        print(f"   Tried: {alt_path}")

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from utils.logging import structured_logger
import logging

logger = logging.getLogger(__name__)

# Try to import embedding service
try:
    from services.embedding_service import get_embedding_service
    EMBEDDING_SERVICE_AVAILABLE = True
except ImportError:
    EMBEDDING_SERVICE_AVAILABLE = False
    logger.warning("Embedding service not available, papers will be synced without embeddings")

# Import from research metadata database
# Note: This script should be run from the research metadata database directory
# or with its venv activated to have access to all dependencies
try:
    from app.core.database import SessionLocal
    from app.models.paper import Paper
except ImportError as e:
    print(f"❌ Error importing from research metadata database: {e}")
    print("   This script needs to be run from the copernicusai-research-metadata directory")
    print("   OR with its venv activated:")
    print("   cd /home/gdubs/copernicusai-research-metadata")
    print("   source venv/bin/activate")
    print("   python3 /home/gdubs/copernicus-web-public/cloud-run-backend/scripts/sync_research_papers.py")
    sys.exit(1)


def convert_paper_to_firestore_format(paper: Paper) -> Dict[str, Any]:
    """Convert PostgreSQL paper model to Firestore format."""
    return {
        "paper_id": str(paper.paper_id),
        "arxiv_id": paper.arxiv_id,
        "doi": paper.doi,
        "title": paper.title,
        "authors": paper.authors or [],
        "abstract": paper.abstract or "",
        "published_at": paper.published_at.isoformat() if paper.published_at else None,
        "categories": paper.categories or [],
        "sources": paper.sources or ["arxiv"],
        "ingested_at": paper.ingested_at.isoformat() if paper.ingested_at else None,
        "updated_at": paper.updated_at.isoformat() if paper.updated_at else None,
        "created_at": datetime.utcnow().isoformat(),
        "discipline": "mathematics" if paper.categories and any(cat.startswith("math.") for cat in paper.categories) else "other",
    }


def sync_papers(
    dry_run: bool = False,
    limit: Optional[int] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Sync papers from PostgreSQL to Firestore.
    
    Args:
        dry_run: If True, don't actually write to Firestore
        limit: Maximum number of papers to sync (None for all)
        skip_existing: Skip papers that already exist in Firestore
    
    Returns:
        Dictionary with sync statistics
    """
    stats = {
        "total_in_postgres": 0,
        "already_in_firestore": 0,
        "synced": 0,
        "failed": 0,
        "errors": []
    }
    
    # Get PostgreSQL database session
    db = SessionLocal()
    
    # Initialize Firestore client
    try:
        # Try to get GCP_PROJECT_ID from environment or config
        import os
        GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        firestore_db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    except Exception as e:
        print(f"❌ Failed to initialize Firestore: {e}")
        print("   Make sure you're running from cloud-run-backend directory with proper GCP credentials")
        sys.exit(1)
    
    try:
        # Get all papers from PostgreSQL
        query = db.query(Paper)
        if limit:
            query = query.limit(limit)
        
        papers = query.all()
        stats["total_in_postgres"] = len(papers)
        
        print(f"\n📊 Found {stats['total_in_postgres']} papers in PostgreSQL")
        print(f"   Dry run: {dry_run}")
        print(f"   Limit: {limit or 'None (all)'}")
        print(f"   Skip existing: {skip_existing}\n")
        
        # Check existing papers in Firestore
        firestore_papers_ref = firestore_db.collection('research_papers')
        existing_paper_ids = set()
        
        if skip_existing:
            print("🔍 Checking existing papers in Firestore...")
            for doc in firestore_papers_ref.stream():
                existing_paper_ids.add(doc.id)
            print(f"   Found {len(existing_paper_ids)} existing papers\n")
        
        # Sync each paper
        for i, paper in enumerate(papers, 1):
            paper_id = str(paper.paper_id)
            
            # Skip if already exists
            if skip_existing and paper_id in existing_paper_ids:
                stats["already_in_firestore"] += 1
                if i % 50 == 0:
                    print(f"   Progress: {i}/{len(papers)} (skipped {stats['already_in_firestore']} existing)")
                continue
            
            try:
                # Convert to Firestore format
                paper_data = convert_paper_to_firestore_format(paper)
                
                # Generate embedding
                has_embedding = False
                if EMBEDDING_SERVICE_AVAILABLE:
                    try:
                        embedding_service = get_embedding_service()
                        # Check if service is available (try different attribute names)
                        is_available = (hasattr(embedding_service, 'available') and embedding_service.available) or \
                                      (hasattr(embedding_service, 'model') and embedding_service.model is not None)
                        if embedding_service and is_available:
                            # Create text for embedding
                            text_parts = []
                            if paper_data.get('title'):
                                text_parts.append(paper_data['title'])
                            if paper_data.get('abstract'):
                                text_parts.append(paper_data['abstract'])
                            if paper_data.get('categories'):
                                text_parts.append(' '.join(paper_data['categories']))
                            
                            text_for_embedding = '\n'.join(text_parts)
                            embedding = embedding_service.embed_text(text_for_embedding)
                            
                            if embedding:
                                paper_data['embedding'] = Vector(embedding)
                                paper_data['embedding_model'] = getattr(embedding_service, 'model_name', 'text-embedding-004')
                                paper_data['embedding_updated'] = datetime.utcnow().isoformat()
                                has_embedding = True
                    except Exception as e:
                        structured_logger.warning(
                            f"Failed to generate embedding for paper {paper_id}",
                            error=str(e)
                        )
                        has_embedding = False
                
                # Write to Firestore
                if not dry_run:
                    firestore_papers_ref.document(paper_id).set(paper_data)
                
                stats["synced"] += 1
                
                if i % 10 == 0:
                    status = "✅" if has_embedding else "⚠️"
                    print(f"   {status} Progress: {i}/{len(papers)} synced ({stats['synced']} new, {stats['already_in_firestore']} skipped)")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Paper {paper_id} ({paper.arxiv_id}): {str(e)}"
                stats["errors"].append(error_msg)
                structured_logger.error(
                    f"Failed to sync paper {paper_id}",
                    error=str(e),
                    arxiv_id=paper.arxiv_id
                )
                if stats["failed"] <= 5:  # Only print first 5 errors
                    print(f"   ❌ {error_msg}")
        
        print(f"\n✅ Sync complete!")
        print(f"   Total in PostgreSQL: {stats['total_in_postgres']}")
        print(f"   Already in Firestore: {stats['already_in_firestore']}")
        print(f"   Synced: {stats['synced']}")
        print(f"   Failed: {stats['failed']}")
        
        if stats["errors"] and len(stats["errors"]) > 5:
            print(f"\n⚠️  {len(stats['errors'])} errors occurred (showing first 5):")
            for error in stats["errors"][:5]:
                print(f"   - {error}")
        
        return stats
        
    finally:
        db.close()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync research papers from PostgreSQL to Firestore")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to Firestore")
    parser.add_argument("--limit", type=int, help="Maximum number of papers to sync")
    parser.add_argument("--no-skip-existing", action="store_true", help="Don't skip papers that already exist")
    
    args = parser.parse_args()
    
    print("="*70)
    print("RESEARCH PAPER SYNC: PostgreSQL → Firestore")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to Firestore\n")
    
    stats = sync_papers(
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=not args.no_skip_existing
    )
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to actually sync.")
    
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

