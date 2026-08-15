#!/usr/bin/env python3
"""
A1.0 — harvest unique papers named in GLMP process `sources` arrays.

Writes a candidate manifest only. Does not rewrite chart JSON, does not
elect a canonical source, and does not ingest to Firestore. See
A1-glmp-source-backfill-plan.md (2026-08-15): papers enter later as
`glmp_chart_source_candidate` evidence.

Default input: huggingface-space/glmp-processes-database/processes/*.json
in this checkout. The v2 gap TSV is not present here; pass --tsv when it is.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROCESSES = SCRIPT_DIR.parent.parent / "glmp-processes-database" / "processes"
DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


def _normalize_doi(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    text = str(raw).strip()
    match = DOI_RE.search(text)
    if not match:
        return None
    doi = match.group(0).rstrip(".,;)]")
    return doi.lower()


def _normalize_pmid(raw: Optional[str]) -> Optional[str]:
    if raw is None or raw == "":
        return None
    digits = re.sub(r"\D", "", str(raw))
    return digits or None


def _iter_process_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.glob("*.json")):
        if path.name == "metadata.json":
            continue
        yield path


def _load_sources(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chart_id = data.get("id") or data.get("process_id") or path.stem
    sources = data.get("sources") or []
    if not isinstance(sources, list):
        return str(chart_id), []
    return str(chart_id), [s for s in sources if isinstance(s, dict)]


def harvest_processes(root: Path) -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    for path in _iter_process_files(root):
        chart_id, sources = _load_sources(path)
        for src in sources:
            doi = _normalize_doi(src.get("doi"))
            pmid = _normalize_pmid(src.get("pmid"))
            if not doi and not pmid:
                continue
            key = f"doi:{doi}" if doi else f"pmid:{pmid}"
            row = by_key.setdefault(
                key,
                {
                    "doi": doi,
                    "pmid": pmid,
                    "title": (src.get("title") or "").strip() or None,
                    "paper_id": src.get("paper_id"),
                    "chart_ids": [],
                    "source_files": [],
                },
            )
            if chart_id not in row["chart_ids"]:
                row["chart_ids"].append(chart_id)
            rel = str(path.as_posix())
            if rel not in row["source_files"]:
                row["source_files"].append(rel)
            if not row.get("title") and src.get("title"):
                row["title"] = str(src["title"]).strip()
            if not row.get("pmid") and pmid:
                row["pmid"] = pmid
            if not row.get("doi") and doi:
                row["doi"] = doi
    rows = list(by_key.values())
    rows.sort(key=lambda r: (-len(r["chart_ids"]), r.get("doi") or r.get("pmid") or ""))
    return rows


def harvest_tsv(path: Path) -> List[Dict[str, Any]]:
    """Optional second input when the v2 gap report is available."""
    import csv

    by_key: Dict[str, Dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for rec in reader:
            doi = _normalize_doi(rec.get("doi") or rec.get("DOI"))
            pmid = _normalize_pmid(rec.get("pmid") or rec.get("PMID"))
            if not doi and not pmid:
                continue
            key = f"doi:{doi}" if doi else f"pmid:{pmid}"
            chart_id = rec.get("chart_id") or rec.get("process_id") or rec.get("id")
            row = by_key.setdefault(
                key,
                {
                    "doi": doi,
                    "pmid": pmid,
                    "title": (rec.get("title") or "").strip() or None,
                    "paper_id": rec.get("paper_id"),
                    "chart_ids": [],
                    "source_files": [str(path.as_posix())],
                },
            )
            if chart_id and chart_id not in row["chart_ids"]:
                row["chart_ids"].append(str(chart_id))
    rows = list(by_key.values())
    rows.sort(key=lambda r: (-len(r["chart_ids"]), r.get("doi") or r.get("pmid") or ""))
    return rows


def merge_rows(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            key = f"doi:{row['doi']}" if row.get("doi") else f"pmid:{row.get('pmid')}"
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = {
                    **row,
                    "chart_ids": list(row.get("chart_ids") or []),
                    "source_files": list(row.get("source_files") or []),
                }
                continue
            for chart_id in row.get("chart_ids") or []:
                if chart_id not in existing["chart_ids"]:
                    existing["chart_ids"].append(chart_id)
            for src in row.get("source_files") or []:
                if src not in existing["source_files"]:
                    existing["source_files"].append(src)
            if not existing.get("title") and row.get("title"):
                existing["title"] = row["title"]
    merged = list(by_key.values())
    merged.sort(key=lambda r: (-len(r["chart_ids"]), r.get("doi") or r.get("pmid") or ""))
    return merged


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processes-dir",
        type=Path,
        default=DEFAULT_PROCESSES,
        help="Directory of GLMP process JSON files",
    )
    parser.add_argument(
        "--tsv",
        type=Path,
        default=None,
        help="Optional v2 gap-report TSV (not required to start A1.0)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_DIR / "a1_chart_source_candidates.jsonl",
        help="JSONL manifest path",
    )
    args = parser.parse_args()

    groups: List[List[Dict[str, Any]]] = []
    if args.processes_dir.is_dir():
        groups.append(harvest_processes(args.processes_dir))
    else:
        print(f"Processes dir missing: {args.processes_dir}", file=sys.stderr)
        return 2
    if args.tsv:
        if not args.tsv.is_file():
            print(f"TSV missing: {args.tsv}", file=sys.stderr)
            return 2
        groups.append(harvest_tsv(args.tsv))

    rows = merge_rows(*groups)
    charts = set()
    for row in rows:
        charts.update(row["chart_ids"])

    payload_meta = {
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "acquisition_channel": "glmp_chart_source_candidate",
        "canonical_association": False,
        "unique_papers": len(rows),
        "distinct_charts": len(charts),
        "processes_dir": str(args.processes_dir),
        "tsv": str(args.tsv) if args.tsv else None,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_meta": payload_meta}, ensure_ascii=False) + "\n")
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    multi = sum(1 for r in rows if len(r["chart_ids"]) > 1)
    print(f"Unique papers with DOI or PMID: {len(rows)}")
    print(f"Distinct charts naming them:    {len(charts)}")
    print(f"Papers named by 2+ charts:      {multi}")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
