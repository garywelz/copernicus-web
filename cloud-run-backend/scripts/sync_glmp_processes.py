#!/usr/bin/env python3
"""
Sync GLMP Processes from Google Cloud Storage to Firestore

Reads GLMP process JSON files from GCS, generates embeddings,
and syncs them to CopernicusAI Firestore for vector search.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from services.embedding_service import get_embedding_service
from mcp_server.utils.gcs_client import list_glmp_files, get_glmp_file
from mcp_server.config import GCS_BUCKET_NAME, GLMP_BUCKET_PATH
from utils.logging import structured_logger
import logging

logger = logging.getLogger(__name__)


def create_text_for_glmp(process_data: Dict[str, Any]) -> str:
    """Create text representation of GLMP process for embedding."""
    parts = []
    
    # Title/Name
    title = process_data.get('title') or process_data.get('name') or process_data.get('id', '')
    if title:
        parts.append(title)
    
    # Description
    description = process_data.get('description', '')
    if description:
        parts.append(description)
    
    # Category
    category = process_data.get('category', '')
    if category:
        parts.append(f"Category: {category}")
    
    # Organism
    organism = process_data.get('organism', '')
    if organism:
        parts.append(f"Organism: {organism}")
    
    # Extract text from Mermaid diagram (node labels)
    mermaid = process_data.get('mermaid') or process_data.get('mermaid_syntax') or process_data.get('flowchart', '')
    if mermaid:
        # Extract node labels from Mermaid syntax (simple extraction)
        # Look for patterns like "A[Label]" or "A(Label)" or "A{Label}"
        import re
        node_pattern = r'[A-Za-z0-9_]+[\[\(\{]([^\]]+)[\]\)\}]'
        nodes = re.findall(node_pattern, mermaid)
        if nodes:
            # Add first 20 node labels (to avoid too much text)
            parts.append("Process steps: " + ", ".join(nodes[:20]))
    
    # Sources/References
    sources = process_data.get('sources', [])
    if sources and isinstance(sources, list):
        # Add source titles if available
        source_texts = []
        for source in sources[:5]:  # First 5 sources
            if isinstance(source, dict):
                source_texts.append(source.get('title', '') or source.get('citation', ''))
            elif isinstance(source, str):
                source_texts.append(source)
        if source_texts:
            parts.append("References: " + ", ".join(filter(None, source_texts)))
    
    return "\n".join(parts)


def convert_glmp_to_firestore_format(process_data: Dict[str, Any], process_id: str, file_path: str) -> Dict[str, Any]:
    """Convert GLMP process data to Firestore format."""
    return {
        "process_id": process_id,
        "name": process_data.get('name') or process_data.get('title') or process_id,
        "title": process_data.get('title') or process_data.get('name') or process_id,
        "description": process_data.get('description', ''),
        "category": process_data.get('category', ''),
        "organism": process_data.get('organism', ''),
        "complexity": process_data.get('complexity', ''),
        "mermaid_code": process_data.get('mermaid') or process_data.get('mermaid_syntax') or process_data.get('flowchart', ''),
        "sources": process_data.get('sources', []),
        "metadata": {
            "scientific_accuracy": process_data.get('scientificAccuracy', ''),
            "color_scheme": process_data.get('colorScheme', ''),
            "version": process_data.get('version', '1.0'),
            "file_path": file_path,
            "gcs_url": f"gs://{GCS_BUCKET_NAME}/{file_path}"
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


def sync_glmp_processes(
    dry_run: bool = False,
    limit: Optional[int] = None,
    skip_existing: bool = True
) -> Dict[str, Any]:
    """
    Sync GLMP processes from GCS to Firestore.
    
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
        # Get all GLMP files from GCS
        print("📋 Fetching GLMP processes from Google Cloud Storage...")
        all_files = list_glmp_files(GCS_BUCKET_NAME, GLMP_BUCKET_PATH)
        
        # Deduplicate by process ID - prefer subdirectory versions
        print("🔍 Deduplicating processes (removing duplicates)...")
        from collections import defaultdict
        from google.cloud import storage
        
        process_id_to_files = defaultdict(list)
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        
        for file_path in all_files:
            try:
                process_data = get_glmp_file(GCS_BUCKET_NAME, file_path)
                if process_data:
                    process_id = process_data.get('id') or process_data.get('name') or file_path.split('/')[-1].replace('.json', '')
                    blob = bucket.blob(file_path)
                    updated = blob.updated if blob.exists() else None
                    process_id_to_files[process_id].append((file_path, updated))
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                continue
        
        # For each process ID, pick the best file:
        # 1. Prefer subdirectory version (e.g., bacillus/process.json)
        # 2. If both in subdirs, prefer most recent
        # 3. Otherwise, use root version
        glmp_files = []
        for process_id, file_list in process_id_to_files.items():
            if len(file_list) == 1:
                glmp_files.append(file_list[0][0])
            else:
                # Prefer subdirectory versions
                subdir_files = [(f, u) for f, u in file_list if '/' in f.replace(GLMP_BUCKET_PATH + '/', '').replace('.json', '')]
                if subdir_files:
                    # If multiple subdir files, prefer most recent
                    subdir_files.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
                    glmp_files.append(subdir_files[0][0])
                else:
                    # Use root version (most recent if multiple)
                    file_list.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
                    glmp_files.append(file_list[0][0])
        
        print(f"   Found {len(all_files)} files, {len(process_id_to_files)} unique processes")
        print(f"   Removed {len(all_files) - len(glmp_files)} duplicate files")
        
        if limit:
            glmp_files = glmp_files[:limit]
        
        stats["total_in_gcs"] = len(glmp_files)
        
        print(f"\n📊 Found {stats['total_in_gcs']} GLMP processes in GCS")
        print(f"   Dry run: {dry_run}")
        print(f"   Limit: {limit or 'None (all)'}")
        print(f"   Skip existing: {skip_existing}\n")
        
        # Check existing processes in Firestore
        firestore_glmp_ref = firestore_db.collection('glmp_processes')
        existing_process_ids = set()
        
        if skip_existing:
            print("🔍 Checking existing processes in Firestore...")
            for doc in firestore_glmp_ref.stream():
                existing_process_ids.add(doc.id)
            print(f"   Found {len(existing_process_ids)} existing processes\n")
        
        # Sync each process
        for i, file_path in enumerate(glmp_files, 1):
            try:
                # Extract process ID from file path
                # Format: glmp-v2/processes/process-name.json
                process_id = file_path.replace(GLMP_BUCKET_PATH + "/", "").replace(".json", "")
                # Clean process_id for Firestore (replace slashes and special chars)
                process_id = process_id.replace("/", "-").replace(" ", "-")
                
                # Skip if already exists
                if skip_existing and process_id in existing_process_ids:
                    stats["already_in_firestore"] += 1
                    if i % 20 == 0:
                        print(f"   Progress: {i}/{len(glmp_files)} (skipped {stats['already_in_firestore']} existing)")
                    continue
                
                # Get process data from GCS
                process_data = get_glmp_file(GCS_BUCKET_NAME, file_path)
                if not process_data:
                    stats["failed"] += 1
                    error_msg = f"Could not load process from {file_path}"
                    stats["errors"].append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                # Convert to Firestore format
                glmp_doc = convert_glmp_to_firestore_format(process_data, process_id, file_path)
                
                # Generate embedding
                has_embedding = False
                if embedding_available and embedding_service:
                    try:
                        text = create_text_for_glmp(process_data)
                        if text and text.strip():
                            embedding = embedding_service.embed_text(text)
                            if embedding:
                                # Convert to Vector type for Firestore vector search
                                from google.cloud.firestore_v1.vector import Vector
                                glmp_doc["embedding"] = Vector(embedding)
                                glmp_doc["embedding_model"] = "text-embedding-004"
                                glmp_doc["embedding_updated"] = datetime.utcnow().isoformat()
                                has_embedding = True
                                stats["with_embeddings"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for process {process_id}: {e}")
                
                # Write to Firestore
                if not dry_run:
                    firestore_glmp_ref.document(process_id).set(glmp_doc)
                
                stats["synced"] += 1
                
                if i % 10 == 0:
                    status = "✅" if has_embedding else "⚠️"
                    print(f"   {status} Progress: {i}/{len(glmp_files)} synced ({stats['synced']} new, {stats['already_in_firestore']} skipped)")
                
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Process {file_path}: {str(e)}"
                stats["errors"].append(error_msg)
                logger.error(f"Failed to sync process {file_path}: {str(e)}")
                if stats["failed"] <= 5:  # Only print first 5 errors
                    print(f"   ❌ {error_msg}")
        
        print(f"\n✅ Sync complete!")
        print(f"   Total in GCS: {stats['total_in_gcs']}")
        print(f"   Already in Firestore: {stats['already_in_firestore']}")
        print(f"   Synced: {stats['synced']}")
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
    
    parser = argparse.ArgumentParser(description="Sync GLMP processes from GCS to Firestore")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually write to Firestore")
    parser.add_argument("--limit", type=int, help="Maximum number of processes to sync")
    parser.add_argument("--no-skip-existing", action="store_true", help="Don't skip processes that already exist")
    
    args = parser.parse_args()
    
    print("="*70)
    print("GLMP PROCESS SYNC: Google Cloud Storage → Firestore")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made to Firestore\n")
    
    stats = sync_glmp_processes(
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=not args.no_skip_existing
    )
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to actually sync.")
    
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

