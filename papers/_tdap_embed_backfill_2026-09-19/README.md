# Embedding backfill pin — `research_papers`

- Pinned at (UTC): 2026-09-20T00:37:01Z
- n: **129**
- Model/dims: `text-embedding-3-small` / 1536
- Predicate: embedding_model empty/missing AND title != Untitled
- Provenance:
- id_prefix_counts: {'arxiv': 1, 'crossref': 128}
- corpus_scanned: 118874
- created_at_min: 2026-09-19T23:43:18+00:00
- created_at_max: 2026-09-20T00:23:41+00:00
- with_abstract: 22
- untitled_skipped: 0
- note: Scout biology ingest without embed pass (measured 2026-07-22); not GLMP flowchart hand-delivery.

## Sequence

1. `--dry-run` (no writes)
2. `--pilot N` (episodes: start with 5, then live find_nearest proof)
3. `--run` after remainder-go
4. Re-census + findability probe (not count alone)

Rerun-safe: per-doc skip if `embedding_model` already set.

Abort behavior: StructuralError (wrong dim/model, empty API response) hard-stops
immediately and bypasses retries. Transient API errors (429/5xx/timeout) retry a
few times with backoff, then hard-stop. Rerun is safe either way.
