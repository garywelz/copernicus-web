#!/usr/bin/env python3
"""Remove non-canonical process JSON from GCS and orphan docs from Firestore."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
HF_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_BUCKET = "regal-scholar-453620-r7-podcast-storage"
FIRESTORE_COLLECTION = "math_processes"


def canonical_ids(db_name: str) -> set[str]:
    meta_path = HF_ROOT / db_name / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {p["id"] for p in meta["processes"]}


def prune_gcs(db_name: str, bucket: str, canonical: set[str], *, apply: bool) -> dict:
    from collections import defaultdict

    from google.cloud import storage

    client = storage.Client()
    b = client.bucket(bucket)
    prefix = f"{db_name}/processes/"
    by_id: dict[str, list[str]] = defaultdict(list)
    orphan_paths: list[str] = []

    for blob in b.list_blobs(prefix=prefix):
        if not blob.name.endswith(".json"):
            continue
        try:
            data = json.loads(blob.download_as_text())
            pid = data.get("id") or blob.name.rsplit("/", 1)[-1].replace(".json", "")
        except Exception:
            pid = blob.name.rsplit("/", 1)[-1].replace(".json", "")
        if pid not in canonical:
            orphan_paths.append(blob.name)
        else:
            by_id[pid].append(blob.name)

    duplicate_paths: list[str] = []
    for paths in by_id.values():
        if len(paths) <= 1:
            continue
        keep = max(paths, key=lambda p: p.count("/"))
        duplicate_paths.extend(p for p in paths if p != keep)

    to_delete = orphan_paths + duplicate_paths
    kept = sum(1 for paths in by_id.values() for _ in paths) - len(duplicate_paths)

    if apply:
        for name in to_delete:
            b.blob(name).delete()

    return {
        "gcs_kept": len(by_id),
        "gcs_deleted": len(to_delete),
        "gcs_orphans": orphan_paths,
        "gcs_duplicates": duplicate_paths,
    }


def prune_firestore(canonical: set[str], *, apply: bool) -> dict:
    from google.cloud import firestore

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    coll = db.collection(FIRESTORE_COLLECTION)
    to_delete: list[str] = []
    kept = 0

    for doc in coll.stream():
        if doc.id in canonical:
            kept += 1
        else:
            to_delete.append(doc.id)

    if apply:
        for i in range(0, len(to_delete), 400):
            batch = db.batch()
            for doc_id in to_delete[i : i + 400]:
                batch.delete(coll.document(doc_id))
            batch.commit()

    return {"firestore_kept": kept, "firestore_deleted": len(to_delete), "firestore_ids": to_delete}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="mathematics-processes-database")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    canonical = canonical_ids(args.database)
    gcs = prune_gcs(args.database, args.bucket, canonical, apply=args.apply)
    fs = prune_firestore(canonical, apply=args.apply)

    report = {
        "database": args.database,
        "canonical_count": len(canonical),
        "apply": args.apply,
        **gcs,
        **fs,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
