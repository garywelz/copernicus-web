#!/usr/bin/env python3
"""
A2 §8 — 50-seed one-hop citation-expansion pilot.

Seeds: #43 researcher-cited papers, then A1 chart-named papers, to a
cap of 50. One hop only. A candidate is kept if two or more seeds cite
it, or it is among the most-cited references of a seed (OpenAlex
cited_by_count, top 5, cap 8 per seed). Never expand from papers this
hop admits.

Channel: cited_by_collection. Production scout cron is not touched.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from google.cloud import firestore

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
A1_PATH = SCRIPT_DIR / "a1_resolve_and_ingest.py"
INGEST_PATH = REPO_ROOT / "cloud-run-backend" / "scripts" / "ingest_papers_from_metadata_json.py"
DEFAULT_REPORT = SCRIPT_DIR / "citation_expansion_pilot_report.jsonl"

UA = "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"
CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
SEED_CAP = 50
PER_SEED_CAP = 8
TOP_N_IN_SEED = 5
BATCH_NEW_CAP = 200
CITED_CONTEXT = (
    "One-hop citation expansion from a trusted seed (researcher-cited or "
    "chart-named). Not a certified source."
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm_doi(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    d = str(raw).strip()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "")
    d = d.replace("https://dx.doi.org/", "").replace("doi:", "")
    d = d.strip().lower().rstrip(".,;")
    return d or None


def collect_seeds(db, limit: int = SEED_CAP) -> List[Dict[str, Any]]:
    col = db.collection("research_papers")
    seeds: List[Dict[str, Any]] = []
    seen = set()

    def add(doc_id: str, data: Dict[str, Any], kind: str) -> None:
        doi = _norm_doi(data.get("doi"))
        if not doi or doi in seen:
            return
        seen.add(doi)
        seeds.append({
            "doc_id": doc_id,
            "doi": doi,
            "title": data.get("title"),
            "kind": kind,
        })

    for snap in col.where("acquisition_channel", "==", "researcher_citation").stream():
        add(snap.id, snap.to_dict() or {}, "researcher_citation")
        if len(seeds) >= limit:
            return seeds[:limit]

    chart_rows: List[Tuple[int, str, Dict[str, Any]]] = []
    for snap in col.where("acquisition_channel", "==", "glmp_chart_source_candidate").stream():
        data = snap.to_dict() or {}
        n = len(data.get("named_by_charts") or [])
        chart_rows.append((n, snap.id, data))
    chart_rows.sort(key=lambda r: -r[0])
    for _n, doc_id, data in chart_rows:
        add(doc_id, data, "glmp_chart_source_candidate")
        if len(seeds) >= limit:
            break
    return seeds[:limit]


def crossref_refs(doi: str) -> List[Dict[str, Any]]:
    url = f"{CROSSREF}/{quote(doi, safe='')}"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
        if resp.status_code != 200:
            return []
        refs = (resp.json().get("message") or {}).get("reference") or []
    except Exception:
        return []
    out = []
    for ref in refs:
        rd = _norm_doi(ref.get("DOI"))
        if not rd:
            continue
        out.append({
            "doi": rd,
            "title": ref.get("article-title") or ref.get("unstructured") or "",
            "cited_by_count": None,
            "source": "crossref",
        })
    return out


def openalex_refs(doi: str) -> List[Dict[str, Any]]:
    try:
        resp = requests.get(
            f"{OPENALEX}/doi:{quote(doi, safe='')}",
            timeout=30,
            headers={"User-Agent": UA},
            params={"select": "id,doi,referenced_works"},
        )
        if resp.status_code != 200:
            return []
        ids = (resp.json() or {}).get("referenced_works") or []
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for i in range(0, len(ids), 50):
        chunk = [w.rsplit("/", 1)[-1] for w in ids[i : i + 50]]
        filt = "|".join(chunk)
        try:
            r = requests.get(
                OPENALEX,
                timeout=45,
                headers={"User-Agent": UA},
                params={
                    "filter": f"openalex_id:{filt}",
                    "per-page": 50,
                    "select": "doi,title,cited_by_count",
                },
            )
            if r.status_code != 200:
                continue
            for item in (r.json() or {}).get("results") or []:
                rd = _norm_doi(item.get("doi"))
                if not rd:
                    continue
                out.append({
                    "doi": rd,
                    "title": item.get("title") or "",
                    "cited_by_count": item.get("cited_by_count"),
                    "source": "openalex",
                })
        except Exception:
            continue
        time.sleep(0.1)
    return out


def fetch_seed_refs(doi: str) -> Tuple[List[Dict[str, Any]], str]:
    refs = crossref_refs(doi)
    source = "crossref"
    if not refs:
        refs = openalex_refs(doi)
        source = "openalex" if refs else "none"
    time.sleep(0.35)
    return refs, source


def admit(seeds: List[Dict[str, Any]], per_seed_refs: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    seed_dois = {s["doi"] for s in seeds}
    cited_by: Dict[str, List[str]] = defaultdict(list)
    meta: Dict[str, Dict[str, Any]] = {}
    for seed in seeds:
        for ref in per_seed_refs.get(seed["doi"], []):
            rd = ref["doi"]
            if rd in seed_dois:
                continue
            if seed["doi"] not in cited_by[rd]:
                cited_by[rd].append(seed["doi"])
            prev = meta.get(rd)
            if prev is None or (ref.get("cited_by_count") or 0) > (prev.get("cited_by_count") or 0):
                meta[rd] = ref

    keep: Dict[str, Dict[str, Any]] = {}
    for doi, parents in cited_by.items():
        if len(parents) >= 2:
            row = dict(meta[doi])
            row["parents"] = parents
            row["reason"] = "cited_by_2plus_seeds"
            keep[doi] = row

    for seed in seeds:
        refs = [
            r for r in per_seed_refs.get(seed["doi"], [])
            if r["doi"] not in seed_dois and r.get("cited_by_count") is not None
        ]
        scored = sorted(refs, key=lambda r: r.get("cited_by_count") or 0, reverse=True)[:TOP_N_IN_SEED]
        added = 0
        for ref in scored:
            if added >= PER_SEED_CAP:
                break
            rd = ref["doi"]
            if rd in keep:
                if seed["doi"] not in keep[rd]["parents"]:
                    keep[rd]["parents"].append(seed["doi"])
                continue
            row = dict(ref)
            row["parents"] = [seed["doi"]]
            row["reason"] = "top_cited_in_seed"
            keep[rd] = row
            added += 1

    rows = list(keep.values())
    rows.sort(key=lambda r: (-len(r["parents"]), -(r.get("cited_by_count") or 0)))
    return rows


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-cap", type=int, default=SEED_CAP)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    a1 = _load_module("a1_resolve_and_ingest", A1_PATH)
    intake = _load_module("researcher_cited_intake", SCRIPT_DIR / "researcher_cited_intake.py")
    ingest = _load_module("ingest_papers_from_metadata_json", INGEST_PATH)
    mods = {
        "crossref": intake._load_module("acquire_crossref_batch", "acquire_crossref_batch.py"),
        "pubmed": intake._load_module("acquire_pubmed_batch", "acquire_pubmed_batch.py"),
        "arxiv": intake._load_module("acquire_arxiv_batch", "acquire_arxiv_batch.py"),
        "nasa_ads": intake._load_module("acquire_nasa_ads_batch", "acquire_nasa_ads_batch.py"),
        "biorxiv": intake._load_module("acquire_biorxiv_medrxiv_batch", "acquire_biorxiv_medrxiv_batch.py"),
    }

    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    col = db.collection("research_papers")
    seeds = collect_seeds(db, limit=args.seed_cap)
    print(f"Seeds: {len(seeds)}  "
          f"researcher={sum(1 for s in seeds if s['kind']=='researcher_citation')}  "
          f"chart={sum(1 for s in seeds if s['kind']=='glmp_chart_source_candidate')}")

    per_seed: Dict[str, List[Dict[str, Any]]] = {}
    source_counts = defaultdict(int)
    for i, seed in enumerate(seeds, 1):
        refs, src = fetch_seed_refs(seed["doi"])
        per_seed[seed["doi"]] = refs
        source_counts[src] += 1
        print(f"  [{i}/{len(seeds)}] {src:8} {len(refs):3} refs  {seed['doi']}  { (seed.get('title') or '')[:50]}")

    candidates = admit(seeds, per_seed)
    print(f"Admitted after gates: {len(candidates)}  "
          f"(2+ seeds: {sum(1 for c in candidates if c['reason']=='cited_by_2plus_seeds')}, "
          f"top-in-seed: {sum(1 for c in candidates if c['reason']=='top_cited_in_seed')})")
    print(f"Ref source by seed: {dict(source_counts)}")

    counts = {
        "seeds": len(seeds),
        "admitted": len(candidates),
        "already_in_corpus": 0,
        "created": 0,
        "merged": 0,
        "unresolved": 0,
        "title_mismatch": 0,
        "new_capped": 0,
        "would_create": 0,
        "would_merge": 0,
    }
    cited_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    new_writes = 0

    with args.report.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "_meta": {
                "ran_at": datetime.now(timezone.utc).isoformat(),
                "write": bool(args.write),
                "seeds": len(seeds),
                "ref_sources": dict(source_counts),
            }
        }, ensure_ascii=False) + "\n")
        for i, cand in enumerate(candidates, 1):
            record, err = intake.resolve_doi(cand["doi"], mods)
            if record is None:
                record, err = a1.resolve_doi_encoded(cand["doi"], mods["crossref"].parse_crossref_item)
            if record is None:
                counts["unresolved"] += 1
                fh.write(json.dumps({"status": "unresolved", **cand, "error": err}, ensure_ascii=False) + "\n")
                continue
            if cand.get("title") and not a1.titles_match(cand.get("title"), record.get("title")):
                # Harvest title from Crossref/OpenAlex can be thin; allow if cand title empty.
                if len(a1._norm_title(cand.get("title"))) >= 12:
                    counts["title_mismatch"] += 1
                    fh.write(json.dumps({
                        "status": "title_mismatch",
                        "doi": cand["doi"],
                        "harvest_title": cand.get("title"),
                        "resolved_title": record.get("title"),
                    }, ensure_ascii=False) + "\n")
                    continue

            record["acquisition_channel"] = "cited_by_collection"
            record["parent_paper_ids"] = cand["parents"]
            record["cited_by"] = "citation_expansion_pilot"
            record["cited_date"] = cited_date
            record["cited_project"] = "glmp"
            record["cited_context"] = f"{CITED_CONTEXT} reason={cand['reason']}"

            doc_id = ingest._doc_id_for_paper(record)
            snap = col.document(doc_id).get()
            exists = snap.exists
            if not exists:
                dup, _note = intake.check_firestore_duplicate(record)
                if dup:
                    exists = True
                    doc_id = dup["doc_id"]

            if exists:
                counts["already_in_corpus"] += 1
                if args.write:
                    existing = col.document(doc_id).get().to_dict() or {}
                    update = {
                        "parent_paper_ids": firestore.ArrayUnion(cand["parents"]),
                        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    }
                    if not existing.get("acquisition_channel"):
                        update["acquisition_channel"] = "cited_by_collection"
                    citations = list(existing.get("citations") or [])
                    event = {
                        "cited_by": record["cited_by"],
                        "cited_date": cited_date,
                        "cited_context": record["cited_context"],
                        "cited_project": "glmp",
                    }
                    if event not in citations:
                        citations.append(event)
                        update["citations"] = citations
                    col.document(doc_id).update(update)
                    counts["merged"] += 1
                    action = "merged"
                else:
                    counts["would_merge"] += 1
                    action = "would_merge"
            else:
                if new_writes >= BATCH_NEW_CAP:
                    counts["new_capped"] += 1
                    action = "capped"
                elif args.write:
                    doc = ingest._to_firestore_paper(record, Path(f"pilot/{record.get('id')}.json"))
                    col.document(doc_id).create(doc)
                    counts["created"] += 1
                    new_writes += 1
                    action = "created"
                else:
                    counts["would_create"] += 1
                    action = "would_create"

            fh.write(json.dumps({
                "status": action,
                "doc_id": doc_id,
                "doi": cand["doi"],
                "title": record.get("title"),
                "reason": cand["reason"],
                "parents": cand["parents"],
                "cited_by_count": cand.get("cited_by_count"),
            }, ensure_ascii=False) + "\n")
            if i % 20 == 0 or i == len(candidates):
                print(f"  ingest [{i}/{len(candidates)}] {counts}")

    print("============================================================")
    print(json.dumps(counts, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
