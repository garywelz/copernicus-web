#!/usr/bin/env python3
"""Run track A dense retrieval benchmark locally (notebook §6b + §10)."""

from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from openai import OpenAI, RateLimitError

PAPERS_DIR = Path(__file__).resolve().parent
CORPUS_PATH = PAPERS_DIR / "research_papers_20260526.jsonl.gz"
QUERIES_PATH = PAPERS_DIR / "appendix_queries.json"
JUDGMENTS_PATH = PAPERS_DIR / "judgments.csv"
EMB_PATH = PAPERS_DIR / "openai_doc_embeddings.npz"
EMB_PARTIAL_PATH = PAPERS_DIR / "openai_doc_embeddings.partial.npz"

K = 10
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_BATCH_SIZE = int(os.environ.get("OPENAI_BATCH_SIZE", "100"))
OPENAI_EMBED_MAX_CHARS = int(os.environ.get("OPENAI_EMBED_MAX_CHARS", "8000"))


def load_corpus(path: Path) -> pd.DataFrame:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            rows.append(
                {
                    "doc_id": d["doc_id"],
                    "combined_text": d.get("combined_text") or "",
                }
            )
    documents = pd.DataFrame(rows).drop_duplicates(subset=["doc_id"]).reset_index(drop=True)
    return documents


def load_queries(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["queries"]


def normalize_rows(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n = np.maximum(n, 1e-12)
    return (m / n).astype(np.float32)


def _rate_limit_sleep(exc: RateLimitError, attempt: int) -> None:
    msg = str(exc)
    m = re.search(r"try again in (\d+)ms", msg)
    wait = (int(m.group(1)) / 1000.0 + 0.5) if m else min(60.0, 2.0**attempt)
    print(f"  rate limited — sleeping {wait:.1f}s (attempt {attempt})")
    time.sleep(wait)


def embed_batch(client: OpenAI, texts: list[str]) -> np.ndarray:
    texts = [t[:OPENAI_EMBED_MAX_CHARS] if t else " " for t in texts]
    for attempt in range(1, 12):
        try:
            resp = client.embeddings.create(model=OPENAI_EMBED_MODEL, input=texts)
            break
        except RateLimitError as exc:
            if attempt == 11:
                raise
            _rate_limit_sleep(exc, attempt)
    idx_map = {d.index: np.array(d.embedding, dtype=np.float32) for d in resp.data}
    return np.stack([idx_map[i] for i in range(len(texts))], axis=0)


def embed_corpus(
    client: OpenAI,
    texts: list[str],
    *,
    doc_ids: list[str],
    start_index: int = 0,
    partial_emb: np.ndarray | None = None,
) -> np.ndarray:
    out: list[np.ndarray] = []
    if partial_emb is not None and start_index > 0:
        out.append(partial_emb)

    n_batches = (len(texts) + OPENAI_BATCH_SIZE - 1) // OPENAI_BATCH_SIZE
    for i in range(start_index, len(texts), OPENAI_BATCH_SIZE):
        batch_num = i // OPENAI_BATCH_SIZE + 1
        batch = texts[i : i + OPENAI_BATCH_SIZE]
        out.append(embed_batch(client, batch))
        done = min(i + OPENAI_BATCH_SIZE, len(texts))
        print(f"  embedded batch {batch_num}/{n_batches} ({done}/{len(texts)} docs)")
        if done % 500 == 0 or done == len(texts):
            partial = normalize_rows(np.vstack(out).astype(np.float32))
            np.savez_compressed(
                EMB_PARTIAL_PATH,
                doc_ids=np.array(doc_ids[: len(partial)], dtype=object),
                embeddings=partial,
                model=np.array(OPENAI_EMBED_MODEL),
                n_done=np.array(len(partial)),
            )
        time.sleep(0.15)
    return np.vstack(out).astype(np.float32)


def run_retriever(system_name: str, queries: list[dict], rank_fn) -> pd.DataFrame:
    rows = []
    for q in queries:
        ranked = rank_fn(q["text"])
        for r, (doc_id, score) in enumerate(ranked, start=1):
            rows.append(
                {
                    "system": system_name,
                    "query_id": q["id"],
                    "rank": r,
                    "doc_id": doc_id,
                    "score": score,
                }
            )
    return pd.DataFrame(rows)


def reciprocal_rank(rank_list: np.ndarray, rel: np.ndarray) -> float:
    for idx, (_, is_rel) in enumerate(zip(rank_list, rel), start=1):
        if is_rel >= 1:
            return 1.0 / idx
    return 0.0


def dcg_binary(rel: np.ndarray) -> float:
    gains = np.asarray(rel[:K], dtype=np.float64)
    positions = np.arange(1, len(gains) + 1)
    return float(np.sum((2**gains - 1) / np.log2(positions + 1)))


def ndcg_binary(rel_ranked: np.ndarray) -> float:
    rel_sorted = np.sort(rel_ranked)[::-1][:K]
    ideal = np.sort(rel_sorted)[::-1]
    denom = dcg_binary(ideal)
    if denom <= 0:
        return 0.0
    return dcg_binary(rel_ranked[:K]) / denom


def summarise_system(rank_df: pd.DataFrame, judgments: pd.DataFrame) -> dict:
    """Binary relevance from judgments pool; unjudged top-k docs scored as 0 (conservative)."""
    j = judgments.astype({"query_id": int})
    ndcgs, precs, rrs, missing = [], [], [], []
    rel_map = j.set_index(["query_id", "doc_id"])["relevant"].astype(int)
    unjudged_hits = 0

    for qid, sub in rank_df.groupby("query_id"):
        sub = sub.sort_values("rank")
        docs = sub["doc_id"].tolist()[:K]
        rel_vec = []
        for d in docs:
            try:
                rel_vec.append(int(rel_map.loc[(qid, d)]))
            except KeyError:
                rel_vec.append(0)
                unjudged_hits += 1
        rel_vec = np.asarray(rel_vec, dtype=np.int32)
        ndcgs.append(ndcg_binary(rel_vec))
        precs.append(float(rel_vec.mean()))
        rrs.append(reciprocal_rank(np.arange(K), rel_vec))
        missing.append(1 if rel_vec.sum() == 0 else 0)

    return {
        "mean_ndcg_at_10": float(np.mean(ndcgs)),
        "mean_precision_at_10": float(np.mean(precs)),
        "median_reciprocal_rank": float(np.median(rrs)),
        "queries_no_relevant_in_top10": int(np.sum(missing)),
        "unjudged_top10_hits": int(unjudged_hits),
        "n_queries": len(ndcgs),
    }


def write_metrics(rankings: pd.DataFrame, openai_doc_emb: np.ndarray) -> dict:
    judgments = pd.read_csv(JUDGMENTS_PATH)
    dense_metrics = summarise_system(rankings, judgments)

    manifest_path = PAPERS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lexical = manifest.get("table4_lexical", {})

    rows = [
        ("Mean nDCG@10", "mean_ndcg_at_10"),
        ("Mean Precision@10", "mean_precision_at_10"),
        ("Median Reciprocal Rank", "median_reciprocal_rank"),
        ("Queries with no relevant in top-10", "queries_no_relevant_in_top10"),
    ]
    table = []
    for label, key in rows:
        table.append(
            {
                "metric": label,
                "lexical_tf_idf": lexical.get(key, ""),
                "dense_openai": dense_metrics.get(key, ""),
            }
        )
    table_path = PAPERS_DIR / "table4_metrics_lexical_vs_openai.csv"
    pd.DataFrame(table).to_csv(table_path, index=False)
    print(f"Wrote {table_path}")

    manifest["openai_embedding_model"] = OPENAI_EMBED_MODEL
    manifest["openai_embedding_dims"] = str(openai_doc_emb.shape[1])
    manifest["table4_dense_openai"] = dense_metrics
    manifest["runtime_dense"] = "local"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("\n=== Track A results (dense_openai) ===")
    for k, v in dense_metrics.items():
        print(f"  {k}: {v}")
    print("\n=== Lexical baseline (frozen) ===")
    for k, v in lexical.items():
        print(f"  {k}: {v}")
    if dense_metrics.get("unjudged_top10_hits"):
        print(
            "\nNote: unjudged_top10_hits counts dense top-10 docs absent from "
            "judgments.csv (scored as non-relevant). Expand pool for strict protocol."
        )
    return dense_metrics


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 1
    for p in (CORPUS_PATH, QUERIES_PATH, JUDGMENTS_PATH):
        if not p.exists():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 1

    print("Loading corpus...")
    documents = load_corpus(CORPUS_PATH)
    print(f"  documents: {len(documents)}")

    queries = load_queries(QUERIES_PATH)
    print(f"  queries: {len(queries)}")

    client = OpenAI()
    doc_ids = documents["doc_id"].tolist()

    texts = documents["combined_text"].astype(str).tolist()
    start_index = 0
    partial_emb = None

    if EMB_PATH.exists():
        z = np.load(EMB_PATH, allow_pickle=True)
        openai_doc_ids = z["doc_ids"].tolist()
        openai_doc_emb = z["embeddings"].astype(np.float32)
        if openai_doc_ids != doc_ids:
            print("ERROR: cached embeddings doc_id order mismatch — delete .npz", file=sys.stderr)
            return 1
        print(f"Loaded cached embeddings: {EMB_PATH} shape={openai_doc_emb.shape}")
    elif EMB_PARTIAL_PATH.exists():
        z = np.load(EMB_PARTIAL_PATH, allow_pickle=True)
        n_done = int(z["n_done"])
        partial_ids = z["doc_ids"].tolist()
        if partial_ids != doc_ids[:n_done]:
            print("ERROR: partial checkpoint doc_id mismatch — delete .partial.npz", file=sys.stderr)
            return 1
        partial_emb = z["embeddings"].astype(np.float32)
        start_index = n_done
        print(f"Resuming from partial checkpoint: {n_done}/{len(texts)} docs")
        openai_doc_emb = embed_corpus(
            client, texts, doc_ids=doc_ids, start_index=start_index, partial_emb=partial_emb
        )
        openai_doc_emb = normalize_rows(openai_doc_emb)
        np.savez_compressed(
            EMB_PATH,
            doc_ids=np.array(doc_ids, dtype=object),
            embeddings=openai_doc_emb,
            model=np.array(OPENAI_EMBED_MODEL),
        )
        EMB_PARTIAL_PATH.unlink(missing_ok=True)
        print(f"Wrote {EMB_PATH} shape={openai_doc_emb.shape}")
    else:
        print(f"Embedding corpus with {OPENAI_EMBED_MODEL} (batch={OPENAI_BATCH_SIZE})...")
        openai_doc_emb = embed_corpus(client, texts, doc_ids=doc_ids)
        openai_doc_emb = normalize_rows(openai_doc_emb)
        np.savez_compressed(
            EMB_PATH,
            doc_ids=np.array(doc_ids, dtype=object),
            embeddings=openai_doc_emb,
            model=np.array(OPENAI_EMBED_MODEL),
        )
        EMB_PARTIAL_PATH.unlink(missing_ok=True)
        print(f"Wrote {EMB_PATH} shape={openai_doc_emb.shape}")

    def dense_topk(query_text: str) -> list[tuple[str, float]]:
        qt = query_text[:OPENAI_EMBED_MAX_CHARS]
        qv = embed_batch(client, [qt])[0]
        qv = qv / max(float(np.linalg.norm(qv)), 1e-12)
        scores = openai_doc_emb @ qv
        n = scores.shape[0]
        k_eff = min(K, n)
        if k_eff == n:
            idx = np.argsort(scores)[::-1]
        else:
            idx = np.argpartition(scores, -k_eff)[-k_eff:]
            idx = idx[np.argsort(scores[idx])[::-1]]
        return [(doc_ids[i], float(scores[i])) for i in idx]

    print("Running dense retrieval for 30 queries...")
    rankings = run_retriever("dense_openai", queries, dense_topk)
    rankings_path = PAPERS_DIR / "rankings_openai_dense.csv"
    rankings.to_csv(rankings_path, index=False)
    print(f"Wrote {rankings_path}")

    write_metrics(rankings, openai_doc_emb)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
