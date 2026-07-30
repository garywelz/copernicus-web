#!/usr/bin/env python3
"""
One-time migration: correct 12 corrupted document IDs in physics_processes.

Firestore-only fix (see GLMP_MASTER_TODO.md item 22). Each of these 12 docs
has a title/content that is verified correct (description + mermaid checked
directly against the title, 12/12 confirmed) but a document ID whose slug
describes a different, unrelated topic -- a systematic per-subcategory
rotation discovered during findability-probe design.

Deliberately NOT touched by this script (flagged as a separate, still-open
item): metadata.file_path and metadata.gcs_url still point at the
old-wrong-slug GCS source filename. The GCS JSON files themselves are not
renamed here, so re-running a physics sync from GCS would recreate the wrong
IDs. This script only fixes the live Firestore document IDs and the doc's own
internal id/process_id fields to match.

Mechanism: full-document copy to the new (correct) ID -- vector embedding
carried across via Vector, not regenerated -- then delete the old-ID doc.
Same pattern as migrate_math_processes_to_atap_graphs.py. Idempotent: safe
to re-run (skips a pair if the new ID already exists and the old one is
already gone).
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore

COLLECTION = "physics_processes"

# (old_id, new_id) -- new_id derived from the verified-correct title.
ID_FIXES = [
    ("astrophysics-higgs-mechanism", "astrophysics-big-bang-nucleosynthesis"),
    ("astrophysics-particle-collision", "astrophysics-stellar-collapse-chandrasekhar-limit"),
    ("astrophysics-standard-model", "astrophysics-stellar-nucleosynthesis-pp-chain"),
    ("electromagnetism-quantum-computing", "electromagnetism-maxwells-equations-to-em-waves"),
    ("electromagnetism-quantum-entanglement", "electromagnetism-electrostatic-boundary-value-problem"),
    ("electromagnetism-wave-function", "electromagnetism-electromagnetic-induction"),
    ("quantum_mechanics-electromagnetic-induction", "quantum_mechanics-time-independent-schrodinger-equation"),
    ("quantum_mechanics-electromagnetic-wave", "quantum_mechanics-quantum-tunneling-through-a-barrier"),
    ("quantum_mechanics-maxwells-equations", "quantum_mechanics-quantum-harmonic-oscillator"),
    ("solid_state-nuclear-decay", "solid_state-electronic-band-structure-bloch"),
    ("solid_state-nuclear-fission", "solid_state-bcs-superconductivity-cooper-pairing"),
    ("solid_state-nuclear-fusion", "solid_state-phonons-debye-heat-capacity"),
]


def fix_ids(dry_run: bool = False) -> dict:
    gcp_project_id = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
    db = firestore.Client(project=gcp_project_id, database="copernicusai")
    col = db.collection(COLLECTION)

    stats = {"fixed": 0, "skipped": 0, "failed": 0, "errors": []}

    for old_id, new_id in ID_FIXES:
        try:
            old_ref = col.document(old_id)
            new_ref = col.document(new_id)
            old_snap = old_ref.get()
            new_snap = new_ref.get()

            if not old_snap.exists and new_snap.exists:
                print(f"  SKIP  {old_id} -> {new_id} (already migrated: old gone, new exists)")
                stats["skipped"] += 1
                continue

            if not old_snap.exists:
                stats["failed"] += 1
                stats["errors"].append(f"{old_id}: source doc missing, nothing to migrate")
                print(f"  FAIL  {old_id}: source doc missing")
                continue

            data = old_snap.to_dict()
            data["id"] = new_id
            data["process_id"] = new_id
            # metadata.file_path / gcs_url deliberately left untouched --
            # still point at the old-wrong-slug GCS source (flagged, GCS fix
            # is a separate, later thread).

            print(f"  {'[DRY RUN] ' if dry_run else ''}{old_id} -> {new_id}")
            if not dry_run:
                new_ref.set(data)
                old_ref.delete()

            stats["fixed"] += 1
        except Exception as exc:
            stats["failed"] += 1
            stats["errors"].append(f"{old_id}: {exc}")
            print(f"  FAIL  {old_id}: {exc}")

    print()
    print(f"Fixed: {stats['fixed']}  Skipped: {stats['skipped']}  Failed: {stats['failed']}")
    if stats["errors"]:
        print("Errors:")
        for e in stats["errors"]:
            print(f"  - {e}")
    return stats


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes/deletes")
    args = parser.parse_args()

    stats = fix_ids(dry_run=args.dry_run)
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
