#!/usr/bin/env python3
"""Check config/engine_registry.py against the live question_scope_ids
values in research_papers (architecture review Phase 2, gap 1, PR #32
review change 1, 2026-10-04).

Read-only. Exits 0 if every live tag is claimed by some engine; exits 1
and prints the unclaimed tags otherwise -- run by hand or wired into CI,
same spirit as governance/check_citations.py.

Usage: python scripts/check_engine_registry_drift.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from config.engine_registry import find_unregistered_tags, ALL_REGISTERED_TAGS


def live_distinct_question_scope_ids(db) -> set:
    """Firestore has no native DISTINCT; this does one field-masked scan
    over research_papers (embedding and every other field excluded),
    same approach the architecture review's own investigation used."""
    seen = set()
    papers_ref = db.collection("research_papers").select(["question_scope_ids"])
    for doc in papers_ref.stream():
        data = doc.to_dict() or {}
        for tag in data.get("question_scope_ids") or []:
            seen.add(tag)
    return seen


def main() -> int:
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print(f"Registry currently claims {len(ALL_REGISTERED_TAGS)} tags across all engines.")
    print("Scanning research_papers for live question_scope_ids values (read-only)...")

    live_tags = live_distinct_question_scope_ids(db)
    print(f"Found {len(live_tags)} distinct tags live in Firestore.")

    drift = find_unregistered_tags(live_tags)
    if drift:
        print(f"\nDRIFT: {len(drift)} tag(s) live in Firestore but not claimed by any engine:")
        for tag in sorted(drift):
            print(f"  {tag}")
        print(
            "\nThese papers currently fall outside every engine's scoped "
            "retrieval. Add the tag(s) to the matching engine's `tags` "
            "list in config/engine_registry.py."
        )
        return 1

    print("\nNo drift: every live tag is claimed by some engine.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
