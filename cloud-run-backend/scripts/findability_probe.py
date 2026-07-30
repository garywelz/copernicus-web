#!/usr/bin/env python3
"""
Findability probe (v1) — "is this content actually retrievable?" not just
"does it exist?"

Three checks:
  A. Positive findability — real anchor queries through the live
     /api/vector-search/semantic endpoint (not a direct search_semantic()
     call: this probe exists to catch deploy/config drift between the source
     tree and what's actually served, so it must hit what a real caller hits).
     Fail on a live-query collection = ALERT.
  B. Coverage integrity — doc count vs. embedded count vs. index-covered
     count per collection, by measured dimension (never by embedding_model
     label alone).
  C. Index/collection consistency — every vector index maps to a collection
     with matching-dimension data; every queried collection has a READY
     index at its data's dimension.
     B/C fail on an embedded-but-not-live-queried collection = WARNING.

v1 does NOT check ID/title/content identity (that's Check D, deferred —
see GLMP_MASTER_TODO.md item 22).

Coverage note (Check B honesty statement): research_papers is large enough
that a full per-doc dimension scan is expensive, so it is SAMPLED (300 docs).
All other collections are small enough (<=237 docs) to be FULL-SCANNED. A
sampled check can miss a small pocket of wrong-dimension docs; this script
states that limitation in its own output rather than implying a uniform
guarantee across collections of very different size.

Output: a JSON report (see build_report()) suitable for build_master_todo.py
to read as a new SourceResult, following the same pattern as its other
read_*() functions (read_regression_summary, read_decoder_circuits, etc.).
Not yet wired into that chain -- this is Gate 3 (standalone, run manually).
Gate 4 (hook integration) is separate and must fail soft in the chain.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from google.cloud import firestore
from google.cloud import firestore_admin_v1

PROJECT_ID = "regal-scholar-453620-r7"
DATABASE_ID = "copernicusai"
API_BASE_URL = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"
SEMANTIC_ENDPOINT = f"{API_BASE_URL}/api/vector-search/semantic"

RESEARCH_PAPERS_SAMPLE_SIZE = 300
TOP_K = 5

# ── Collections in scope ────────────────────────────────────────────────────
# "large" collections use count() aggregation + a sample for dimension check.
# "small" collections are cheap enough to full-scan for an exact dimension
# distribution -- no sampling uncertainty for these.
LARGE_COLLECTIONS = ["research_papers"]
SMALL_LIVE_QUERY_COLLECTIONS = [
    "episodes",
    "glmp_processes",
    "atap_graphs",
    "chemistry_processes",
    "physics_processes",
    "computer_science_processes",
    "biology_processes",
]
# Embedded but not a find_nearest target anywhere in the codebase today
# (confirmed by source grep, 2026-07-28) -- included in B/C, excluded from A.
NON_QUERIED_EMBEDDED_COLLECTIONS = ["podcast_jobs"]

ALL_COLLECTIONS = LARGE_COLLECTIONS + SMALL_LIVE_QUERY_COLLECTIONS + NON_QUERIED_EMBEDDED_COLLECTIONS

# content_types param the API expects, per collection.
CONTENT_TYPE_PARAM = {
    "research_papers": "papers",
    "episodes": "podcasts",
    "glmp_processes": "glmp",
    "atap_graphs": "math",
    "chemistry_processes": "chemistry",
    "physics_processes": "physics",
    "computer_science_processes": "computer_science",
    "biology_processes": "biology",
}

# JSON response key the API returns results under, per collection.
# NOTE: atap_graphs's response key is still "math_processes" -- deliberately
# unchanged during the migration (see GLMP_MASTER_TODO.md, atap_graphs
# migration entry) to avoid touching frontend/RAG/CLI consumers. Not a bug.
RESPONSE_KEY = {
    "research_papers": "papers",
    "episodes": "podcasts",
    "glmp_processes": "glmp_processes",
    "atap_graphs": "math_processes",
    "chemistry_processes": "chemistry_processes",
    "physics_processes": "physics_processes",
    "computer_science_processes": "computer_science_processes",
    "biology_processes": "biology_processes",
}

# id field name per result-item shape, in priority order.
ID_FIELD_CANDIDATES = ["paper_id", "job_id", "process_id", "id"]

# ── Anchors: (query, expected_doc_id) per collection ────────────────────────
# Semantic queries (query != title) so a pass proves embedding retrieval, not
# keyword luck. IDs confirmed live before this script was written (2026-07-28).
ANCHORS: Dict[str, List[Dict[str, str]]] = {
    "research_papers": [
        {
            "query": "annotation-free integration for cell identity recovery",
            "expected_id": "biorxiv_10.64898_2026.05.14.725078",
        },
    ],
    "atap_graphs": [
        {"query": "field extension degree", "expected_id": "abstract_algebra-field-theory-extensions"},
        {"query": "diagonalization", "expected_id": "cantor-diagonal-proofs"},
    ],
    "glmp_processes": [
        {"query": "lactose metabolism switch", "expected_id": "ecoli_lac_operon"},
        {"query": "negative feedback loop", "expected_id": "synthetic_negative_autoregulation"},
    ],
    "chemistry_processes": [
        {
            "query": "measuring unknown concentration from a standard series",
            "expected_id": "analytical_chemistry-calibration-curve-construction",
        },
        {
            "query": "sweeping electrode voltage to measure redox reaction kinetics",
            "expected_id": "electrochemistry-cyclic-voltammetry",
        },
    ],
    "computer_science_processes": [
        {
            "query": "keeping a tree balanced as data is inserted",
            "expected_id": "algorithms_data_structures-balanced-search-trees",
        },
        {"query": "distributing traffic across servers", "expected_id": "networks-load-balancing"},
    ],
    "biology_processes": [
        {
            "query": "silencing genes with short RNA molecules",
            "expected_id": "mechanisms-rna-interference-sirna-pathway",
        },
        {
            "query": "how cells recognize pathogens without prior exposure",
            "expected_id": "immunology-innate-immune-pattern-recognition",
        },
    ],
    "episodes": [
        {"query": "gene editing without cutting DNA", "expected_id": "ever-bio-250007"},
        {"query": "predicting protein shape from sequence", "expected_id": "ever-compsci-250041"},
    ],
    "physics_processes": [
        {
            "query": "why does a changing magnetic field create an electric current",
            "expected_id": "electromagnetism-electromagnetic-induction",
        },
    ],
}


@dataclass
class AnchorResult:
    collection: str
    query: str
    expected_id: str
    rank: Optional[int]  # 1-based rank if found in top-K, else None
    severity: str  # "pass" | "ALERT"


@dataclass
class CoverageResult:
    collection: str
    total_docs: int
    embedded_docs: int
    dimension_counts: Dict[str, int]
    sampled: bool
    sample_size: Optional[int]
    note: str


@dataclass
class IndexResult:
    collection: str
    has_index: bool
    index_dimension: Optional[int]
    index_state: Optional[str]
    data_dimensions: List[int]
    covered: bool  # every data dimension has a matching READY index
    orphan: bool  # index exists but collection has 0 docs
    severity: str  # "pass" | "WARNING"
    note: str


# ── Check A ──────────────────────────────────────────────────────────────────


def run_check_a() -> List[AnchorResult]:
    results: List[AnchorResult] = []
    for collection, anchors in ANCHORS.items():
        content_type = CONTENT_TYPE_PARAM[collection]
        response_key = RESPONSE_KEY[collection]
        for anchor in anchors:
            query = anchor["query"]
            expected_id = anchor["expected_id"]
            rank: Optional[int] = None
            try:
                resp = requests.get(
                    SEMANTIC_ENDPOINT,
                    params={"query": query, "content_types": content_type, "limit": TOP_K},
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get(response_key, [])
                for i, item in enumerate(items, 1):
                    item_id = None
                    for field_name in ID_FIELD_CANDIDATES:
                        if field_name in item:
                            item_id = item[field_name]
                            break
                    if item_id == expected_id:
                        rank = i
                        break
            except Exception as exc:
                results.append(
                    AnchorResult(collection, query, expected_id, None, f"ALERT (request failed: {exc})")
                )
                continue
            severity = "pass" if rank is not None else "ALERT"
            results.append(AnchorResult(collection, query, expected_id, rank, severity))
    return results


# ── Check B ──────────────────────────────────────────────────────────────────


def _measure_small_collection(db: firestore.Client, name: str) -> CoverageResult:
    docs = list(db.collection(name).stream())
    total = len(docs)
    embedded = 0
    dims: Dict[str, int] = {}
    for d in docs:
        data = d.to_dict() or {}
        emb = data.get("embedding")
        model = data.get("embedding_model")
        if model:
            embedded += 1
        if emb is not None:
            try:
                dim = str(len(emb))
            except Exception:
                dim = "unmeasurable"
            dims[dim] = dims.get(dim, 0) + 1
    return CoverageResult(
        collection=name,
        total_docs=total,
        embedded_docs=embedded,
        dimension_counts=dims,
        sampled=False,
        sample_size=None,
        note=f"{name}: dimension full-scanned across all {total} docs.",
    )


def _measure_large_collection(db: firestore.Client, name: str) -> CoverageResult:
    from google.cloud.firestore_v1.base_query import FieldFilter

    col = db.collection(name)
    total = col.count().get()[0][0].value
    embedded = col.where(filter=FieldFilter("embedding_model", ">", "")).count().get()[0][0].value
    sample = list(
        col.where(filter=FieldFilter("embedding_model", ">", "")).limit(RESEARCH_PAPERS_SAMPLE_SIZE).stream()
    )
    dims: Dict[str, int] = {}
    for d in sample:
        data = d.to_dict() or {}
        emb = data.get("embedding")
        if emb is not None:
            try:
                dim = str(len(emb))
            except Exception:
                dim = "unmeasurable"
            dims[dim] = dims.get(dim, 0) + 1
    return CoverageResult(
        collection=name,
        total_docs=int(total),
        embedded_docs=int(embedded),
        dimension_counts=dims,
        sampled=True,
        sample_size=len(sample),
        note=(
            f"{name}: dimension verified on a {len(sample)}-doc sample "
            f"(of {int(embedded)} embedded docs) -- NOT a full scan. A sampled "
            f"check can miss a small pocket of wrong-dimension docs; small "
            f"collections in this report are full-scanned and carry no such "
            f"caveat."
        ),
    )


def run_check_b(db: firestore.Client) -> List[CoverageResult]:
    results = []
    for name in LARGE_COLLECTIONS:
        results.append(_measure_large_collection(db, name))
    for name in SMALL_LIVE_QUERY_COLLECTIONS + NON_QUERIED_EMBEDDED_COLLECTIONS:
        results.append(_measure_small_collection(db, name))
    return results


# ── Check C ──────────────────────────────────────────────────────────────────


def run_check_c(coverage: List[CoverageResult]) -> List[IndexResult]:
    admin_client = firestore_admin_v1.FirestoreAdminClient()
    parent = f"projects/{PROJECT_ID}/databases/{DATABASE_ID}/collectionGroups/-"
    all_indexes = list(admin_client.list_indexes(parent=parent))

    # collection -> list of (dimension, state) for its vector indexes
    vector_indexes: Dict[str, List[Dict[str, Any]]] = {}
    for idx in all_indexes:
        collection = idx.name.split("/collectionGroups/")[1].split("/indexes/")[0]
        for f in idx.fields:
            if f.vector_config and f.vector_config.dimension:
                vector_indexes.setdefault(collection, []).append(
                    {"dimension": f.vector_config.dimension, "state": idx.state.name}
                )

    coverage_by_name = {c.collection: c for c in coverage}

    results = []
    # 1. Every collection we measured: does its index match its data?
    for name, cov in coverage_by_name.items():
        idxs = vector_indexes.get(name, [])
        data_dims = sorted(int(d) for d in cov.dimension_counts if d.isdigit())
        if not idxs:
            results.append(
                IndexResult(
                    collection=name,
                    has_index=False,
                    index_dimension=None,
                    index_state=None,
                    data_dimensions=data_dims,
                    covered=(not data_dims),  # no data, no index needed = fine
                    orphan=False,
                    severity="pass" if not data_dims else "WARNING",
                    note="no vector index" + (" (no embedded data either, fine)" if not data_dims else " but embedded data exists"),
                )
            )
            continue
        ready_dims = {i["dimension"] for i in idxs if i["state"] == "READY"}
        uncovered = [d for d in data_dims if d not in ready_dims]
        covered = not uncovered
        for i in idxs:
            orphan = cov.total_docs == 0 and i["state"] == "READY"
            severity = "pass"
            note = f"index dim={i['dimension']} state={i['state']}"
            if orphan:
                severity = "WARNING"
                note += " -- ORPHAN: index is READY but collection has 0 docs"
            elif not covered and i["dimension"] in ready_dims:
                # this particular index is fine; the collection overall is not
                pass
            results.append(
                IndexResult(
                    collection=name,
                    has_index=True,
                    index_dimension=i["dimension"],
                    index_state=i["state"],
                    data_dimensions=data_dims,
                    covered=covered,
                    orphan=orphan,
                    severity=severity,
                    note=note,
                )
            )
        if uncovered:
            results.append(
                IndexResult(
                    collection=name,
                    has_index=True,
                    index_dimension=None,
                    index_state=None,
                    data_dimensions=data_dims,
                    covered=False,
                    orphan=False,
                    severity="WARNING",
                    note=(
                        f"{name}: data exists at dimension(s) {uncovered} with "
                        f"NO matching READY index (existing index dims: "
                        f"{sorted(ready_dims)}) -- these docs are unreachable "
                        f"via find_nearest at their own dimension."
                    ),
                )
            )

    # 2. Orphan indexes: collections with a vector index but not in our
    #    coverage set at all (e.g. math_processes, deleted but index remains).
    for coll_name, idxs in vector_indexes.items():
        if coll_name in coverage_by_name:
            continue
        try:
            docs = list(firestore.Client(project=PROJECT_ID, database=DATABASE_ID).collection(coll_name).limit(1).stream())
        except Exception:
            docs = []
        for i in idxs:
            orphan = len(docs) == 0
            results.append(
                IndexResult(
                    collection=coll_name,
                    has_index=True,
                    index_dimension=i["dimension"],
                    index_state=i["state"],
                    data_dimensions=[],
                    covered=not orphan,
                    orphan=orphan,
                    severity="WARNING" if orphan else "pass",
                    note=(
                        f"{coll_name}: not in the tracked collection list, "
                        f"index dim={i['dimension']} state={i['state']}"
                        + (" -- ORPHAN: index READY, 0 docs found" if orphan else "")
                    ),
                )
            )
    return results


# ── Report assembly ──────────────────────────────────────────────────────────


def build_report(
    anchor_results: List[AnchorResult],
    coverage_results: List[CoverageResult],
    index_results: List[IndexResult],
) -> Dict[str, Any]:
    alerts = [r for r in anchor_results if r.severity != "pass"]
    warnings = [r for r in index_results if r.severity == "WARNING"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "check_a_total": len(anchor_results),
            "check_a_alerts": len(alerts),
            "check_c_warnings": len(warnings),
            "overall": "ALERT" if alerts else ("WARNING" if warnings else "OK"),
        },
        "check_a_positive_findability": [
            {
                "collection": r.collection,
                "query": r.query,
                "expected_id": r.expected_id,
                "rank": r.rank,
                "severity": r.severity,
            }
            for r in anchor_results
        ],
        "check_b_coverage_integrity": [
            {
                "collection": c.collection,
                "total_docs": c.total_docs,
                "embedded_docs": c.embedded_docs,
                "dimension_counts": c.dimension_counts,
                "sampled": c.sampled,
                "sample_size": c.sample_size,
                "note": c.note,
            }
            for c in coverage_results
        ],
        "check_c_index_consistency": [
            {
                "collection": i.collection,
                "has_index": i.has_index,
                "index_dimension": i.index_dimension,
                "index_state": i.index_state,
                "data_dimensions": i.data_dimensions,
                "covered": i.covered,
                "orphan": i.orphan,
                "severity": i.severity,
                "note": i.note,
            }
            for i in index_results
        ],
    }


def print_human_summary(report: Dict[str, Any]) -> None:
    print("=" * 70)
    print("FINDABILITY PROBE — v1")
    print("=" * 70)
    print(f"Generated: {report['generated_at']}")
    print(f"Overall: {report['summary']['overall']}")
    print()
    print("-- Check A: positive findability --")
    for r in report["check_a_positive_findability"]:
        marker = "PASS" if r["severity"] == "pass" else r["severity"]
        rank_str = f"rank {r['rank']}" if r["rank"] else "NOT FOUND in top-5"
        print(f"  [{marker:6s}] {r['collection']:28s} \"{r['query']}\" -> {rank_str}")
    print()
    print("-- Check B: coverage integrity --")
    for c in report["check_b_coverage_integrity"]:
        print(f"  {c['collection']:28s} total={c['total_docs']:<8} embedded={c['embedded_docs']:<8} dims={c['dimension_counts']}")
        print(f"      {c['note']}")
    print()
    print("-- Check C: index/collection consistency --")
    for i in report["check_c_index_consistency"]:
        marker = "PASS" if i["severity"] == "pass" else i["severity"]
        print(f"  [{marker:8s}] {i['collection']:28s} {i['note']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=str, default="", help="Write full JSON report to this path")
    args = parser.parse_args()

    db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)

    anchor_results = run_check_a()
    coverage_results = run_check_b(db)
    index_results = run_check_c(coverage_results)

    report = build_report(anchor_results, coverage_results, index_results)
    print_human_summary(report)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote: {args.json_out}")

    return 1 if report["summary"]["overall"] == "ALERT" else 0


if __name__ == "__main__":
    sys.exit(main())
