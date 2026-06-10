#!/usr/bin/env python3
"""Prune legacy GLMP Firestore docs and re-sync canonical glmp-v2 JSON from GCS."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google.cloud import firestore

from process_sync_common import sync_process_collection

GCP_PROJECT = "regal-scholar-453620-r7"
FIRESTORE_DB = "copernicusai"
COLLECTION = "glmp_processes"
BUCKET_PATH = "glmp-v2"
GCS_META = "gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/metadata.json"


def load_canonical_ids() -> set[str]:
    result = subprocess.run(
        ["gsutil", "cat", GCS_META],
        check=True,
        capture_output=True,
        text=True,
    )
    meta = json.loads(result.stdout)
    return {p["id"] for p in meta["processes"]}


def prune_firestore(canonical: set[str], *, apply: bool) -> dict:
    db = firestore.Client(project=GCP_PROJECT, database=FIRESTORE_DB)
    coll = db.collection(COLLECTION)
    to_delete: list[str] = []
    kept = 0
    for doc in coll.stream():
        if doc.id in canonical:
            kept += 1
        else:
            to_delete.append(doc.id)

    if apply and to_delete:
        for i in range(0, len(to_delete), 400):
            batch = db.batch()
            for doc_id in to_delete[i : i + 400]:
                batch.delete(coll.document(doc_id))
            batch.commit()

    return {
        "canonical_count": len(canonical),
        "firestore_kept": kept,
        "firestore_deleted": len(to_delete),
        "deleted_ids": to_delete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete orphans and re-sync")
    parser.add_argument("--skip-resync", action="store_true", help="Prune only, do not re-sync from GCS")
    args = parser.parse_args()

    canonical = load_canonical_ids()
    print(f"Canonical GLMP IDs: {len(canonical)}")

    prune_report = prune_firestore(canonical, apply=args.apply)
    print(json.dumps({k: v for k, v in prune_report.items() if k != "deleted_ids"}, indent=2))
    if prune_report["deleted_ids"]:
        print(f"Sample deleted IDs: {prune_report['deleted_ids'][:5]}")

    if args.apply and not args.skip_resync:
        print("\nRe-syncing glmp-v2 from GCS (canonical JSON ids)...")
        sync_stats = sync_process_collection(
            collection_name=COLLECTION,
            bucket_path=BUCKET_PATH,
            default_category="glmp",
            dry_run=False,
            skip_existing=False,
        )
        print(json.dumps(sync_stats, indent=2))

    if args.apply:
        db = firestore.Client(project=GCP_PROJECT, database=FIRESTORE_DB)
        final = sum(1 for _ in db.collection(COLLECTION).stream())
        print(f"\nFinal Firestore {COLLECTION} count: {final} (target {len(canonical)})")

    elif not args.apply:
        print("\nDry run only. Re-run with --apply to delete and re-sync.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
