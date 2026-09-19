#!/usr/bin/env python3
"""
A2 §8 — one-hop citation-expansion pilot, now config-driven by project.

Seeds: by default, #43 researcher-cited papers then A1 chart-named papers,
to a cap of 50 (collect_seeds()) -- unchanged GLMP/ATAP behavior. Or pass
--seed-doi-file for an explicit doi,question_ids CSV (load_seed_file()),
for seeds that don't (yet) exist in Firestore under a matching
acquisition_channel -- see that function's docstring. Every seed carries a
direction key, fixed to "references" for now; no forward (citing-papers)
mode exists yet, and none is planned for broad, highly-cited seeds like
Zomorodian-Carlsson or Otter et al. (forward expansion from those would
flood the corpus -- see TDAP_BACKFILL_RECON_2026-09-19.md Q1).

One hop only, references direction only. A candidate is kept if at least
--min-parents seeds cite it (default 2), or it is among the most-cited
references of a single seed (OpenAlex cited_by_count, top --top-n-in-seed,
default 5). A candidate inherits the union of its parents' question_ids.
Never expand from papers this hop admits.

acquisition_channel and cited_project are CLI params (--acquisition-channel,
--cited-project), defaulting to "cited_by_collection"/"glmp" to preserve
prior behavior exactly. Production scout cron is not touched.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

import requests
from google.cloud import firestore

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
A1_PATH = SCRIPT_DIR / "a1_resolve_and_ingest.py"
INGEST_PATH = REPO_ROOT / "cloud-run-backend" / "scripts" / "ingest_papers_from_metadata_json.py"
DEFAULT_REPORT = SCRIPT_DIR / "citation_expansion_pilot_report.jsonl"

UA = "CopernicusAI/1.0 (mailto:gwelz@gc.cuny.edu)"
CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
SEED_CAP = 50
# PER_SEED_CAP (formerly 8) removed 2026-09-19 (TDAP): the per-seed reference
# loop already slices to top_n_in_seed candidates before this cap could ever
# apply (dead check since the cap was always looser than the slice) -- see
# TDAP_BACKFILL_RECON_2026-09-19.md Q4. top_n_in_seed is now the one real
# per-seed ceiling, and it's a CLI param (--top-n-in-seed) instead of a
# module constant so each initiative can tune it without editing this file.
TOP_N_IN_SEED = 5
DEFAULT_MIN_PARENTS = 2
DEFAULT_CITED_PROJECT = "glmp"
DEFAULT_ACQUISITION_CHANNEL = "cited_by_collection"
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
    """Default seed source (unchanged GLMP/ATAP behavior): seeds already
    living in research_papers under a trusted acquisition_channel. Every
    seed dict carries question_ids=frozenset() and direction="references"
    so downstream code (admit()) has one shape regardless of seed source --
    see load_seed_file() for the alternative, explicit-DOI-list source."""
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
            "question_ids": frozenset(),
            "direction": "references",
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


def load_seed_file(path: Path) -> List[Dict[str, Any]]:
    """Explicit seed source (added 2026-09-19 for TDAP): a CSV with columns
    `doi,question_ids` (question_ids is a `|`-separated list of this
    project's question ids, e.g. "tdap-q1|tdap-q2"; may be empty). Used
    instead of collect_seeds() when a project's seeds aren't (yet, or ever
    going to be) tagged with a matching acquisition_channel in Firestore --
    e.g. six hand-picked TDAP seed papers that predate any TDAP acquisition.

    Seeds loaded this way are NOT thereby added to research_papers -- this
    script only ever writes admitted *candidates*, never the seeds
    themselves. Seed papers must be intake'd separately (e.g. via
    researcher_cited_intake.py) if they should also be corpus members.
    direction is fixed to "references" for every seed loaded here; no
    forward (citing-papers) mode exists yet (see module docstring)."""
    seeds: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "doi" not in reader.fieldnames:
            raise ValueError(f"{path}: expected a CSV header with a 'doi' column, got {reader.fieldnames}")
        for row in reader:
            doi = _norm_doi(row.get("doi"))
            if not doi:
                continue
            if doi in seen:
                print(f"  [seed-file] duplicate DOI skipped: {doi}")
                continue
            seen.add(doi)
            raw_qids = (row.get("question_ids") or "").strip()
            question_ids = frozenset(q.strip() for q in raw_qids.split("|") if q.strip())
            seeds.append({
                "doc_id": None,
                "doi": doi,
                "title": (row.get("title") or "").strip() or None,
                "kind": "seed_file",
                "question_ids": question_ids,
                "direction": "references",
            })
    return seeds


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


def admit(
    seeds: List[Dict[str, Any]],
    per_seed_refs: Dict[str, List[Dict[str, Any]]],
    top_n_in_seed: int = TOP_N_IN_SEED,
    min_parents: int = DEFAULT_MIN_PARENTS,
) -> List[Dict[str, Any]]:
    seed_dois = {s["doi"] for s in seeds}
    # doi -> union of question_ids across every parent seed that named it.
    # A candidate's question_ids is the union of its parents' questions
    # (Claude Chat review, 2026-09-19) -- seeds stay in one run rather than
    # split by question, since the min-parents rule depends on seeing all
    # seeds together.
    seed_qids: Dict[str, frozenset] = {s["doi"]: s.get("question_ids") or frozenset() for s in seeds}
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

    def _qids_for(parents: List[str]) -> Set[str]:
        out: Set[str] = set()
        for p in parents:
            out |= seed_qids.get(p, frozenset())
        return out

    keep: Dict[str, Dict[str, Any]] = {}
    for doi, parents in cited_by.items():
        if len(parents) >= min_parents:
            row = dict(meta[doi])
            row["parents"] = parents
            row["reason"] = "cited_by_2plus_seeds"
            row["question_ids"] = _qids_for(parents)
            keep[doi] = row

    for seed in seeds:
        refs = [
            r for r in per_seed_refs.get(seed["doi"], [])
            if r["doi"] not in seed_dois and r.get("cited_by_count") is not None
        ]
        scored = sorted(refs, key=lambda r: r.get("cited_by_count") or 0, reverse=True)[:top_n_in_seed]
        for ref in scored:
            rd = ref["doi"]
            if rd in keep:
                if seed["doi"] not in keep[rd]["parents"]:
                    keep[rd]["parents"].append(seed["doi"])
                    keep[rd]["question_ids"] = keep[rd]["question_ids"] | seed_qids.get(seed["doi"], frozenset())
                continue
            row = dict(ref)
            row["parents"] = [seed["doi"]]
            row["reason"] = "top_cited_in_seed"
            row["question_ids"] = set(seed_qids.get(seed["doi"], frozenset()))
            keep[rd] = row

    rows = list(keep.values())
    rows.sort(key=lambda r: (-len(r["parents"]), -(r.get("cited_by_count") or 0)))
    # JSON-safe from here out: question_ids is built as a set above (union
    # arithmetic needs set semantics), but every consumer downstream --
    # including the "unresolved" report line's **cand spread -- needs a
    # plain list. Converting once here, at the return boundary, beats
    # converting at every call site and re-introducing this bug.
    for row in rows:
        row["question_ids"] = sorted(row.get("question_ids") or [])
    return rows


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-cap", type=int, default=SEED_CAP)
    parser.add_argument(
        "--seed-doi-file", type=Path, default=None,
        help="CSV with columns doi,question_ids (question_ids '|'-separated, e.g. "
             "'tdap-q1|tdap-q2', may be empty) -- explicit seed list, replacing the "
             "default Firestore acquisition_channel query (see load_seed_file()). "
             "Omit to keep existing GLMP/ATAP behavior (collect_seeds()).",
    )
    parser.add_argument(
        "--cited-project", default=DEFAULT_CITED_PROJECT,
        help=f"cited_project stamped on every admitted/merged record (default: {DEFAULT_CITED_PROJECT!r}, "
             "preserving prior behavior).",
    )
    parser.add_argument(
        "--acquisition-channel", default=DEFAULT_ACQUISITION_CHANNEL,
        help=f"acquisition_channel stamped on newly-created records (default: {DEFAULT_ACQUISITION_CHANNEL!r}, "
             "preserving prior behavior).",
    )
    parser.add_argument(
        "--min-parents", type=int, default=DEFAULT_MIN_PARENTS,
        help=f"admit a candidate if at least this many seeds cite it (default: {DEFAULT_MIN_PARENTS}).",
    )
    parser.add_argument(
        "--top-n-in-seed", type=int, default=TOP_N_IN_SEED,
        help=f"per-seed cap on top-cited-in-seed candidates (default: {TOP_N_IN_SEED}, preserving "
             "prior behavior; TDAP expects to raise this since 6 seeds at top-5 under-yields).",
    )
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
    if args.seed_doi_file:
        seeds = load_seed_file(args.seed_doi_file)[: args.seed_cap]
        print(f"Seeds: {len(seeds)} (from {args.seed_doi_file}, seed_cap={args.seed_cap})  "
              f"with_question_ids={sum(1 for s in seeds if s['question_ids'])}")
    else:
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

    candidates = admit(seeds, per_seed, top_n_in_seed=args.top_n_in_seed, min_parents=args.min_parents)
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

            record["acquisition_channel"] = args.acquisition_channel
            record["parent_paper_ids"] = cand["parents"]
            record["cited_by"] = "citation_expansion_pilot"
            record["cited_date"] = cited_date
            record["cited_project"] = args.cited_project
            record["cited_context"] = f"{CITED_CONTEXT} reason={cand['reason']}"
            # Union of parents' question_ids (Q5 gap closed: the pilot never
            # set cited_for_question before, so question_scope_ids never
            # populated -- ingest_papers_from_metadata_json.py's derivation
            # only understands a single cited_for_question value, not a set,
            # so it's applied directly here rather than through that field.
            qids = sorted(cand.get("question_ids") or [])

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
                        update["acquisition_channel"] = args.acquisition_channel
                    if qids:
                        update["question_scope_ids"] = firestore.ArrayUnion(qids)
                    citations = list(existing.get("citations") or [])
                    event = {
                        "cited_by": record["cited_by"],
                        "cited_date": cited_date,
                        "cited_context": record["cited_context"],
                        "cited_project": args.cited_project,
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
                    if qids:
                        doc["question_scope_ids"] = sorted(set(doc.get("question_scope_ids") or []) | set(qids))
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
                "question_ids": qids,
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
