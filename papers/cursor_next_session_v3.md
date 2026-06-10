# Cursor Handoff — Next Session (v3)
**Date:** 2026-06-07  
**From:** Claude + Gary (division of labor agreed 2026-06-07)  
**To:** Cursor agent  
**Repo:** `~/copernicus-web-public`  
**Supersedes:** `papers/cursor_next_session_v2.md`

**Related docs:**
- `papers/dense_retrieval_benchmark_handoff.md` — track A protocol
- `papers/cursor_session_handoff_for_claude.md` — audit context
- `papers/knowledge_engine_vision.md` — paper to edit in phase 3

---

## Division of labor (agreed)

| Phase | Who | What |
|------:|-----|------|
| 1 | **Cursor** | doc_id check + GLMP backfill → report back |
| 2 | **Gary or Cursor** | Run `retrieval_pilot_colab_bundle.ipynb` §6b (needs `OPENAI_API_KEY`; Colab or local) → metrics |
| 3 | **Cursor** | Draft §6 dense retrieval prose + Table 4 dense column using real numbers |
| 4 | **Gary** | Paste Cursor’s draft to Claude |
| 5 | **Claude** | Review prose (no notebook execution, no API key) |

**Claude cannot run Colab or call OpenAI.** Claude reviews and refines prose after metrics exist.

---

## Phase 1 — Do now (this session)

### Task A. Verify doc_id alignment (prerequisite for track A)

Confirm every `judgments.csv` doc_id exists in the frozen corpus export before spending API credits on dense embeddings.

**Download corpus** (not in repo):

```bash
gsutil cp gs://regal-scholar-453620-r7-podcast-storage/research_data/snapshots/research_papers_20260526.jsonl.gz papers/
```

**Empirical hint:** `judgments.csv` ↔ `rankings_lexical.csv` = **267/267** doc_id overlap; lexical nDCG@10 = **0.545**. Expect confirmation, not surprises.

```python
import csv, gzip, json
from pathlib import Path

jud_ids = set()
with Path("papers/judgments.csv").open() as f:
    for row in csv.DictReader(f):
        jud_ids.add(row["doc_id"])

corpus_ids = set()
with gzip.open("papers/research_papers_20260526.jsonl.gz", "rt") as f:
    for line in f:
        d = json.loads(line)
        corpus_ids.add(d.get("doc_id") or d.get("id"))

missing = sorted(jud_ids - corpus_ids)
print(f"Judgment ids in corpus: {len(jud_ids) - len(missing)} / {len(jud_ids)}")
if missing:
    print("Sample missing:", missing[:10])
```

### Task B. GLMP embedding backfill (104 docs) — production fix, not benchmark blocker

```bash
cd ~/copernicus-web-public
source venv_embeddings/bin/activate
export OPENAI_API_KEY='sk-...'
python backfill_embeddings.py --submit --collection glmp_processes
python backfill_embeddings.py --check && python backfill_embeddings.py --write
```

### Phase 1 report back

- doc_id check: `N/M` judgment ids in corpus export
- GLMP: `108/108` embedded (if backfill completed)

---

## Phase 2 — After phase 1 (Gary or Cursor)

Run track A per `papers/dense_retrieval_benchmark_handoff.md`:

- Notebook: `papers/retrieval_pilot_colab_bundle.ipynb` §6b + §10
- Frozen corpus + queries + existing `judgments.csv`
- Outputs: `rankings_openai_dense.csv`, `openai_doc_embeddings.npz`, `table4_metrics_lexical_vs_openai.csv`

Gary pastes key metrics to Cursor (at minimum mean nDCG@10, Precision@10, MRR, no-relevant-in-top-10 count).

---

## Phase 3 — Cursor drafts paper (after metrics)

Edit `papers/knowledge_engine_vision.md`:

- §6 dense retrieval results (second column or Table 5)
- Evaluation Roadmap track (A) — mark complete with date
- §7 — soften “formal dense evaluation pending” if appropriate
- Optional abstract sentence (only if Gary approves framing)

**Do not change:** lexical Table 4 values, query/corpus SHA256s, frozen Zenodo DOI for original bundle.

Claude’s role after this: **review** Gary’s paste of Cursor’s draft — Zenodo deposit description, abstract wording, interpretation polish.

---

## Do NOT do in phase 1

- Do not edit paper prose until metrics exist (phase 3)
- Do not modify frozen corpus, `judgments.csv`, or lexical Table 4
- Do not re-embed Firestore papers for benchmark purposes — track A uses frozen JSONL only
