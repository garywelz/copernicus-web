#!/usr/bin/env python3
"""Sync all JSON-canonical process families from GCS to Firestore."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from process_sync_common import sync_process_collection
from sync_math_processes import sync_math_processes as sync_atap_graphs

# atap_graphs (formerly math_processes) is embedding-capable and fail-loud
# (see sync_math_processes.py) -- it is NOT synced through the generic
# metadata-only process_sync_common path below. That path never writes an
# embedding, so routing atap_graphs through it would recreate the exact
# vectorless-doc defect the atap_graphs migration exists to fix. One writer
# discipline for atap_graphs, not two: this driver calls the dedicated,
# already-fail-loud sync function instead of duplicating embedding logic
# into the shared helper (which is also used by the four families below and
# is out of scope for this migration).
ATAP_GRAPHS_FAMILY = "atap_graphs"

FAMILIES = [
    ("chemistry_processes", "chemistry-processes-database", "chemistry"),
    ("physics_processes", "physics-processes-database", "physics"),
    ("computer_science_processes", "computer-science-processes-database", "computer_science"),
    ("biology_processes", "biology-processes-database", "biology"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--family",
        choices=[ATAP_GRAPHS_FAMILY] + [f[0] for f in FAMILIES],
        help="Sync one family only",
    )
    parser.add_argument("--no-skip-existing", action="store_true")
    args = parser.parse_args()

    failed = 0

    if not args.family or args.family == ATAP_GRAPHS_FAMILY:
        print(f"\n{'=' * 60}\n  {ATAP_GRAPHS_FAMILY} ← mathematics-processes-database (embedding-capable, fail-loud)\n{'=' * 60}")
        stats = sync_atap_graphs(
            dry_run=args.dry_run,
            skip_existing=not args.no_skip_existing,
        )
        print(
            f"   GCS={stats['total_in_gcs']} synced={stats['synced']} "
            f"embeddings={stats['with_embeddings']} "
            f"skipped={stats['already_in_firestore']} failed={stats['failed']}"
        )
        if stats["failed"]:
            failed += stats["failed"]

    families = FAMILIES if args.family != ATAP_GRAPHS_FAMILY else []
    if args.family and args.family != ATAP_GRAPHS_FAMILY:
        families = [f for f in FAMILIES if f[0] == args.family]

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
