#!/usr/bin/env python3
"""Convert HTML process charts to canonical JSON under processes/<subcategory>/."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from publish import extract_mermaid
from schema import DEFAULT_COLOR_SCHEME, infer_process_type, subcategory_label

SCRIPT_DIR = Path(__file__).resolve().parent
HF_ROOT = SCRIPT_DIR.parent.parent

SKIP_HTML_NAMES = {
    "index.html",
    "README.html",
    "schema.html",
    "pilot-summary.html",
    "design-notes.html",
    "proof-graph-schema-v2.html",
}


def database_root(name: str) -> Path:
    return HF_ROOT / name


def title_from_html(content: str, fallback: str) -> str:
    match = re.search(r"<title>([^<]+)</title>", content, re.IGNORECASE)
    if not match:
        return fallback.replace("-", " ").title()
    title = html_lib.unescape(match.group(1).strip())
    title = re.sub(r"\s*-\s*Mathematics Process\s*$", "", title, flags=re.I)
    title = re.sub(r"\s*-\s*Proof Graph\s*$", "", title, flags=re.I)
    return title.strip() or fallback.replace("-", " ").title()


def description_from_html(content: str) -> str:
    patterns = [
        r'<div class="description"[^>]*>.*?<p[^>]*>(.*?)</p>',
        r'<p[^>]*>(.*?)</p>',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            text = re.sub(r"<[^>]+>", "", match.group(1))
            text = html_lib.unescape(re.sub(r"\s+", " ", text)).strip()
            if len(text) > 40:
                return text[:1200]
    return ""


def process_id_from_path(path: Path, subcategory: str) -> str:
    stem = path.stem
    if stem.startswith(f"{subcategory}-"):
        return stem
    if subcategory == "proof_graphs":
        return stem
    return f"{subcategory}-{stem}"


def build_json_doc(
    *,
    path: Path,
    subcategory: str,
    content: str,
    mermaid: str,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    pid = process_id_from_path(path, subcategory)
    today = date.today().isoformat()
    doc: dict[str, Any] = {
        "id": pid,
        "name": title_from_html(content, path.stem),
        "category": "mathematics",
        "subcategory": subcategory,
        "subcategory_name": subcategory_label(subcategory),
        "description": description_from_html(content) or f"Process chart: {path.stem}",
        "mermaid": mermaid,
        "colorScheme": DEFAULT_COLOR_SCHEME,
        "keywords": [],
        "sources": [],
        "relatedProcesses": [],
        "created": today,
        "lastUpdated": today,
        "verified": True,
        "flowchartStandard": "GLMP_6color",
    }
    if subcategory == "proof_graphs":
        doc["processType"] = "proof_graph"
        doc["graphType"] = "proof_graph"
    if existing:
        for key in (
            "name",
            "description",
            "complexity",
            "keywords",
            "sources",
            "relatedProcesses",
            "processType",
            "graphType",
            "created",
        ):
            if existing.get(key):
                doc[key] = existing[key]
        if existing.get("mermaid") and len(existing["mermaid"]) >= len(mermaid):
            doc["mermaid"] = existing["mermaid"]
    doc["processType"] = infer_process_type(doc)
    return doc


def iter_chart_sources(db_root: Path) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    processes_dir = db_root / "processes"
    if processes_dir.exists():
        for path in sorted(processes_dir.rglob("*.html")):
            if "_archive" in path.parts or path.parent.name == "graph_type_pilots":
                continue
            if path.name in SKIP_HTML_NAMES:
                continue
            items.append((path, path.parent.name))

    proof_dir = db_root / "proof-graphs"
    if proof_dir.exists():
        for path in sorted(proof_dir.glob("*.html")):
            if path.name in SKIP_HTML_NAMES:
                continue
            items.append((path, "proof_graphs"))
        for path in sorted(proof_dir.glob("*.md")):
            if path.name in {n.replace(".html", ".md") for n in SKIP_HTML_NAMES}:
                continue
            if path.stem in {"README", "design-notes", "schema", "pilot-summary", "proof-graph-schema-v2"}:
                continue
            items.append((path, "proof_graphs"))
    return items


def convert_database(db_name: str, *, dry_run: bool = False, overwrite: bool = False) -> dict[str, Any]:
    db_root = database_root(db_name)
    created = 0
    updated = 0
    skipped: list[str] = []

    for html_path, subcategory in iter_chart_sources(db_root):
        content = html_path.read_text(encoding="utf-8", errors="replace")
        mermaid = extract_mermaid(content)
        if not mermaid:
            skipped.append(f"{html_path.relative_to(db_root)}: no mermaid")
            continue

        pid = process_id_from_path(html_path, subcategory)
        out_path = db_root / "processes" / subcategory / f"{pid}.json"
        existing = None
        if out_path.exists():
            with out_path.open(encoding="utf-8") as fh:
                existing = json.load(fh)
            if existing.get("mermaid") and not overwrite:
                skipped.append(f"{out_path.relative_to(db_root)}: already has mermaid")
                continue

        doc = build_json_doc(
            path=html_path,
            subcategory=subcategory,
            content=content,
            mermaid=mermaid,
            existing=existing,
        )
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if existing:
            updated += 1
        else:
            created += 1

    return {
        "database": db_name,
        "created": created,
        "updated": updated,
        "skipped": len(skipped),
        "skippedSamples": skipped[:25],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="mathematics-processes-database")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing mermaid from HTML")
    args = parser.parse_args()
    result = convert_database(args.database, dry_run=args.dry_run, overwrite=args.overwrite)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
