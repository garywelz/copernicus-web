#!/usr/bin/env python3
"""
One-time cleanup: delete 49 content-free placeholder stubs from
chemistry_processes.

Background (GLMP_MASTER_TODO.md item 24): a batch of 49 docs created
2025-12-29 all carry the identical placeholder description
"Chemistry process: {title}" and generic auto-generated mermaid diagrams
with no real chemistry content. A later, substantive batch (2026-01-08
onward) added real content covering the same ground -- sometimes under the
same subcategory, sometimes a renamed one (e.g.
surface_chemistry_catalysis -> surface_chemistry, kinetic_processes ->
kinetics, thermodynamic_processes -> thermodynamics, spectroscopy_analysis
-> spectroscopy_advanced, electrochemical_processes -> electrochemistry).
The December stubs were never removed and still compete in retrieval
against the better content that superseded them.

chemistry_processes is a Methods & Tools demonstration collection, not part
of a running Knowledge Engine project (GLMP, ATAP) -- confirmed out of
scope for that concern before this script was written.

Identifies stubs by the exact placeholder pattern at run time (not a
hardcoded ID list) so a --dry-run run right before the real one reflects
current state, not a stale list from when this was investigated.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

COLLECTION = "chemistry_processes"


def find_stubs(col) -> list:
    stubs = []
    for d in col.stream():
        data = d.to_dict() or {}
        title = data.get("title", "")
        desc = data.get("description", "")
        if desc.strip() == f"Chemistry process: {title}".strip():
            stubs.append((d.id, title, str(data.get("created_at", ""))[:10]))
    return stubs


def dedup(dry_run: bool = False) -> dict:
    gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    db = firestore.Client(project=gcp_project_id, database="copernicusai")
    col = db.collection(COLLECTION)

    total_before = len(list(col.stream()))
    stubs = find_stubs(col)

    print(f"Total docs before: {total_before}")
    print(f"Stubs found: {len(stubs)}")
    print()

    stats = {"deleted": 0, "failed": 0, "errors": []}
    for doc_id, title, created in sorted(stubs):
        print(f"  {'[DRY RUN] would delete' if dry_run else 'DELETE'}  {created}  {doc_id:55s} | {title}")
        if not dry_run:
            try:
                col.document(doc_id).delete()
                stats["deleted"] += 1
            except Exception as exc:
                stats["failed"] += 1
                stats["errors"].append(f"{doc_id}: {exc}")

    print()
    if dry_run:
        print(f"Would delete: {len(stubs)}")
    else:
        print(f"Deleted: {stats['deleted']}  Failed: {stats['failed']}")
        if stats["errors"]:
            print("Errors:")
            for e in stats["errors"]:
                print(f"  - {e}")

    return stats


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no deletes")
    args = parser.parse_args()

    stats = dedup(dry_run=args.dry_run)
    return 1 if stats.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
