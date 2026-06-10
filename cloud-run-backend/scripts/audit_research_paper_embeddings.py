#!/usr/bin/env python3
"""
Sample research_papers in Firestore and report embedding vector length + embedding_model.

Efficient: one query with limit (no full collection scan). Use a larger --sample for
tighter confidence on "are we mixed".

Usage (from repo, with ADC: gcloud auth application-default login):
  cd cloud-run-backend && source venv/bin/activate
  python3 scripts/audit_research_paper_embeddings.py --sample 800

Env:
  GOOGLE_CLOUD_PROJECT (default: regal-scholar-453620-r7)
  FIRESTORE_DATABASE (default: copernicusai)

Exit 0 always; prints JSON summary at end.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


def _len_embedding(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    # google.cloud.firestore_v1.vector.Vector is a Sequence; prefer len().
    try:
        return len(raw)
    except Exception:
        pass
    if isinstance(raw, dict) and "values" in raw:
        v = raw.get("values")
        if isinstance(v, (list, tuple)):
            return len(v)
    return None


def _model_str(d: dict) -> str:
    m = d.get("embedding_model")
    if m is None or str(m).strip() == "":
        return "(missing)"
    return str(m).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit paper embedding dimensions and model labels in Firestore")
    ap.add_argument("--sample", type=int, default=500, help="Max documents to read (ordered query+limit).")
    ap.add_argument(
        "--query",
        choices=("with_model", "any_embedding"),
        default="with_model",
        help="with_model: documents with non-empty embedding_model (fast, matches /api/content/stats). "
        "any_embedding: not supported as single query without OR; use with_model for v1.",
    )
    ap.add_argument("--json-out", type=str, default="", help="If set, write full summary JSON to this path.")
    args = ap.parse_args()

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7")
    database = os.environ.get("FIRESTORE_DATABASE", "copernicusai")

    client = firestore.Client(project=project, database=database)
    col = client.collection("research_papers")

    q = col.where(filter=FieldFilter("embedding_model", ">", "")).limit(max(1, int(args.sample)))
    dims: List[Optional[int]] = []
    models: List[str] = []
    doc_ids: List[str] = []
    for snap in q.stream():
        d = snap.to_dict() or {}
        raw = d.get("embedding")
        L = _len_embedding(raw)
        dims.append(L)
        models.append(_model_str(d))
        doc_ids.append(snap.id)

    dim_counts = Counter(dims)
    model_counts = Counter(models)

    unique_dims = sorted({x for x in dims if x is not None}, key=lambda x: (x is None, x))
    mixed_dims = len(unique_dims) > 1
    mixed_models = len([k for k in model_counts if k != "(missing)"]) > 1

    summary = {
        "project": project,
        "database": database,
        "query": args.query,
        "sample_size_requested": args.sample,
        "documents_examined": len(doc_ids),
        "vector_length_counts": {str(k): v for k, v in sorted(dim_counts.items(), key=lambda kv: str(kv[0]))},
        "embedding_model_counts": dict(model_counts.most_common()),
        "unique_vector_lengths": unique_dims,
        "interpretation": {
            "mixed_vector_lengths_in_sample": bool(mixed_dims),
            "mixed_embedding_model_strings_in_sample": bool(mixed_models),
            "note": "If multiple lengths appear, the same Firestore `embedding` field is not safe for a single "
            "vector index. For A/B (Vertex vs OpenAI) research, use separate fields and indexes, e.g. "
            "embedding_vertex + embedding_openai.",
        },
    }

    print("=" * 72)
    print("Firestore embedding audit — research_papers (sampled)")
    print("=" * 72)
    print(f"Project:   {project}")
    print(f"Database:  {database}")
    print(f"Examined:  {len(doc_ids)} documents (embedding_model non-empty)")
    print()
    print("Vector length (dimension) → count")
    for k, v in sorted(dim_counts.items(), key=lambda x: (x[0] is None, str(x[0]))):
        print(f"  {k!r}  →  {v}")
    print()
    print("embedding_model string → count")
    for k, v in model_counts.most_common(20):
        print(f"  {k!r}  →  {v}")
    print()
    if mixed_dims:
        print("⚠️  Multiple vector lengths in this sample: one ANN / Firestore index per dimension, or re-embed.")
    else:
        print("✓  Single vector length in sample (or none parsed).")
    if mixed_models:
        print("⚠️  Multiple model labels in this sample: verify with Cloud Run which provider is active.")
    else:
        print("✓  Single model label in sample (or only missing).")
    print("=" * 72)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({**summary, "sample_doc_ids": doc_ids[:50]}, f, indent=2)
        print("Wrote:", args.json_out)

    j = json.dumps(summary, indent=2)
    print(j)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
