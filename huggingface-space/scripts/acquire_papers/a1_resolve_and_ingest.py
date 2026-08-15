#!/usr/bin/env python3
"""
A1.0 — resolve harvested chart-named papers and write them to Firestore.

Records a file fact: current GLMP charts name this paper
(`named_by_charts`, `acquisition_channel=glmp_chart_source_candidate`).
Does not rewrite chart JSON and does not certify a chart as verified.

Reuse: researcher_cited_intake resolvers + ingest_papers_from_metadata_json
identity / Firestore shape. Dedup: merge attribution onto an existing
research_papers doc; create only when absent.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
INGEST_PATH = REPO_ROOT / "cloud-run-backend" / "scripts" / "ingest_papers_from_metadata_json.py"
DEFAULT_MANIFEST = SCRIPT_DIR / "a1_chart_source_candidates.jsonl"
DEFAULT_REPORT = SCRIPT_DIR / "a1_resolve_ingest_report.jsonl"

CITED_BY = "glmp_chart_sources"
CITED_PROJECT = "glmp"
CITED_CONTEXT = (
    "Named in current GLMP chart source lists. Charts are the best current "
    "approximation of a process, not a verified canonical result."
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _load_manifest(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("_meta"):
            continue
        rows.append(rec)
    return rows


def resolve_pmid_eutils(pmid: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """PubMed esummary without Biopython — NCBI E-utilities JSON."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    try:
        resp = requests.get(
            url,
            params={
                "db": "pubmed",
                "id": pmid,
                "retmode": "json",
                "tool": "CopernicusAI",
                "email": "gary@copernicusai.fyi",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None, f"PubMed esummary HTTP {resp.status_code} for PMID {pmid}"
        result = (resp.json().get("result") or {})
        rec = result.get(str(pmid))
        if not rec:
            return None, f"PMID not found via esummary: {pmid}"
    except Exception as e:
        return None, f"PubMed esummary failed for PMID {pmid}: {e}"

    title = rec.get("title") or "Untitled"
    authors = []
    for a in rec.get("authors") or []:
        name = a.get("name") if isinstance(a, dict) else None
        if name:
            authors.append(name)
    doi = None
    for aid in rec.get("articleids") or []:
        if isinstance(aid, dict) and str(aid.get("idtype") or "").lower() == "doi":
            doi = str(aid.get("value") or "").strip() or None
            break
    year = ""
    pubdate = str(rec.get("pubdate") or "")
    if len(pubdate) >= 4 and pubdate[:4].isdigit():
        year = pubdate[:4]
    paper = {
        "id": f"pubmed_{pmid}",
        "pmid": str(pmid),
        "title": title,
        "authors": authors,
        "author_string": ", ".join(authors[:8]),
        "journal": rec.get("fulljournalname") or rec.get("source") or "",
        "year": year,
        "abstract": "",
        "doi": doi,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
        "source": "pubmed",
        "acquired_date": datetime.now(timezone.utc).isoformat(),
        "category": "biology",
    }
    return paper, None


def resolve_doi_encoded(doi: str, parse_crossref_item) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Retry Crossref with a fully encoded DOI path (parentheses, etc.)."""
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    try:
        resp = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"},
        )
        if resp.status_code != 200:
            return None, f"DOI not found via Crossref (encoded): {doi}"
        item = (resp.json() or {}).get("message") or {}
        rec = parse_crossref_item(item)
        if rec:
            return rec, None
        return None, f"encoded Crossref matched but failed to parse: {doi}"
    except Exception as e:
        return None, f"encoded Crossref failed for {doi}: {e}"


def _norm_title(text: Optional[str]) -> str:
    return "".join(c.lower() for c in (text or "") if c.isalnum())


def titles_match(harvest: Optional[str], resolved: Optional[str]) -> bool:
    """Chart-file PMIDs are often the wrong paper. Require a title overlap
    before attributing named_by_charts. No harvest title → reject."""
    a, b = _norm_title(harvest), _norm_title(resolved)
    if len(a) < 12 or len(b) < 12:
        return False
    return a[:28] in b or b[:28] in a


def _stamp(record: Dict[str, Any], row: Dict[str, Any], cited_date: str) -> Dict[str, Any]:
    charts = list(row.get("chart_ids") or [])
    out = dict(record)
    out["acquisition_channel"] = "glmp_chart_source_candidate"
    out["named_by_charts"] = charts
    out["cited_by"] = CITED_BY
    out["cited_date"] = cited_date
    out["cited_project"] = CITED_PROJECT
    out["cited_context"] = CITED_CONTEXT
    return out


def _repair_mismatches(args) -> int:
    """Undo named_by_charts written when PubMed PMID != harvest title."""
    from google.cloud import firestore

    harvest_rows = _load_manifest(args.manifest)
    by_pmid = {str(r["pmid"]): r for r in harvest_rows if r.get("pmid")}
    by_doi = {(r.get("doi") or "").lower(): r for r in harvest_rows if r.get("doi")}

    report_path = args.report
    if not report_path.is_file():
        report_path = DEFAULT_REPORT.with_name("a1_resolve_ingest_report_retry.jsonl")
    if not report_path.is_file():
        print(f"No report to repair: {report_path}", file=sys.stderr)
        return 2

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    col = db.collection("research_papers")
    stripped = 0
    skipped = 0
    for line in report_path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec.get("status") not in ("merged", "created"):
            continue
        harvest = by_pmid.get(str(rec.get("pmid") or "")) or by_doi.get((rec.get("doi") or "").lower())
        if harvest and titles_match(harvest.get("title"), rec.get("title")):
            skipped += 1
            continue
        doc_id = rec.get("doc_id")
        if not doc_id:
            continue
        snap = col.document(doc_id).get()
        if not snap.exists:
            continue
        data = snap.to_dict() or {}
        charts = set(rec.get("named_by_charts") or harvest and harvest.get("chart_ids") or [])
        remaining = [c for c in (data.get("named_by_charts") or []) if c not in charts]
        citations = [
            c for c in (data.get("citations") or [])
            if not (
                c.get("cited_by") == CITED_BY
                and c.get("cited_context") == CITED_CONTEXT
            )
        ]
        update = {
            "named_by_charts": remaining,
            "citations": citations,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        if args.write:
            col.document(doc_id).update(update)
            stripped += 1
        else:
            stripped += 1
        print(f"{'STRIP' if args.write else 'would_strip'} {doc_id}  harvest={(harvest or {}).get('title', '')[:50]!r}  resolved={rec.get('title', '')[:50]!r}")
    print(f"title-ok left in place: {skipped}; mismatch attributions {'stripped' if args.write else 'would strip'}: {stripped}")
    return 0


def _merge_onto_existing(db, col, doc_id: str, record: Dict[str, Any], write: bool) -> str:
    from google.cloud import firestore

    doc_ref = col.document(doc_id)
    existing = doc_ref.get().to_dict() or {}
    charts = record.get("named_by_charts") or []
    update: Dict[str, Any] = {
        "named_by_charts": firestore.ArrayUnion(charts),
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    # Do not overwrite a more specific channel (researcher_citation, scout, …).
    if not existing.get("acquisition_channel"):
        update["acquisition_channel"] = "glmp_chart_source_candidate"

    citations = list(existing.get("citations") or [])
    event = {
        "cited_by": record.get("cited_by"),
        "cited_date": record.get("cited_date"),
        "cited_context": record.get("cited_context"),
        "cited_project": record.get("cited_project"),
    }
    event = {k: v for k, v in event.items() if v}
    if event and event not in citations:
        citations.append(event)
        update["citations"] = citations
        update.update(event)

    if write:
        doc_ref.update(update)
        return "merged"
    return "would_merge"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=0, help="0 = all")
    parser.add_argument("--sleep", type=float, default=0.0, help="Extra pause after each resolve")
    parser.add_argument("--write", action="store_true", help="Write to Firestore (default is dry-run)")
    parser.add_argument(
        "--retry-unresolved",
        action="store_true",
        help="Only retry rows marked unresolved in --report (reads the previous report first)",
    )
    parser.add_argument(
        "--repair-mismatches",
        action="store_true",
        help="Strip named_by_charts from docs whose resolved title does not match the harvest title",
    )
    args = parser.parse_args()

    if args.repair_mismatches:
        return _repair_mismatches(args)

    if not args.manifest.is_file():
        print(f"Manifest missing: {args.manifest}", file=sys.stderr)
        return 2

    intake = _load_module("researcher_cited_intake", SCRIPT_DIR / "researcher_cited_intake.py")
    ingest = _load_module("ingest_papers_from_metadata_json", INGEST_PATH)

    mods = {
        "crossref": intake._load_module("acquire_crossref_batch", "acquire_crossref_batch.py"),
        "pubmed": intake._load_module("acquire_pubmed_batch", "acquire_pubmed_batch.py"),
        "arxiv": intake._load_module("acquire_arxiv_batch", "acquire_arxiv_batch.py"),
        "nasa_ads": intake._load_module("acquire_nasa_ads_batch", "acquire_nasa_ads_batch.py"),
        "biorxiv": intake._load_module("acquire_biorxiv_medrxiv_batch", "acquire_biorxiv_medrxiv_batch.py"),
    }

    from google.cloud import firestore

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    col = db.collection("research_papers")

    rows = _load_manifest(args.manifest)
    if args.retry_unresolved and args.report.is_file():
        want = set()
        for line in args.report.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("status") == "unresolved":
                want.add((rec.get("doi") or "", str(rec.get("pmid") or "")))
        rows = [r for r in rows if (r.get("doi") or "", str(r.get("pmid") or "")) in want]
        print(f"Retrying {len(rows)} previously unresolved rows")
        if args.report == DEFAULT_REPORT:
            args.report = DEFAULT_REPORT.with_name("a1_resolve_ingest_report_retry.jsonl")
    if args.limit:
        rows = rows[: args.limit]
    cited_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    counts = {
        "resolved": 0,
        "created": 0,
        "merged": 0,
        "unresolved": 0,
        "failed": 0,
        "would_create": 0,
        "would_merge": 0,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report_fh = args.report.open("w", encoding="utf-8")

    try:
        for i, row in enumerate(rows, 1):
            doi = row.get("doi")
            pmid = row.get("pmid")
            record = None
            err = None
            if doi:
                record, err = intake.resolve_doi(doi, mods)
                if record is None:
                    record, err = resolve_doi_encoded(doi, mods["crossref"].parse_crossref_item)
            if record is None and pmid:
                record, err = intake.resolve_pmid(str(pmid), mods)
                if record is None:
                    record, err = resolve_pmid_eutils(str(pmid))
                    time.sleep(0.35)
            if record is not None and not titles_match(row.get("title"), record.get("title")):
                counts["unresolved"] += 1
                report_fh.write(json.dumps({
                    "status": "title_mismatch",
                    "doi": doi,
                    "pmid": pmid,
                    "harvest_title": row.get("title"),
                    "resolved_title": record.get("title"),
                    "chart_ids": row.get("chart_ids"),
                }, ensure_ascii=False) + "\n")
                print(f"[{i}/{len(rows)}] TITLE MISMATCH {doi or pmid}")
                record = None
                continue
            if record is None:
                counts["unresolved"] += 1
                report_fh.write(json.dumps({
                    "status": "unresolved",
                    "doi": doi,
                    "pmid": pmid,
                    "title": row.get("title"),
                    "error": err,
                    "chart_ids": row.get("chart_ids"),
                }, ensure_ascii=False) + "\n")
                print(f"[{i}/{len(rows)}] UNRESOLVED {doi or pmid}: {err}")
                continue

            counts["resolved"] += 1
            record = _stamp(record, row, cited_date)
            doc_id = ingest._doc_id_for_paper(record)
            snap = col.document(doc_id).get()
            exists = snap.exists
            if not exists:
                # Ingest id may differ from a prior scout id (DOI vs PMID).
                dup, _note = intake.check_firestore_duplicate(record)
                if dup:
                    exists = True
                    doc_id = dup["doc_id"]

            try:
                if exists:
                    action = _merge_onto_existing(db, col, doc_id, record, write=args.write)
                    counts["merged" if action == "merged" else "would_merge"] += 1
                else:
                    doc = ingest._to_firestore_paper(record, Path(f"a1/{record.get('id')}.json"))
                    if args.write:
                        col.document(doc_id).create(doc)
                        counts["created"] += 1
                        action = "created"
                    else:
                        counts["would_create"] += 1
                        action = "would_create"
            except Exception as e:
                counts["failed"] += 1
                action = f"failed:{type(e).__name__}"
                report_fh.write(json.dumps({
                    "status": "failed",
                    "doc_id": doc_id,
                    "doi": doi,
                    "pmid": pmid,
                    "error": str(e),
                }, ensure_ascii=False) + "\n")
                print(f"[{i}/{len(rows)}] FAIL {doc_id}: {e}")
                continue

            report_fh.write(json.dumps({
                "status": action,
                "doc_id": doc_id,
                "doi": record.get("doi"),
                "pmid": record.get("pmid"),
                "title": record.get("title"),
                "named_by_charts": record.get("named_by_charts"),
            }, ensure_ascii=False) + "\n")
            if i % 25 == 0 or i == len(rows):
                print(f"[{i}/{len(rows)}] {action} {doc_id}  {counts}")
            if args.sleep:
                time.sleep(args.sleep)
    finally:
        report_fh.close()

    print("============================================================")
    print(f"Write: {bool(args.write)}")
    print(json.dumps(counts, indent=2))
    print(f"Report: {args.report}")
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
