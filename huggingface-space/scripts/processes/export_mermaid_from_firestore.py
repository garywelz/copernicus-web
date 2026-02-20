#!/usr/bin/env python3
"""
Export Mermaid flowcharts from Firestore into a local folder tree that can be used
as a restore source for `restore_mermaid_from_source.py`.

This is designed specifically to recover "old good graphs" after local JSONs were
overwritten, while keeping citations/sources in the local JSONs untouched.

Writes files like:
  <out-root>/processes/<subcategory>/<process-id>.json

Each exported file contains at minimum:
  { "id": "...", "subcategory": "...", "mermaid_code": "graph TD ..." }

Usage (CS):
  python3 scripts/processes/export_mermaid_from_firestore.py \
    --project regal-scholar-453620-r7 \
    --database copernicusai \
    --collection computer_science_processes \
    --metadata computer-science-processes-database/metadata.json \
    --out-root firestore-export/computer-science-processes-database

Then restore into local JSONs:
  python3 scripts/processes/restore_mermaid_from_source.py \
    --db-dir computer-science-processes-database \
    --source-root firestore-export/computer-science-processes-database/processes
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import firestore


def _read_metadata_ids(metadata_path: Path) -> List[str]:
    meta = json.loads(metadata_path.read_text(encoding="utf-8"))
    procs = meta.get("processes") or []
    ids: List[str] = []
    for p in procs:
        if isinstance(p, dict) and p.get("id"):
            ids.append(str(p["id"]))
    return ids


def _guess_subcategory_from_id(pid: str) -> str:
    return pid.split("-", 1)[0] if "-" in pid else "unknown"


def _extract_mermaid(doc: Dict[str, Any]) -> str:
    return (
        (doc.get("mermaid_code") or "")
        or (doc.get("mermaid") or "")
        or (doc.get("mermaid_syntax") or "")
        or (doc.get("flowchart") or "")
    ).strip()


def _try_get_doc(coll, pid: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Try common historical doc-id patterns.
    Returns (doc_id, doc_dict) or (None, None).
    """
    sub = _guess_subcategory_from_id(pid)
    candidates = [
        pid,
        f"processes-{sub}-{pid}",
        f"processes/{sub}/{pid}",
    ]
    for doc_id in candidates:
        snap = coll.document(doc_id).get()
        if snap.exists:
            return snap.id, (snap.to_dict() or {})

    # Try field-based lookup (different doc ids)
    try:
        snaps = list(coll.where("process_id", "==", pid).limit(1).stream())
        if snaps:
            snap = snaps[0]
            return snap.id, (snap.to_dict() or {})
    except Exception:
        pass

    return None, None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="regal-scholar-453620-r7")
    ap.add_argument("--database", default="copernicusai", help='Firestore database name (e.g. "copernicusai" or "(default)")')
    ap.add_argument("--collection", required=True, help="e.g. computer_science_processes")
    ap.add_argument("--metadata", required=True, help="Path to metadata.json listing the target process IDs")
    ap.add_argument("--out-root", required=True, help="Output folder (will be created).")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    ids = _read_metadata_ids(Path(args.metadata))
    if args.limit:
        ids = ids[: args.limit]

    db = firestore.Client(project=args.project, database=args.database)
    coll = db.collection(args.collection)

    out_root = Path(args.out_root)
    processes_root = out_root / "processes"
    processes_root.mkdir(parents=True, exist_ok=True)

    exported = 0
    missing: List[str] = []
    no_mermaid: List[str] = []

    for pid in ids:
        _, doc = _try_get_doc(coll, pid)
        if not doc:
            missing.append(pid)
            continue
        mermaid = _extract_mermaid(doc)
        if not mermaid:
            no_mermaid.append(pid)
            continue
        sub = (doc.get("subcategory") or _guess_subcategory_from_id(pid)).strip()
        out_path = processes_root / sub / f"{pid}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"id": pid, "subcategory": sub, "mermaid_code": mermaid}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        exported += 1

    print(json.dumps({"exported": exported, "missing_docs": len(missing), "missing_mermaid": len(no_mermaid), "out_root": str(out_root)}, indent=2))
    if missing:
        print("\nMissing docs (first 20):")
        for pid in missing[:20]:
            print(f"- {pid}")
    if no_mermaid:
        print("\nDocs missing mermaid fields (first 20):")
        for pid in no_mermaid[:20]:
            print(f"- {pid}")


if __name__ == "__main__":
    main()

