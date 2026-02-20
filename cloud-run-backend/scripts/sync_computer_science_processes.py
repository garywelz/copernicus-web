#!/usr/bin/env python3
"""
Sync Chemistry Processes from Google Cloud Storage to Firestore

Reads chemistry process JSON files from GCS, generates embeddings,
and syncs them to CopernicusAI Firestore for vector search.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from google.cloud import storage
from google.cloud.firestore_v1.vector import Vector
from services.embedding_service import get_embedding_service
from utils.logging import structured_logger
import logging

logger = logging.getLogger(__name__)

# GCS Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "regal-scholar-453620-r7-podcast-storage")
COMPUTER_SCIENCE_PROCESSES_BUCKET_PATH = "computer_science-processes-database"


def create_text_for_computer_science_process(process_data: Dict[str, Any]) -> str:
    """Create text representation of computer science process for embedding."""
    parts = []
    
    # Title
    title = process_data.get('title', '')
    if title:
        parts.append(title)
    
    # Description
    description = process_data.get('description', '')
    if description:
        parts.append(description)
    
    # Category and subcategory
    category = process_data.get('category', '')
    subcategory = process_data.get('subcategory', '')
    if category:
        parts.append(f"Category: {category}")
    if subcategory:
        parts.append(f"Subcategory: {subcategory}")
    
    # Entities
    entities = process_data.get('entities', [])
    if entities and isinstance(entities, list):
        parts.append("Entities: " + ", ".join(entities[:20]))
    
    # Extract text from Mermaid diagram
    mermaid = process_data.get('mermaid', '')
    if mermaid:
        node_pattern = r'[A-Za-z0-9_]+[\[\(\{]([^\]]+)[\]\)\}]'
        nodes = re.findall(node_pattern, mermaid)
        if nodes:
            parts.append("Process steps: " + ", ".join(nodes[:30]))
    
    return "\n".join(parts)


def convert_computer_science_to_firestore_format(process_data: Dict[str, Any], process_id: str, file_path: str) -> Dict[str, Any]:
    """Convert computer science process data to Firestore format."""
    return {
        "process_id": process_id,
        "title": process_data.get('title', process_id),
        "description": process_data.get('description', ''),
        "category": process_data.get('category', 'computer_science'),
        "subcategory": process_data.get('subcategory', 'general'),
        "mermaid_code": process_data.get('mermaid', ''),
        "entities": process_data.get('entities', []),
        "metadata": {
            "source": process_data.get('metadata', {}).get('source', 'programming_framework'),
            "batch": process_data.get('metadata', {}).get('batch', ''),
            "batch_number": process_data.get('metadata', {}).get('batch_number', 0),
            "batch_title": process_data.get('metadata', {}).get('batch_title', ''),
            "color_scheme": process_data.get('metadata', {}).get('color_scheme', 'discipline_based'),
            "node_count": process_data.get('metadata', {}).get('node_count', 0),
            "complexity": process_data.get('metadata', {}).get('complexity', 'medium'),
            "file_path": file_path,
            "gcs_url": f"gs://{GCS_BUCKET_NAME}/{file_path}"
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def list_computer_science_process_files(bucket_name: str, bucket_path: str) -> List[str]:
    """List all computer science process JSON files in GCS."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    files = []
    prefix = bucket_path.rstrip('/') + '/'
    
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith('.json') and blob.name != f"{prefix}index.json":
            files.append(blob.name)
    
    return files


def get_computer_science_process_file(bucket_name: str, file_path: str) -> Optional[Dict[str, Any]]:
    """Get computer science process JSON file from GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        
        if not blob.exists():
            return None
        
        content = blob.download_as_text()
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load computer science process from {file_path}: {e}")
        return None


def sync_computer_science_processes(
    dry_run: bool = False,
    limit: Optional[int] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Sync computer science processes from GCS to Firestore.
    
    Args:
        dry_run: If True, don't actually write to Firestore
        limit: Maximum number of processes to sync (None for all)
        skip_existing: Skip processes that already exist in Firestore
    
    Returns:
        Dictionary with sync statistics
    """
    stats = {
        "total_in_gcs": 0,
        "already_in_firestore": 0,
        "synced": 0,
        "failed": 0,
        "with_embeddings": 0,
        "errors": []
    }
    
    # Initialize Firestore client
    try:
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        firestore_db = firestore.Client(project=gcp_project_id, database="copernicusai")
        print(f"✅ Connected to Firestore (project: {gcp_project_id}, database: copernicusai)")
    except Exception as e:
        print(f"❌ Failed to initialize Firestore: {e}")
        sys.exit(1)
    
    # Get embedding service
    try:
        embedding_service = get_embedding_service()
        embedding_available = True
    except Exception as e:
        logger.warning(f"Embedding service not available: {e}")
        embedding_service = None
        embedding_available = False
        print("⚠️  Embedding service not available. Processes will be synced without embeddings.")
    
    try:
        # Get all computer science process files from GCS
        print("📋 Fetching computer science processes from Google Cloud Storage...")
        all_files = list_computer_science_process_files(GCS_BUCKET_NAME, COMPUTER_SCIENCE_PROCESSES_BUCKET_PATH)
        
        if limit:
            all_files = all_files[:limit]
        
        stats["total_in_gcs"] = len(all_files)
        
        print(f"\n📊 Found {stats['total_in_gcs']} computer science processes in GCS")
        print(f"   Dry run: {dry_run}")
        print(f"   Limit: {limit or 'None (all)'}")
        print(f"   Skip existing: {skip_existing}\n")
        
        # Check existing processes in Firestore
        firestore_cs_ref = firestore_db.collection('computer_science_processes')
        existing_process_ids = set()
        
        if skip_existing:
            print("🔍 Checking existing processes in Firestore...")
            for doc in firestore_cs_ref.stream():
                existing_process_ids.add(doc.id)
            print(f"   Found {len(existing_process_ids)} existing processes\n")
        
        # Sync each process
        for i, file_path in enumerate(all_files, 1):
            try:
                # Extract process ID from file path
                process_id = file_path.replace(COMPUTER_SCIENCE_PROCESSES_BUCKET_PATH + "/", "").replace(".json", "")
                process_id = process_id.replace("/", "-")
                
                # Skip if already exists
                if skip_existing and process_id in existing_process_ids:
                    stats["already_in_firestore"] += 1
                    if i % 10 == 0:
                        print(f"   Progress: {i}/{len(all_files)} (skipped {stats['already_in_firestore']} existing)")
                    continue
                
                # Get process data from GCS
                process_data = get_computer_science_process_file(GCS_BUCKET_NAME, file_path)
                if not process_data:
                    stats["failed"] += 1
                    error_msg = f"Could not load process from {file_path}"
                    stats["errors"].append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Convert to Firestore format
                cs_doc = convert_computer_science_to_firestore_format(process_data, process_id, file_path)
                
                # Generate embedding
                has_embedding = False
                if embedding_available and embedding_service:
                    try:
                        text = create_text_for_computer_science_process(process_data)
                        if text:
                            embedding = embedding_service.embed_text(text)
                            if embedding:
                                cs_doc["embedding"] = Vector(embedding)
                                cs_doc["embedding_model"] = "text-embedding-004"
                                cs_doc["embedding_updated"] = datetime.utcnow().isoformat()
                                has_embedding = True
                                stats["with_embeddings"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for {process_id}: {e}")
                        stats["errors"].append(f"{process_id}: embedding generation failed")
                
                # Write to Firestore
                if not dry_run:
                    firestore_cs_ref.document(process_id).set(cs_doc)
                
                stats["synced"] += 1
                
                # Progress reporting
                if i % 10 == 0 or i == len(all_files):
                    status = "✅" if has_embedding else "⚠️"
                    print(f"   {status} Progress: {i}/{len(all_files)} "
                          f"(synced: {stats['synced']}, "
                          f"embeddings: {stats['with_embeddings']}, "
                          f"failed: {stats['failed']})")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Error syncing {file_path}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                if len(stats["errors"]) <= 5:
                    print(f"   ❌ Error: {error_msg}")
        
        # Final summary
        print("\n" + "="*70)
        print("  SYNC COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Total in GCS: {stats['total_in_gcs']}")
        print(f"   Already in Firestore: {stats['already_in_firestore']}")
        print(f"   Synced: {stats['synced']}")
        print(f"   With embeddings: {stats['with_embeddings']}")
        print(f"   Failed: {stats['failed']}")
        
        if stats["errors"]:
            print(f"\n⚠️  Errors ({len(stats['errors'])}):")
            for error in stats["errors"][:10]:
                print(f"   - {error}")
            if len(stats["errors"]) > 10:
                print(f"   ... and {len(stats['errors']) - 10} more errors")
        
        if dry_run:
            print("\n⚠️  This was a dry run. No changes were made to Firestore.")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync computer science processes from GCS to Firestore")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to Firestore")
    parser.add_argument("--limit", type=int, help="Maximum number of processes to sync")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-sync existing processes")
    
    args = parser.parse_args()
    
    print("="*70)
    print("  SYNC COMPUTER SCIENCE PROCESSES TO FIRESTORE")
    print("="*70)
    print()
    
    stats = sync_computer_science_processes(
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=not args.no_skip_existing
    )
    
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

