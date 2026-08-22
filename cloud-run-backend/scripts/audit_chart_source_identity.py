#!/usr/bin/env python
"""
Audit chart-source identity: for every GLMP process chart's `sources[]`
entries, resolve the stored DOI and PMID separately against the live KE
corpus (Firestore `research_papers`) and flag collisions -- identifier not
found, identifier resolves to a different paper than the chart claims
(title mismatch), or a correct match with no abstract (a generation
blocker even when the identity is right).

Read-only. Makes no Firestore writes and edits no chart files -- a report,
not a repair tool. See
papers/claude_code_handoff_2026-08-22_chart_source_identity_errors.md for
the collision pattern this exists to catch project-wide (Napoli, the
Swint-Kruse fabricated citation, Levine/Mizushima/Xie/Takeshige PMID
swaps, etc. were all found by hand, one chart at a time -- this is that
check made repeatable). Do not treat `a1_resolve_ingest_report.jsonl` as
ground truth for whether a chart's sources are correct; that report only
tracks whether *something* was ingested, not whether it was the right
paper.

Usage:
    python scripts/audit_chart_source_identity.py \\
        --processes-root "C:\\Users\\garyw\\glmp\\glmp-v2\\processes" \\
        --out chart_source_audit.tsv

    # Spot-check a handful of charts instead of the whole corpus:
    python scripts/audit_chart_source_identity.py \\
        --processes-root ... --out ... --limit 10
"""

import argparse
import csv
import difflib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services.paper_resolver import resolve_by_identifier  # noqa: E402  -- reuse, not reimplement


def normalize_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(a: str, b: str) -> float:
    """difflib ratio on normalized titles. Not exact-match -- real titles
    vary in punctuation, subtitles, and capitalization even when correct
    (e.g. "Chemotaxis in Escherichia coli analysed by three-dimensional
    tracking" is a genuine hit for a chart that just says "Chemotaxis
    tracking"). Threshold is tuned in main(), not baked in here."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def load_chart_sources(path: Path) -> List[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  SKIP unreadable {path}: {e}", file=sys.stderr)
        return []
    chart_id = data.get("id") or path.stem
    return [(chart_id, s) for s in (data.get("sources") or []) if isinstance(s, dict)]


def audit_one_identifier(field: str, value: str, stored_title: str, mismatch_threshold: float) -> Dict[str, Any]:
    paper = resolve_by_identifier({field: value})
    if not paper:
        return {"checked_field": field, "checked_value": value, "flag": "NOT_FOUND"}

    resolved_title = paper.get("title") or ""
    sim = title_similarity(stored_title, resolved_title)
    has_abstract = bool((paper.get("abstract") or "").strip())

    if sim < mismatch_threshold:
        flag = "TITLE_MISMATCH"
    elif not has_abstract:
        flag = "NO_ABSTRACT"
    else:
        flag = "OK"

    return {
        "checked_field": field,
        "checked_value": value,
        "flag": flag,
        "resolved_paper_id": paper.get("paper_id"),
        "resolved_title": resolved_title,
        "title_similarity": round(sim, 3),
        "has_abstract": has_abstract,
    }


def audit_source(chart_id: str, source: Dict[str, Any], mismatch_threshold: float) -> List[Dict[str, Any]]:
    stored_title = source.get("title") or ""
    doi = str(source.get("doi") or "").strip()
    pmid = str(source.get("pmid") or "").strip()

    rows = []
    if not doi and not pmid:
        # Not every sources[] entry is a paper -- database links (RegulonDB),
        # books (ISBN only), etc. Record it as out-of-scope, not a failure.
        rows.append({
            "chart_id": chart_id,
            "stored_title": stored_title,
            "stored_authors": source.get("authors", ""),
            "checked_field": "",
            "checked_value": "",
            "flag": "NO_IDENTIFIERS",
            "resolved_paper_id": "",
            "resolved_title": "",
            "title_similarity": "",
            "has_abstract": "",
        })
        return rows

    for field, value in (("doi", doi), ("pmid", pmid)):
        if not value:
            continue
        result = audit_one_identifier(field, value, stored_title, mismatch_threshold)
        rows.append({
            "chart_id": chart_id,
            "stored_title": stored_title,
            "stored_authors": source.get("authors", ""),
            **result,
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processes-root", required=True, help="Root of glmp-v2/processes (all *.json scanned recursively)")
    ap.add_argument("--out", required=True, help="TSV report path")
    ap.add_argument("--limit", type=int, default=0, help="Max chart files to scan (0 = all)")
    ap.add_argument("--mismatch-threshold", type=float, default=0.5,
                     help="difflib ratio below which a resolved title counts as a mismatch (default 0.5)")
    ap.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between charts (rate-limit cushion)")
    args = ap.parse_args()

    root = Path(args.processes_root)
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    chart_files = sorted(root.rglob("*.json"))
    if args.limit:
        chart_files = chart_files[: args.limit]

    print(f"Scanning {len(chart_files)} chart files under {root}")

    all_rows: List[Dict[str, Any]] = []
    charts_with_issues = set()
    counts = {"OK": 0, "NOT_FOUND": 0, "TITLE_MISMATCH": 0, "NO_ABSTRACT": 0, "NO_IDENTIFIERS": 0}

    for i, path in enumerate(chart_files, 1):
        for chart_id, source in load_chart_sources(path):
            rows = audit_source(chart_id, source, args.mismatch_threshold)
            for r in rows:
                counts[r["flag"]] = counts.get(r["flag"], 0) + 1
                if r["flag"] in ("NOT_FOUND", "TITLE_MISMATCH", "NO_ABSTRACT"):
                    charts_with_issues.add(chart_id)
                all_rows.append(r)
        if i % 20 == 0 or i == len(chart_files):
            print(f"  {i}/{len(chart_files)} charts scanned, {len(all_rows)} source rows checked so far")
        if args.sleep:
            time.sleep(args.sleep)

    out_path = Path(args.out)
    fieldnames = [
        "chart_id", "stored_title", "stored_authors", "checked_field", "checked_value",
        "flag", "resolved_paper_id", "resolved_title", "title_similarity", "has_abstract",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)

    print("=" * 60)
    print(f"Wrote {out_path} ({len(all_rows)} rows)")
    print(f"Flag counts: {counts}")
    print(f"Charts with at least one NOT_FOUND / TITLE_MISMATCH / NO_ABSTRACT row: {len(charts_with_issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
