#!/usr/bin/env python3
"""Identify and relocate superseded process-chart files out of active collections."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
HF_ROOT = SCRIPT_DIR.parent.parent
ARCHIVE_ROOT = HF_ROOT / "_archive" / "superseded"


SUPERSEDED_MANIFEST = {
    "description": "Files and trees superseded by JSON-canonical mathematics-processes-database",
    "lastUpdated": None,
    "archiveMoves": [
        {
            "source": "math-processes",
            "reason": "Phase-1 pilot tree; replaced by mathematics-processes-database",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_01.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_02.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_03.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_04.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_05.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_06.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_batch_07.html",
            "reason": "Early batch HTML; superseded by per-process JSON/HTML",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_index.html",
            "reason": "Early index; superseded by mathematics-database-table.html",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics_processes.html",
            "reason": "Early listing; superseded by mathematics-database-table.html",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics-database-table.html",
            "reason": "Duplicate table; canonical copy in mathematics-processes-database/",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/infinitely-many-primes.html",
            "reason": "Superseded by infinitely-many-primes-v2-demo.html",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/infinitely-many-primes.md",
            "reason": "Superseded by infinitely-many-primes-v2-demo",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/euclid-book-i-pilot.html",
            "reason": "Pilot chart; not in canonical collection",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/euclid-book-i-pilot.md",
            "reason": "Pilot chart source; not in canonical collection",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/pilot-summary.html",
            "reason": "Pilot summary doc; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/pilot-summary.md",
            "reason": "Pilot summary doc; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/schema.html",
            "reason": "Schema documentation; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/schema.md",
            "reason": "Schema documentation; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/proof-graph-schema-v2.html",
            "reason": "Schema documentation; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/proof-graphs/proof-graph-schema-v2.md",
            "reason": "Schema documentation; not a process chart",
        },
        {
            "source": "huggingface-space/mathematics-processes-database/processes/graph_type_pilots",
            "reason": "Graph-type pilots; excluded from production catalog",
        },
        {
            "source": "huggingface-space/programming-framework/mathematics-processes-database",
            "reason": "Early duplicate math database tree; canonical copy is mathematics-processes-database/",
        },
    ],
}


def resolve_source(rel: str) -> Path:
    path = REPO_ROOT / rel
    if path.exists():
        return path
    return HF_ROOT.parent / rel if rel.startswith("huggingface-space/") else path


def archive_destination(source: Path) -> Path:
    try:
        rel = source.relative_to(REPO_ROOT)
    except ValueError:
        rel = Path(source.name)
    return ARCHIVE_ROOT / rel


def audit(*, apply: bool = False) -> dict:
    manifest = dict(SUPERSEDED_MANIFEST)
    manifest["lastUpdated"] = date.today().isoformat()
    found: list[dict] = []
    moved: list[str] = []
    missing: list[str] = []

    for entry in manifest["archiveMoves"]:
        rel = entry["source"]
        source = resolve_source(rel)
        record = {"source": rel, "reason": entry["reason"], "exists": source.exists()}
        found.append(record)
        if not source.exists():
            missing.append(rel)
            continue
        if apply:
            dest = archive_destination(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
            shutil.move(str(source), str(dest))
            moved.append(f"{rel} -> {dest.relative_to(REPO_ROOT)}")

    manifest_path = ARCHIVE_ROOT / "superseded_manifest.json"
    if apply:
        ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "archiveRoot": str(ARCHIVE_ROOT.relative_to(REPO_ROOT)),
        "candidates": len(found),
        "existing": sum(1 for f in found if f["exists"]),
        "missing": missing,
        "moved": moved,
        "apply": apply,
        "items": found,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Move files to _archive/superseded/")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args()
    result = audit(apply=args.apply and not args.dry_run)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
