#!/usr/bin/env python3
"""
One-time migration: copy math_processes -> atap_graphs.

NOT the sync pipeline (see sync_math_processes.py, which now writes to
atap_graphs going forward). This script exists only to carry the existing
237 already-correctly-embedded docs (1536d, text-embedding-3-small) over to
the new collection name without re-embedding them -- the vectors are copied
byte-for-byte via Vector, never regenerated.

Excludes ORPHAN_ID defensively. As of the last live check this ID does not
exist in math_processes at all (confirmed via direct .get() and via a full
GCS-manifest-vs-Firestore diff showing zero mismatches either direction), so
in practice this is a no-op exclusion -- kept only so the script matches the
agreed migration spec and is a no-op either way if that changes.

Idempotent: full .set() (not merge) per document, same document ID. Safe to
re-run if interrupted -- last write wins, no duplicates.

Does NOT delete math_processes. Read-only against the source collection.

Usage:
  python scripts/migrate_math_processes_to_atap_graphs.py --dry-run
  python scripts/migrate_math_processes_to_atap_graphs.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

SOURCE_COLLECTION = "math_processes"
TARGET_COLLECTION = "atap_graphs"
ORPHAN_ID = "math-set-theory-001"


def migrate(dry_run: bool = False) -> dict:
    gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    db = firestore.Client(project=gcp_project_id, database="copernicusai")

    source_ref = db.collection(SOURCE_COLLECTION)
    target_ref = db.collection(TARGET_COLLECTION)

    print(f"Reading source collection: {SOURCE_COLLECTION}")
    source_docs = list(source_ref.stream())
    print(f"  Source doc count: {len(source_docs)}")

    orphan_present = any(d.id == ORPHAN_ID for d in source_docs)
    print(f"  Orphan '{ORPHAN_ID}' present in source: {orphan_present}")

    to_migrate = [d for d in source_docs if d.id != ORPHAN_ID]
    print(f"  Docs to migrate (source minus orphan, if present): {len(to_migrate)}")
    print(f"  Dry run: {dry_run}\n")

    stats = {
        "source_count": len(source_docs),
        "orphan_present": orphan_present,
        "planned_migrate_count": len(to_migrate),
        "migrated": 0,
        "failed": 0,
        "errors": [],
    }

    for i, snap in enumerate(to_migrate, 1):
        try:
            data = snap.to_dict()
            if not dry_run:
                target_ref.document(snap.id).set(data)
            stats["migrated"] += 1
            if i % 25 == 0 or i == len(to_migrate):
                print(f"  Progress: {i}/{len(to_migrate)} migrated")
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"{snap.id}: {e}")
            print(f"  FAILED {snap.id}: {e}")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE" if not dry_run else "DRY RUN COMPLETE (no writes)")
    print("=" * 60)
    print(f"  Source count:        {stats['source_count']}")
    print(f"  Orphan present:      {stats['orphan_present']}")
    print(f"  Planned to migrate:  {stats['planned_migrate_count']}")
    print(f"  Migrated:            {stats['migrated']}")
    print(f"  Failed:              {stats['failed']}")
    if stats["errors"]:
        print("  Errors:")
        for e in stats["errors"]:
            print(f"    - {e}")

    return stats


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Read and report only, no writes")
    args = parser.parse_args()

    stats = migrate(dry_run=args.dry_run)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
