#!/usr/bin/env python3
"""
Sync Mathematics Processes from Google Cloud Storage to Firestore

Reads canonical JSON from mathematics-processes-database/processes/ on GCS
and syncs to CopernicusAI Firestore (math_processes).

Embeddings: use backfill_embeddings.py --collection math_processes (OpenAI 1536d).
This script does not write Vertex embeddings to avoid mixed vector spaces.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from google.cloud import storage
import logging

logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "regal-scholar-453620-r7-podcast-storage")
MATH_PROCESSES_BUCKET_PATH = "mathematics-processes-database"
PROCESSES_PREFIX = f"{MATH_PROCESSES_BUCKET_PATH}/processes/"

SKIP_JSON_NAMES = {
    "metadata.json",
    "process-index.json",
    "catalog_config.json",
    "index.json",
}


def create_text_for_math_process(process_data: Dict[str, Any]) -> str:
    """Text for embedding (also used by vector_search.create_text_for_math)."""
    parts = []
    for field in ("name", "title", "description"):
        val = process_data.get(field, "")
        if val:
            parts.append(str(val))
    for field in ("category", "subcategory", "subcategory_name"):
        val = process_data.get(field, "")
        if val:
            parts.append(f"{field}: {val}")
    keywords = process_data.get("keywords") or []
    if keywords:
        parts.append("Keywords: " + ", ".join(keywords[:20]))
    mermaid = process_data.get("mermaid") or process_data.get("mermaid_code") or ""
    if mermaid:
        node_pattern = r'[A-Za-z0-9_]+[\[\(\{]([^\]\)\}]+)[\]\)\}]'
        nodes = re.findall(node_pattern, mermaid)
        if nodes:
            parts.append("Process steps: " + ", ".join(nodes[:30]))
    return "\n".join(parts)


def convert_math_to_firestore_format(
    process_data: Dict[str, Any], process_id: str, file_path: str
) -> Dict[str, Any]:
    """Map JSON-canonical schema to Firestore math_processes document."""
    name = process_data.get("name") or process_data.get("title") or process_id
    complexity = process_data.get("complexity") or {}
    if isinstance(complexity, dict):
        level = complexity.get("level", "medium")
    else:
        level = str(complexity)

    return {
        "process_id": process_id,
        "id": process_data.get("id", process_id),
        "name": name,
        "title": name,
        "description": process_data.get("description", ""),
        "category": process_data.get("category", "mathematics"),
        "subcategory": process_data.get("subcategory", "general"),
        "subcategory_name": process_data.get("subcategory_name", ""),
        "processType": process_data.get("processType", "algorithm"),
        "mermaid": process_data.get("mermaid", ""),
        "mermaid_code": process_data.get("mermaid", ""),
        "keywords": process_data.get("keywords", []),
        "sources": process_data.get("sources", []),
        "metadata": {
            "source": "json_canonical",
            "file_path": file_path,
            "gcs_url": f"gs://{GCS_BUCKET_NAME}/{file_path}",
            "complexity": level,
            "verified": process_data.get("verified", True),
            "flowchartStandard": process_data.get("flowchartStandard", "GLMP_6color"),
        },
        "created_at": process_data.get("created", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_math_process_files(bucket_name: str, bucket_path: str) -> List[str]:
    """List process JSON files under processes/ only."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    prefix = f"{bucket_path.rstrip('/')}/processes/"

    files = []
    for blob in bucket.list_blobs(prefix=prefix):
        if not blob.name.endswith(".json"):
            continue
        base = blob.name.rsplit("/", 1)[-1]
        if base in SKIP_JSON_NAMES:
            continue
        files.append(blob.name)
    return sorted(files)


def get_math_process_file(bucket_name: str, file_path: str) -> Optional[Dict[str, Any]]:
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    except Exception as e:
        logger.error("Failed to load math process from %s: %s", file_path, e)
        return None


def process_id_from_blob(file_path: str, process_data: Dict[str, Any]) -> str:
    if process_data.get("id"):
        return process_data["id"]
    rel = file_path.replace(PROCESSES_PREFIX, "").replace(".json", "")
    return rel.replace("/", "-")


def sync_math_processes(
    dry_run: bool = False,
    limit: Optional[int] = None,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    stats = {
        "total_in_gcs": 0,
        "already_in_firestore": 0,
        "synced": 0,
        "updated": 0,
        "failed": 0,
        "errors": [],
    }

    gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    firestore_db = firestore.Client(project=gcp_project_id, database="copernicusai")
    print(f"✅ Connected to Firestore (project: {gcp_project_id}, database: copernicusai)")

    print("📋 Fetching mathematics processes from GCS...")
    print(f"   Bucket path: {MATH_PROCESSES_BUCKET_PATH}/processes/")
    all_files = list_math_process_files(GCS_BUCKET_NAME, MATH_PROCESSES_BUCKET_PATH)
    if limit:
        all_files = all_files[:limit]
    stats["total_in_gcs"] = len(all_files)

    print(f"\n📊 Found {stats['total_in_gcs']} process JSON files in GCS")
    print(f"   Dry run: {dry_run}")
    print(f"   Skip existing: {skip_existing}\n")

    firestore_math_ref = firestore_db.collection("math_processes")
    existing_process_ids: set[str] = set()
    if skip_existing:
        print("🔍 Checking existing processes in Firestore...")
        for doc in firestore_math_ref.stream():
            existing_process_ids.add(doc.id)
        print(f"   Found {len(existing_process_ids)} existing documents\n")

    for i, file_path in enumerate(all_files, 1):
        try:
            process_data = get_math_process_file(GCS_BUCKET_NAME, file_path)
            if not process_data:
                stats["failed"] += 1
                stats["errors"].append(f"Could not load {file_path}")
                continue

            process_id = process_id_from_blob(file_path, process_data)
            exists = process_id in existing_process_ids

            if skip_existing and exists:
                stats["already_in_firestore"] += 1
                if i % 25 == 0:
                    print(f"   Progress: {i}/{len(all_files)} (skipped {stats['already_in_firestore']} existing)")
                continue

            math_doc = convert_math_to_firestore_format(process_data, process_id, file_path)
            if not dry_run:
                firestore_math_ref.document(process_id).set(math_doc, merge=True)

            stats["synced"] += 1
            if exists:
                stats["updated"] += 1

            if i % 25 == 0 or i == len(all_files):
                print(f"   ✅ Progress: {i}/{len(all_files)} (synced: {stats['synced']})")

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"{file_path}: {e}")
            logger.error("Error syncing %s", file_path, exc_info=True)

    print("\n" + "=" * 70)
    print("  SYNC COMPLETE")
    print("=" * 70)
    print(f"   Total in GCS:           {stats['total_in_gcs']}")
    print(f"   Already in Firestore:   {stats['already_in_firestore']}")
    print(f"   Synced (new+updated):   {stats['synced']}")
    print(f"   Failed:                 {stats['failed']}")
    if stats["errors"]:
        print(f"\n⚠️  Errors ({len(stats['errors'])}):")
        for error in stats["errors"][:10]:
            print(f"   - {error}")
    if dry_run:
        print("\n⚠️  Dry run — no Firestore writes.")
    else:
        print("\n💡 Run: python backfill_embeddings.py --collection math_processes --run-all")

    return stats


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-sync all processes (merge update)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("  SYNC MATHEMATICS PROCESSES TO FIRESTORE")
    print("=" * 70)
    print()

    stats = sync_math_processes(
        dry_run=args.dry_run,
        limit=args.limit,
        skip_existing=not args.no_skip_existing,
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
