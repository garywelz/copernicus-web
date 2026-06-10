#!/usr/bin/env python3
"""Sync all JSON-canonical process families from GCS to Firestore."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from process_sync_common import sync_process_collection

FAMILIES = [
    ("math_processes", "mathematics-processes-database", "mathematics"),
    ("chemistry_processes", "chemistry-processes-database", "chemistry"),
    ("physics_processes", "physics-processes-database", "physics"),
    ("computer_science_processes", "computer-science-processes-database", "computer_science"),
    ("biology_processes", "biology-processes-database", "biology"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--family", choices=[f[0] for f in FAMILIES], help="Sync one family only")
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    families = FAMILIES
    if args.family:
        families = [f for f in FAMILIES if f[0] == args.family]

    failed = 0
    for collection, bucket_path, category in families:
        print(f"\n{'=' * 60}\n  {collection} ← {bucket_path}\n{'=' * 60}")
        stats = sync_process_collection(
            collection_name=collection,
            bucket_path=bucket_path,
            default_category=category,
            dry_run=args.dry_run,
            skip_existing=not args.no_skip_existing,
        )
        print(
            f"   GCS={stats['total_in_gcs']} synced={stats['synced']} "
            f"skipped={stats['already_in_firestore']} failed={stats['failed']}"
        )
        if stats["failed"]:
            failed += stats["failed"]

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
