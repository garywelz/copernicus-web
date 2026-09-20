#!/usr/bin/env python3
"""
A2 §8 — one-hop citation-expansion pilot, now config-driven by project.

Seeds: by default, #43 researcher-cited papers then A1 chart-named papers,
to a cap of 50 (collect_seeds()) -- unchanged GLMP/ATAP behavior. Or pass
--seed-doi-file for an explicit doi,question_ids[,title,arxiv_id,admit_policy]
CSV (load_seed_file()), for seeds that don't (yet) exist in Firestore under
a matching acquisition_channel -- see that function's docstring. Every seed
carries a direction key, fixed to "references" for now; no forward
(citing-papers) mode exists yet, and none is planned for broad, highly-cited
seeds like Zomorodian-Carlsson or Otter et al. (forward expansion from those
would flood the corpus -- see TDAP_BACKFILL_RECON_2026-09-19.md Q1).

Reference lists: Crossref first, OpenAlex fallback, then (only for a seed
file entry with an arxiv_id, only if both of those came back empty)
Semantic Scholar by arXiv id -- see semanticscholar_refs_by_arxiv(). Every
reference's cited_by_count is then backfilled from OpenAlex uniformly
(_enrich_cited_by_count()), regardless of which of the three sources
supplied it, so the top-cited-in-seed gate isn't silently blind to
Crossref-sourced or Semantic-Scholar-sourced seeds.

One hop only, references direction only. Per seed, admit_policy controls
how its own references are gated: "strict" (default -- unchanged
GLMP/ATAP behavior) keeps a candidate only if at least --min-parents seeds
cite it (default 2) or it's among a single seed's most-cited references
(top --top-n-in-seed, default 5); "all_references" admits every one of
that seed's resolvable references outright, for a seed whose whole
bibliography is already on-topic. A candidate inherits the union of its
parents' question_ids. Never expand from papers this hop admits.

acquisition_channel and cited_project are CLI params (--acquisition-channel,
--cited-project), defaulting to "cited_by_collection"/"glmp" to preserve
prior behavior exactly. Production scout cron is not touched.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
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
SEMANTIC_SCHOLAR = "https://api.semanticscholar.org/graph/v1/paper"
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


def _clean_title(title: Optional[str]) -> Optional[str]:
    """Strip embedded HTML tags and collapse whitespace/newlines in a
    title (2026-09-19, TDAP tier-1 write pre-flight, Claude Chat review).
    Some Crossref records carry raw XML-to-JSON artifacts in `title`, e.g.
    a literal '<i>...</i>' and a line break (found live in this session:
    "The structure of the nervous system of the nematode\n <i>Caenorhabditis
    elegans</i>"). Verified empirically against all 124 tier-1 v2 records
    before applying this: 0 of 124 have their doc_id change as a result
    (every one of them resolves via Crossref/bioRxiv to a DOI-derived
    `crossref_<doi>`-style id -- _doc_id_for_paper() never reaches the
    title-hash fallback for any of them), so this is safe to apply before
    doc_id computation, not just cosmetic after the fact. Two of the 124
    actually had something to clean: 10.21105/joss.05791 (embedded '\\n')
    and 10.2139/ssrn.2903278 (a double space)."""
    if not isinstance(title, str) or not title:
        return title
    t = re.sub(r"<[^>]+>", "", title)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def collect_seeds(
    db, limit: int = SEED_CAP, cited_project: str = DEFAULT_CITED_PROJECT
) -> List[Dict[str, Any]]:
    """Default seed source (GLMP/ATAP behavior, now project-scoped): seeds
    already living in research_papers under a trusted acquisition_channel
    AND tagged cited_project == cited_project. Every seed dict carries
    question_ids=frozenset() and direction="references" so downstream code
    (admit()) has one shape regardless of seed source -- see
    load_seed_file() for the alternative, explicit-DOI-list source.

    cited_project filter added 2026-09-19 (TDAP round 3, Claude Chat
    review) -- closes a real cross-project seed leak, verified against
    the code before fixing: researcher_cited_intake.py hardcodes
    acquisition_channel="researcher_citation" regardless of which project
    intake'd the paper, and this function had no project filter at all.
    Once TDAP's seeds were intake'd, the next default (GLMP) run would
    have silently expanded from them too. Verified read-only before this
    change that the filter drops nothing intended: every existing
    acquisition_channel==researcher_citation doc has cited_project
    'glmp' (227/229) or 'atap' (2/229 -- a pre-existing cross-project
    leak this filter also closes, independent of TDAP); every
    acquisition_channel==glmp_chart_source_candidate doc has
    cited_project 'glmp' (274/274). Both are plain Firestore
    equality-on-equality compound queries -- confirmed live, no
    composite index required."""
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
            "arxiv_id": data.get("arxiv_id") or None,
            "admit_policy": "strict",
        })

    researcher_q = (
        col.where("acquisition_channel", "==", "researcher_citation")
        .where("cited_project", "==", cited_project)
    )
    for snap in researcher_q.stream():
        add(snap.id, snap.to_dict() or {}, "researcher_citation")
        if len(seeds) >= limit:
            return seeds[:limit]

    chart_rows: List[Tuple[int, str, Dict[str, Any]]] = []
    chart_q = (
        col.where("acquisition_channel", "==", "glmp_chart_source_candidate")
        .where("cited_project", "==", cited_project)
    )
    for snap in chart_q.stream():
        data = snap.to_dict() or {}
        n = len(data.get("named_by_charts") or [])
        chart_rows.append((n, snap.id, data))
    chart_rows.sort(key=lambda r: -r[0])
    for _n, doc_id, data in chart_rows:
        add(doc_id, data, "glmp_chart_source_candidate")
        if len(seeds) >= limit:
            break
    return seeds[:limit]


VALID_ADMIT_POLICIES = ("strict", "all_references")


def load_seed_file(path: Path) -> List[Dict[str, Any]]:
    """Explicit seed source (added 2026-09-19 for TDAP): a CSV with columns
    `doi,question_ids` (question_ids is a `|`-separated list of this
    project's question ids, e.g. "tdap-q1|tdap-q2"; may be empty), plus
    optional `title`, `arxiv_id`, and `admit_policy` columns. Used instead
    of collect_seeds() when a project's seeds aren't (yet, or ever going
    to be) tagged with a matching acquisition_channel in Firestore -- e.g.
    hand-picked TDAP seed papers that predate any TDAP acquisition.

    arxiv_id (optional): tried as a third reference-list source, after
    Crossref and OpenAlex both come back empty by DOI -- see
    semanticscholar_refs_by_arxiv(). Added 2026-09-19 because two TDAP
    seeds (SoCG/LIPIcs and ALENEX 2026 papers, neither indexed by DOI on
    Crossref or OpenAlex) turned out to have real reference lists on
    Semantic Scholar, but only when queried by arXiv id.

    admit_policy (optional, default "strict"): "strict" keeps this
    session's existing min-parents/top-N-in-seed gates (unchanged
    GLMP/ATAP behavior). "all_references" admits every one of this seed's
    resolvable references outright, no gate -- for a seed whose whole
    bibliography is already on-topic (2026-09-19, TDAP task 4, Claude
    Chat review), rather than one gated for a broad, mixed-topic seed
    like Zomorodian-Carlsson/Otter et al. Any other value is a config
    error and raises, rather than silently falling back to "strict".

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
            admit_policy = (row.get("admit_policy") or "").strip() or "strict"
            if admit_policy not in VALID_ADMIT_POLICIES:
                raise ValueError(
                    f"{path}: row {doi!r} has admit_policy={admit_policy!r}, "
                    f"expected one of {VALID_ADMIT_POLICIES} (blank means 'strict')"
                )
            seeds.append({
                "doc_id": None,
                "doi": doi,
                "title": (row.get("title") or "").strip() or None,
                "kind": "seed_file",
                "question_ids": question_ids,
                "direction": "references",
                "arxiv_id": (row.get("arxiv_id") or "").strip() or None,
                "admit_policy": admit_policy,
            })
    return seeds


def _new_attempt(source: str) -> Dict[str, Any]:
    return {"source": source, "http_status": None, "ok": False, "error": None}


def crossref_refs(doi: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Returns (refs, attempt). attempt["ok"] is True iff the request itself
    succeeded (HTTP 200 + parseable JSON) -- an empty refs list with ok=True
    is a confirmed real result (this DOI has no deposited reference list on
    Crossref); an empty refs list with ok=False means the request failed
    and emptiness is NOT confirmed. Distinguishing these two (2026-09-19,
    TDAP task 2, Claude Chat review) is the whole point: a prior version's
    bare `except: return []` made a genuine 429 read identically to a
    genuine empty result, and that exact failure mode masked a real
    Semantic Scholar rate-limit as "no references" in the round-2 dry run."""
    attempt = _new_attempt("crossref")
    url = f"{CROSSREF}/{quote(doi, safe='')}"
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": UA})
        attempt["http_status"] = resp.status_code
        if resp.status_code != 200:
            attempt["error"] = f"HTTP {resp.status_code}"
            return [], attempt
        refs = (resp.json().get("message") or {}).get("reference") or []
        attempt["ok"] = True
    except Exception as e:
        attempt["error"] = f"{type(e).__name__}: {e}"
        return [], attempt
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
    return out, attempt


def openalex_refs(doi: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Returns (refs, attempt) -- see crossref_refs() docstring for the
    ok/empty distinction this preserves. The initial referenced_works
    lookup determines attempt["ok"]; per-chunk batch-detail failures are
    recorded in attempt["batch_errors"] but don't flip ok to False on
    their own (a batch failure loses some references, it doesn't mean the
    seed has none -- that's a partial result, not a confirmed-empty one;
    the count of references actually resolved still reflects in len(out))."""
    attempt = _new_attempt("openalex")
    try:
        resp = requests.get(
            f"{OPENALEX}/doi:{quote(doi, safe='')}",
            timeout=30,
            headers={"User-Agent": UA},
            params={"select": "id,doi,referenced_works"},
        )
        attempt["http_status"] = resp.status_code
        if resp.status_code != 200:
            attempt["error"] = f"HTTP {resp.status_code}"
            return [], attempt
        ids = (resp.json() or {}).get("referenced_works") or []
        attempt["ok"] = True
    except Exception as e:
        attempt["error"] = f"{type(e).__name__}: {e}"
        return [], attempt
    out: List[Dict[str, Any]] = []
    batch_errors: List[str] = []
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
                batch_errors.append(f"batch@{i}: HTTP {r.status_code}")
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
        except Exception as e:
            batch_errors.append(f"batch@{i}: {type(e).__name__}: {e}")
            continue
        time.sleep(0.1)
    if batch_errors:
        attempt["batch_errors"] = batch_errors
    return out, attempt


def semanticscholar_refs_by_arxiv(arxiv_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Third fallback reference source (added 2026-09-19 for TDAP), tried
    only when a seed has an arxiv_id and both Crossref and OpenAlex (by
    DOI) came back empty. Semantic Scholar indexes reference lists for some
    arXiv preprints that neither of those has by DOI -- confirmed live for
    two TDAP seeds (a SoCG/LIPIcs paper not on Crossref at all, and an
    ALENEX 2026 paper too recent for either source), 28-32 references each
    via S2 keyed by arXiv id, versus zero via DOI on any other source.
    cited_by_count is deliberately left None here (not S2's own
    citationCount) -- see _enrich_cited_by_count(), which backfills every
    reference uniformly from OpenAlex regardless of source, so the
    top-cited-in-seed gate compares apples to apples. Only references with
    a DOI in externalIds are usable downstream (this pipeline is DOI-keyed
    throughout), so DOI-less S2 references are dropped, same as
    crossref_refs()/openalex_refs() already do.

    Returns (refs, attempt) -- see crossref_refs() docstring for the
    ok/empty distinction. Retries on 429/timeout (up to 3 tries, linear
    backoff) -- S2's anonymous rate limit is strict and shared per-IP
    across all callers. A first version of this function had neither the
    retry nor the ok/error distinction, and its bare `except: return []`
    made a genuine 429 (this session had hit S2's rate limit manually
    minutes earlier) read identically to a genuine empty result in the
    round-2 dry run -- both TDAP seeds this function exists for showed
    "0 refs" even though the same request succeeded seconds later by
    hand. Even with retries, a persistent 429 across all 3 attempts still
    happened once in practice (Nigmetov-Morozov, round-2 dry run) -- an
    S2 API key would very likely fix that; not obtained here."""
    attempt = _new_attempt("semanticscholar")
    refs: List[Dict[str, Any]] = []
    for try_n in range(3):
        try:
            resp = requests.get(
                f"{SEMANTIC_SCHOLAR}/arXiv:{quote(arxiv_id, safe='')}",
                timeout=30,
                headers={"User-Agent": UA},
                params={"fields": "references.title,references.externalIds"},
            )
            attempt["http_status"] = resp.status_code
            if resp.status_code == 200:
                refs = (resp.json() or {}).get("references") or []
                attempt["ok"] = True
                break
            if resp.status_code == 429 and try_n < 2:
                time.sleep(2 * (try_n + 1))
                continue
            attempt["error"] = f"HTTP {resp.status_code}"
            return [], attempt
        except Exception as e:
            if try_n < 2:
                time.sleep(2 * (try_n + 1))
                continue
            attempt["error"] = f"{type(e).__name__}: {e}"
            return [], attempt
    out: List[Dict[str, Any]] = []
    for ref in refs:
        ext = ref.get("externalIds") or {}
        rd = _norm_doi(ext.get("DOI"))
        if not rd:
            continue
        out.append({
            "doi": rd,
            "title": ref.get("title") or "",
            "cited_by_count": None,
            "source": "semanticscholar",
        })
    return out, attempt


def _enrich_cited_by_count(refs: List[Dict[str, Any]]) -> None:
    """Backfill cited_by_count from OpenAlex for any reference missing it,
    regardless of which source supplied the reference list (2026-09-19,
    TDAP task 3, Claude Chat review). Without this, the top-cited-in-seed
    admit path only ever fires for a seed that happened to resolve via
    openalex_refs() -- the only source that natively carries citation
    counts -- which silently starved 3 of 4 productive TDAP seeds of that
    admission path even though top_n_in_seed was raised to 15 for them.
    Mutates refs in place. Batched via OpenAlex's doi filter, pipe-OR up to
    50 DOIs per request (verified live, same pattern openalex_refs()
    already uses for referenced_works ids)."""
    missing = [r for r in refs if r.get("cited_by_count") is None]
    if not missing:
        return
    by_doi = {r["doi"]: r for r in missing}
    dois = list(by_doi.keys())
    for i in range(0, len(dois), 50):
        chunk = dois[i : i + 50]
        filt = "|".join(chunk)
        try:
            r = requests.get(
                OPENALEX,
                timeout=45,
                headers={"User-Agent": UA},
                params={"filter": f"doi:{filt}", "per-page": 50, "select": "doi,cited_by_count"},
            )
            if r.status_code != 200:
                continue
            for item in (r.json() or {}).get("results") or []:
                rd = _norm_doi(item.get("doi"))
                if rd and rd in by_doi:
                    by_doi[rd]["cited_by_count"] = item.get("cited_by_count")
        except Exception:
            continue
        time.sleep(0.1)


def fetch_seed_refs(
    doi: str, arxiv_id: Optional[str] = None, enrich_cited_by_count: bool = False
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    """Returns (refs, source, fetch_status). fetch_status["status"] is one
    of three states (2026-09-19, TDAP task 2, Claude Chat review) -- never
    collapsed into a single ambiguous "none" the way source used to be:
      "ok"    -- got 1+ references from some source.
      "empty" -- every source actually tried responded successfully (ok=
                 True) but all confirmed zero references. A real result,
                 not a failure -- e.g. a thin Crossref record with no
                 deposited bibliography.
      "error" -- refs is empty AND at least one tried source failed
                 (non-200 or exception) -- emptiness is NOT confirmed,
                 unlike "empty". This is exactly the state a bare
                 `except: return []` used to make indistinguishable from
                 "empty", which is what let a real S2 429 read as "no
                 references" in the round-2 dry run.
    fetch_status["attempts"] carries every attempt dict tried, in order,
    for the full report.

    enrich_cited_by_count (default False, 2026-09-19, TDAP round 3 --
    Claude Chat review, option B): gates _enrich_cited_by_count(). A
    regression check against pre-change commit 528db05c5 found that
    enriching unconditionally (as this session's first version did)
    changes GLMP's own default-args output too -- top_cited_in_seed
    admissions jumped 15 -> 172 purely from previously-Crossref-only
    GLMP seeds gaining a cited_by_count for the first time. That's a
    real behavior change riding along on TDAP work, and top_cited_in_seed
    is already recorded (this doc's Limits) as structurally
    popularity-biased -- not something to silently turn on for GLMP as
    a side effect. Default False restores byte-for-byte GLMP parity;
    TDAP passes True explicitly via --enrich-cited-by-count."""
    attempts: List[Dict[str, Any]] = []
    refs, a = crossref_refs(doi)
    attempts.append(a)
    source = "crossref"
    if not refs:
        refs, a = openalex_refs(doi)
        attempts.append(a)
        source = "openalex"
    if not refs and arxiv_id:
        refs, a = semanticscholar_refs_by_arxiv(arxiv_id)
        attempts.append(a)
        source = "semanticscholar"
    if enrich_cited_by_count:
        _enrich_cited_by_count(refs)
    time.sleep(0.35)

    if refs:
        status = "ok"
    elif all(att["ok"] for att in attempts):
        status = "empty"
    else:
        status = "error"
    if not refs:
        source = "none"
    return refs, source, {"status": status, "attempts": attempts}


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

    # all_references seeds admit every one of their own resolvable
    # references outright (2026-09-19, TDAP task 4, Claude Chat review) --
    # for a seed whose whole bibliography is already on-topic (tdap-q1/q2's
    # computational-topology seeds), the min-parents/top-N gates built for
    # a broad, mixed-topic seed like Zomorodian-Carlsson/Otter et al. just
    # under-yield. Runs after the two gated passes above so it can merge
    # into an already-kept candidate's parents rather than duplicate it.
    # Seeds keep "strict" (default, unchanged GLMP/ATAP behavior) unless a
    # seed file explicitly opts one in -- e.g. tdap-q3's seeds stay strict,
    # since their bibliographies are mostly non-TDA neuroscience.
    for seed in seeds:
        if seed.get("admit_policy") != "all_references":
            continue
        for ref in per_seed_refs.get(seed["doi"], []):
            rd = ref["doi"]
            if rd in seed_dois:
                continue
            if rd in keep:
                if seed["doi"] not in keep[rd]["parents"]:
                    keep[rd]["parents"].append(seed["doi"])
                    keep[rd]["question_ids"] = keep[rd]["question_ids"] | seed_qids.get(seed["doi"], frozenset())
                continue
            row = dict(ref)
            row["parents"] = [seed["doi"]]
            row["reason"] = "all_references_from_seed"
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
    parser.add_argument(
        "--enrich-cited-by-count", action="store_true",
        help="Backfill cited_by_count from OpenAlex for every reference regardless of source "
             "(default: off, preserving prior GLMP behavior exactly -- a regression check found "
             "enabling this unconditionally changes GLMP's own default output too, since "
             "top_cited_in_seed already runs for every seed and just does nothing for a reference "
             "with no count. TDAP passes this flag explicitly; GLMP does not by default).",
    )
    parser.add_argument(
        "--batch-new-cap", type=int, default=BATCH_NEW_CAP,
        help=f"max new Firestore documents created in one --write run (default: {BATCH_NEW_CAP}). "
             "Only matters with --write; a dry run's would_create count is never capped.",
    )
    parser.add_argument(
        "--only-dois-file", type=Path, default=None,
        help="Restrict processing (report + --write) to admitted candidates whose DOI appears in "
             "this file (one DOI per line, blank lines and '#'-prefixed lines ignored). Filters "
             "AFTER admit() -- seed collection and the admit gates still see every seed's full "
             "reference list, so cited_by_2plus_seeds/top_cited_in_seed decisions are unaffected; "
             "this only trims what gets resolved/reported/written. For a tiered write (2026-09-19, "
             "TDAP task 3): write a trusted subset now, hold the rest for later review.",
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
        seeds = collect_seeds(db, limit=args.seed_cap, cited_project=args.cited_project)
        print(f"Seeds: {len(seeds)}  "
              f"researcher={sum(1 for s in seeds if s['kind']=='researcher_citation')}  "
              f"chart={sum(1 for s in seeds if s['kind']=='glmp_chart_source_candidate')}")

    per_seed: Dict[str, List[Dict[str, Any]]] = {}
    source_counts = defaultdict(int)
    seed_fetch_log: List[Dict[str, Any]] = []
    status_counts = defaultdict(int)
    for i, seed in enumerate(seeds, 1):
        refs, src, fetch_status = fetch_seed_refs(
            seed["doi"], arxiv_id=seed.get("arxiv_id"), enrich_cited_by_count=args.enrich_cited_by_count
        )
        per_seed[seed["doi"]] = refs
        source_counts[src] += 1
        status_counts[fetch_status["status"]] += 1
        seed_fetch_log.append({
            "seed_doi": seed["doi"],
            "seed_title": seed.get("title"),
            "status": fetch_status["status"],
            "final_source": src,
            "ref_count": len(refs),
            "attempts": fetch_status["attempts"],
        })
        policy_flag = " [all_references]" if seed.get("admit_policy") == "all_references" else ""
        status_flag = f" ({fetch_status['status']})" if fetch_status["status"] != "ok" else ""
        print(f"  [{i}/{len(seeds)}] {src:14} {len(refs):3} refs{status_flag}  {seed['doi']}  "
              f"{(seed.get('title') or '')[:50]}{policy_flag}")
        if fetch_status["status"] == "error":
            for att in fetch_status["attempts"]:
                if not att["ok"]:
                    print(f"      [error] {att['source']}: http_status={att['http_status']} error={att['error']}")

    candidates = admit(seeds, per_seed, top_n_in_seed=args.top_n_in_seed, min_parents=args.min_parents)
    print(f"Admitted after gates: {len(candidates)}  "
          f"(2+ seeds: {sum(1 for c in candidates if c['reason']=='cited_by_2plus_seeds')}, "
          f"top-in-seed: {sum(1 for c in candidates if c['reason']=='top_cited_in_seed')}, "
          f"all_references: {sum(1 for c in candidates if c['reason']=='all_references_from_seed')})")
    print(f"Ref source by seed: {dict(source_counts)}")

    if args.only_dois_file:
        with args.only_dois_file.open(encoding="utf-8-sig") as fh:
            only_dois = {
                _norm_doi(line) for line in fh
                if line.strip() and not line.strip().startswith("#")
            }
        only_dois.discard(None)
        before_n = len(candidates)
        candidates = [c for c in candidates if c["doi"] in only_dois]
        print(f"--only-dois-file {args.only_dois_file}: {before_n} admitted -> "
              f"{len(candidates)} selected ({len(only_dois)} DOIs listed)")
    print(f"Ref fetch status by seed: {dict(status_counts)}"
          + ("  <-- 'error' means emptiness is NOT confirmed, see per-seed [error] lines above"
             if status_counts.get("error") else ""))

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
                "ref_fetch_status": dict(status_counts),
                "seed_fetch_log": seed_fetch_log,
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
            record["title"] = _clean_title(record.get("title"))
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
                if new_writes >= args.batch_new_cap:
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
                "source": cand.get("source"),
            }, ensure_ascii=False) + "\n")
            if i % 20 == 0 or i == len(candidates):
                print(f"  ingest [{i}/{len(candidates)}] {counts}")

    print("============================================================")
    print(json.dumps(counts, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
