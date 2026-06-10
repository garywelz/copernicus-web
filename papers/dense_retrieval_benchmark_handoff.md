# Dense Retrieval Benchmark Handoff (Track A)

**Date:** 2026-06-07 (roles updated v3)  
**Author:** Cursor agent  
**Purpose:** Execute **Evaluation Roadmap track (A)** from `papers/knowledge_engine_vision.md` §6 — OpenAI dense retrieval on the **frozen** May 2026 corpus against the **frozen** 30-query set, producing metrics comparable to lexical Table 4.

**Who runs this:** **Gary or Cursor** (requires `OPENAI_API_KEY`; Colab or local). **Claude does not run the notebook** — Claude reviews paper prose after metrics are pasted back.

---

## What this benchmark is (and is not)

| In scope | Out of scope |
|----------|--------------|
| Frozen export `research_papers_20260526.jsonl.gz` (59,499 docs) | Live Firestore queries |
| Frozen `appendix_queries.json` (30 queries) | Re-judging relevance (unless you find gaps) |
| OpenAI `text-embedding-3-small` (1536d) cosine retrieval | Vertex / mixed-dimension embeddings |
| nDCG@10, Precision@10, MRR vs lexical 0.545 | Claiming production superiority |

**Paper constraint:** Table 4 lexical numbers are **frozen and citable**. Do **not** overwrite them. Add dense results as a **second column** (Table 4 extension) or **Table 5** with explicit “dense OpenAI, same judgments” labeling.

---

## Frozen artefacts (verify before run)

| Artefact | Path | SHA256 / count |
|----------|------|----------------|
| Corpus export | `papers/research_papers_20260526.jsonl.gz` | `3dd5e019fca5f8e823bd71020a80c534b2e1a9e7199272b27c0b13da40ee8065` · n=59,499 |
| Query list | `papers/appendix_queries.json` | `8fcfe7bcd50a85ba665ad065afe4a9623c38422da0254f78cdadac47d4dfdd1f` · n=30 |
| Relevance judgments | `papers/judgments.csv` | ~300 rows, mix of relevant=0/1 (already used for lexical pilot) |
| Lexical rankings | `papers/rankings_lexical.csv` | Baseline system `lexical_tf_idf` |
| Lexical metrics | `papers/manifest.json` → `table4_lexical` | mean nDCG@10 ≈ **0.545** |
| Zenodo bundle | https://doi.org/10.5281/zenodo.18463303 | Archive new dense run as v3 or sibling deposit |

GCS mirror (if local gzip missing):  
`gs://regal-scholar-453620-r7-podcast-storage/research_data/snapshots/research_papers_20260526.jsonl.gz`

---

## Execution vehicle

**Primary:** `papers/retrieval_pilot_colab_bundle.ipynb` — sections **§6b** (OpenAI dense) and **§10** (metrics).

The notebook already implements:
- Corpus load → `documents` DataFrame (`doc_id`, `combined_text`)
- Lexical TF-IDF (§6a) — **already run**; do not need to re-run unless validating
- OpenAI batch embedding + L2-normalized dot-product retrieval (§6b)
- Cached replay via `openai_doc_embeddings.npz` (avoids re-billing API)
- `summarise_system()` → nDCG@10, Precision@10, MRR, queries with no relevant in top-10
- Export `table4_metrics_lexical_vs_openai.csv` when both columns exist

**Runtime:** Colab Pro or local with ~8 GB RAM; embedding 59,499 abstracts is the long step (~30–90 min API time depending on batch size and rate limits).

---

## Step-by-step protocol

### 1. Environment

```bash
# Local alternative to Colab
pip install pandas numpy scikit-learn openai
export OPENAI_API_KEY='...'   # Colab: Secrets
export OPENAI_EMBED_MODEL='text-embedding-3-small'  # must match production
export OPENAI_BATCH_SIZE='100'
```

**Critical:** Use **`text-embedding-3-small`** (1536d) — same model as live Firestore index and `backfill_embeddings.py`. Do **not** use Vertex `text-embedding-004` (768d).

### 2. Load frozen corpus (notebook §4)

Build `documents` from the gzipped JSONL export, not Firestore:

- **`doc_id`:** stable string from export (e.g. `pubmed_30872376`, `arxiv_2604.21085v1`, UUIDs)
- **`combined_text`:** concatenate title + abstract (same fields used for lexical pilot)

Assert `len(documents) == 59499` and hash matches manifest.

### 3. Load frozen queries (notebook §5)

Use `papers/appendix_queries.json` verbatim — 30 queries with ids 1–30. Do not paraphrase.

### 4. Run §6b — dense OpenAI

- Embeds all `combined_text` → saves `openai_doc_embeddings.npz`
- For each query: embed query text → cosine top-10 over corpus → `rankings_openai_dense.csv`
- System label: `dense_openai`

**Cost estimate:** ~60k embedding calls × ~500 tokens avg ≈ budget accordingly (OpenAI batch pricing); one-time if `.npz` archived.

### 5. Metrics (notebook §10)

```python
_judgments = pd.read_csv("judgments.csv")  # existing frozen judgments
_tab_o = summarise_system(rankings_openai_dense, _judgments)
```

Record:
- Mean nDCG@10 (primary comparison to **0.545**)
- Mean Precision@10
- Median Reciprocal Rank
- Queries with no relevant in top-10 (lexical had **8/30**)

Export `table4_metrics_lexical_vs_openai.csv`.

### 6. Optional secondary variant (not required for v1)

Notebook §8 scaffolds **hybrid lexical+dense rerank**. Only pursue if dense-alone improves nDCG@10 and you want a third column; document fusion formula in manifest.

### 7. Archive & manuscript updates

1. Zip: notebook, `rankings_openai_dense.csv`, `openai_doc_embeddings.npz`, `table4_metrics_lexical_vs_openai.csv`, updated `manifest.json`, `pip freeze`
2. Upload Zenodo; add DOI to paper §6 and Reference list
3. Paper prose targets:
   - §6 **Preliminary Retrieval Pilot** — add dense row/column with Δ vs lexical
   - §6 **Evaluation Roadmap** — mark track (A) complete with date + DOI
   - §7 **Limitations** — soften “formal dense evaluation pending” if results published
   - Abstract — only if Gary wants symmetric claim (“dense nDCG@10 = X on same 30 queries”)

**Do not change:** lexical Table 4 values, query SHA256, corpus SHA256, Zenodo DOI for original bundle (add new deposit or version).

---

## Expected paper table shape (draft)

| Metric | Lexical TF-IDF (frozen) | OpenAI dense (track A) |
|--------|------------------------:|-----------------------:|
| Mean nDCG@10 | 0.545 | *TBD* |
| Mean Precision@10 | 0.323 | *TBD* |
| Median Reciprocal Rank | 0.500 | *TBD* |
| No relevant in top-10 | 8 / 30 | *TBD* |

Interpretation template (for Claude to draft after numbers):
- If dense nDCG@10 > 0.545: quantify gain; note same single-assessor judgments, not external baseline
- If dense ≤ lexical: discuss query types where keyword overlap wins; 8 zero-hit queries as case study
- Either way: **existence proof** framing — not a claim of SOTA retrieval

---

## Relationship to live production system

| Aspect | Benchmark (track A) | Live Cloud Run |
|--------|---------------------|----------------|
| Corpus | Frozen JSONL May 26 | Firestore `research_papers` (same 59,499 count; post-freeze embeddings added) |
| Embeddings | Embed export text in Colab | Precomputed in Firestore `embedding` field |
| Retrieval | Offline cosine over `.npz` | `/api/vector-search/semantic` |
| Judgments | `judgments.csv` | N/A (user-facing RAG unjudged) |

Live system confirms feasibility; track A provides **citable** dense numbers on the **same** 30-query evaluation protocol.

---

## Failure modes & checks

1. **doc_id mismatch** — dense rankings must use same `doc_id` strings as `judgments.csv`; if export field names changed, join breaks silently (nDCG → 0)
2. **Re-embedding without cache** — expensive; always archive `openai_doc_embeddings.npz`
3. **Truncation** — notebook uses `OPENAI_EMBED_MAX_CHARS=8000`; document if changed
4. **Demo judgments** — repo `judgments.csv` is real (not all zeros); do not overwrite with notebook demo stub
5. **Model drift** — if OpenAI deprecates `text-embedding-3-small`, record replacement model in manifest and re-embed entire corpus for fair comparison

---

## Files Claude should read first

1. `papers/knowledge_engine_vision.md` — §6, §7, Evaluation Roadmap (A)
2. `papers/retrieval_pilot_colab_bundle.ipynb` — §6b, §10
3. `papers/manifest.json` — lexical baseline metadata
4. `papers/judgments.csv` — frozen relevance labels
5. `docs/EVAL_FREEZE.md` — corpus freeze policy

---

## Deliverables checklist

- [ ] `rankings_openai_dense.csv` (30 queries × 10 ranks)
- [ ] `openai_doc_embeddings.npz` (59,499 × 1536)
- [ ] `table4_metrics_lexical_vs_openai.csv`
- [ ] Updated `manifest.json` with `openai_embedding_model`, dims, dense metrics
- [ ] Zenodo deposit + DOI
- [ ] Paper §6/§7 prose + table column (**Cursor drafts** → Gary pastes to **Claude for review**)
- [ ] One-paragraph result summary for `KNOWLEDGE_ENGINE_UPDATES_FOR_CLAUDE.md`
