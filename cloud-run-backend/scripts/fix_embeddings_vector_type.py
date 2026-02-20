#!/usr/bin/env python3
"""
Fix Embeddings: Convert list embeddings to Vector type

Updates all existing documents to store embeddings as Vector type
instead of lists, which is required for Firestore vector search.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from utils.logging import structured_logger
import logging

logger = logging.getLogger(__name__)


def fix_collection_embeddings(collection_name: str, dry_run: bool = True) -> Dict[str, Any]:
    """Convert list embeddings to Vector type in a collection."""
    stats = {
        "total_documents": 0,
        "with_embeddings": 0,
        "fixed": 0,
        "already_vector": 0,
        "errors": []
    }
    
    try:
        gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
        db = firestore.Client(project=gcp_project_id, database="copernicusai")
        
        collection_ref = db.collection(collection_name)
        docs = list(collection_ref.stream())
        stats["total_documents"] = len(docs)
        
        print(f"\n📋 Processing {collection_name}...")
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Dry run: {dry_run}\n")
        
        for i, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()
                embedding = data.get("embedding")
                
                if not embedding:
                    continue
                
                stats["with_embeddings"] += 1
                
                # Check if already Vector type
                if isinstance(embedding, Vector):
                    stats["already_vector"] += 1
                    if i % 50 == 0:
                        print(f"   Progress: {i}/{len(docs)} (already Vector: {stats['already_vector']})")
                    continue
                
                # Convert list to Vector
                if isinstance(embedding, list):
                    if not dry_run:
                        doc_ref = collection_ref.document(doc.id)
                        doc_ref.update({
                            "embedding": Vector(embedding)
                        })
                    stats["fixed"] += 1
                    
                    if i % 10 == 0:
                        print(f"   ✅ Progress: {i}/{len(docs)} (fixed: {stats['fixed']})")
                else:
                    logger.warning(f"Unknown embedding type for {doc.id}: {type(embedding)}")
                    
            except Exception as e:
                stats["errors"].append(f"{doc.id}: {str(e)}")
                logger.error(f"Error fixing {doc.id}: {e}")
                if len(stats["errors"]) <= 5:
                    print(f"   ❌ Error fixing {doc.id}: {e}")
        
        print(f"\n✅ {collection_name} complete!")
        print(f"   Total: {stats['total_documents']}")
        print(f"   With embeddings: {stats['with_embeddings']}")
        print(f"   Fixed: {stats['fixed']}")
        print(f"   Already Vector: {stats['already_vector']}")
        print(f"   Errors: {len(stats['errors'])}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix embeddings: convert lists to Vector type")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update documents")
    parser.add_argument("--collection", type=str, help="Specific collection to fix (default: all)")
    
    args = parser.parse_args()
    
    print("="*70)
    print("FIX EMBEDDINGS: Convert List → Vector Type")
    print("="*70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")
    
    collections = []
    if args.collection:
        collections = [args.collection]
    else:
        collections = ["research_papers", "glmp_processes", "podcast_jobs"]
    
    all_stats = {}
    for collection in collections:
        stats = fix_collection_embeddings(collection, dry_run=args.dry_run)
        all_stats[collection] = stats
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    total_fixed = sum(s["fixed"] for s in all_stats.values())
    total_already = sum(s["already_vector"] for s in all_stats.values())
    total_errors = sum(len(s["errors"]) for s in all_stats.values())
    
    print(f"\n✅ Total fixed: {total_fixed}")
    print(f"✅ Already Vector: {total_already}")
    print(f"❌ Errors: {total_errors}")
    
    if args.dry_run:
        print("\n⚠️  This was a dry run. Use without --dry-run to actually fix embeddings.")
    
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

