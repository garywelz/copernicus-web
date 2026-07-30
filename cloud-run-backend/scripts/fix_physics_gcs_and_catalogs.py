#!/usr/bin/env python3
"""
One-time fix: rename physics-processes-database GCS files to match the
corrected Firestore IDs (item 22), and update the catalog files that
reference the old slugs (item 30).

Covers, per each of the 12 corrected (old_slug, new_slug) pairs:
  1. GCS: copy old.json -> new.json, old.html -> new.html (same folder),
     delete the old pair. 24 files total.
  2. Firestore: update metadata.file_path / metadata.gcs_url on the
     already-ID-corrected doc to point at the new filenames.
  3. Three catalog files that reference the old slugs by name:
     process-index.json, collections.json, whole-of-physics-graph-data.json.
     Fixed via a plain string substitution of old_slug -> new_slug across
     the whole file text -- this correctly handles every reference shape
     found (bare id, "process:"-prefixed id, url path containing the slug,
     link source/target references) in one pass, since none of the 12 old
     slugs is a substring of any other (verified before writing this).
     Each file is re-validated as parseable JSON before re-upload.

Read-only discovery already done and reported before this script was
written: confirmed no self-referential slug appears inside the .html
content itself (only external DOI links), so the .html files need no
internal edits, just the rename.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import storage, firestore

BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
PREFIX = "physics-processes-database/processes"
CATALOG_FILES = [
    "physics-processes-database/process-index.json",
    "physics-processes-database/collections.json",
    "physics-processes-database/whole-of-physics-graph-data.json",
]

# (subcategory, old_slug, new_slug)
FIXES = [
    ("astrophysics", "astrophysics-higgs-mechanism", "astrophysics-big-bang-nucleosynthesis"),
    ("astrophysics", "astrophysics-particle-collision", "astrophysics-stellar-collapse-chandrasekhar-limit"),
    ("astrophysics", "astrophysics-standard-model", "astrophysics-stellar-nucleosynthesis-pp-chain"),
    ("electromagnetism", "electromagnetism-quantum-computing", "electromagnetism-maxwells-equations-to-em-waves"),
    ("electromagnetism", "electromagnetism-quantum-entanglement", "electromagnetism-electrostatic-boundary-value-problem"),
    ("electromagnetism", "electromagnetism-wave-function", "electromagnetism-electromagnetic-induction"),
    ("quantum_mechanics", "quantum_mechanics-electromagnetic-induction", "quantum_mechanics-time-independent-schrodinger-equation"),
    ("quantum_mechanics", "quantum_mechanics-electromagnetic-wave", "quantum_mechanics-quantum-tunneling-through-a-barrier"),
    ("quantum_mechanics", "quantum_mechanics-maxwells-equations", "quantum_mechanics-quantum-harmonic-oscillator"),
    ("solid_state", "solid_state-nuclear-decay", "solid_state-electronic-band-structure-bloch"),
    ("solid_state", "solid_state-nuclear-fission", "solid_state-bcs-superconductivity-cooper-pairing"),
    ("solid_state", "solid_state-nuclear-fusion", "solid_state-phonons-debye-heat-capacity"),
]

# Sanity check: no old slug may be a substring of another (or of any new
# slug), or the raw string-replace pass over the catalog files would be
# unsafe. Verified once here defensively before any writes.
_all_old = [f[1] for f in FIXES]
_all_new = [f[2] for f in FIXES]
for i, o in enumerate(_all_old):
    for j, other in enumerate(_all_old + _all_new):
        if i != j and o in other and o != other:
            raise SystemExit(f"UNSAFE: old slug {o!r} is a substring of {other!r}; aborting.")


def gcs_step(dry_run: bool) -> None:
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    print("=== GCS: rename process files ===")
    for subcat, old_slug, new_slug in FIXES:
        for ext in (".json", ".html"):
            old_path = f"{PREFIX}/{subcat}/{old_slug}{ext}"
            new_path = f"{PREFIX}/{subcat}/{new_slug}{ext}"
            old_blob = bucket.blob(old_path)
            if not old_blob.exists():
                print(f"  SKIP (missing): {old_path}")
                continue
            print(f"  {old_path} -> {new_path}")
            if not dry_run:
                bucket.copy_blob(old_blob, bucket, new_path)
                old_blob.delete()


def firestore_step(dry_run: bool) -> None:
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    col = db.collection("physics_processes")

    print()
    print("=== Firestore: update metadata.file_path / gcs_url ===")
    for subcat, old_slug, new_slug in FIXES:
        doc_ref = col.document(new_slug)  # doc ID already corrected by item 22
        snap = doc_ref.get()
        if not snap.exists:
            print(f"  SKIP (doc missing): {new_slug}")
            continue
        data = snap.to_dict() or {}
        meta = data.get("metadata", {})
        new_file_path = f"{PREFIX}/{subcat}/{new_slug}.json"
        new_gcs_url = f"gs://{BUCKET_NAME}/{new_file_path}"
        old_file_path = meta.get("file_path")
        print(f"  {new_slug}: file_path {old_file_path} -> {new_file_path}")
        if not dry_run:
            meta["file_path"] = new_file_path
            meta["gcs_url"] = new_gcs_url
            doc_ref.update({"metadata": meta})


def catalog_step(dry_run: bool) -> None:
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    print()
    print("=== Catalog files: string-substitute old slugs -> new slugs ===")
    for path in CATALOG_FILES:
        blob = bucket.blob(path)
        if not blob.exists():
            print(f"  SKIP (missing): {path}")
            continue
        content = blob.download_as_text()
        original_len = len(content)
        replacements = 0
        for _subcat, old_slug, new_slug in FIXES:
            count = content.count(old_slug)
            if count:
                content = content.replace(old_slug, new_slug)
                replacements += count
        # Validate JSON integrity before ever writing back.
        json.loads(content)
        print(f"  {path}: {replacements} substring replacements, "
              f"length {original_len} -> {len(content)}, JSON still valid")
        if not dry_run and replacements:
            blob.upload_from_string(content, content_type="application/json")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    gcs_step(args.dry_run)
    firestore_step(args.dry_run)
    catalog_step(args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
