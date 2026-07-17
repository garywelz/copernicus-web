# PR draft notes — stub gate (observe-first) + minimal identity ids

## Critical path
**Jetson SSH restore** — main alone does not stop AM/PM `scout_ingest.sh`.

## Identity fingerprint (minimal core — not wide allowlist)
Hash **identity**, not record state:

- normalized title  
- first-author surname  
- year (or year from `published_date`)  
- plus doi / pmid / arxiv_id / bibcode when present  

**Excluded (mutable knowledge):** abstract, categories, sources, urls, journal_*, acquired_date, and any future scout metadata.

Title normalized (case, whitespace, trailing punctuation, crude LaTeX strip) like DOI.

No list-order trap: fingerprint holds scalars only (first surname, not full authors list).

**Observe-mode side effect:** empty/Untitled stubs collapse onto a small set of last-resort ids → `--skip-existing` collapses remints even before enforce. Empty-title stubs fingerprint as `{}`; literal `"Untitled"` as `{"title":"untitled"}` — two collapse ids, both bounded.

The **~97/day prediction is `gate_hits_day_log`** (line count of the shared daily reject JSONL across AM+PM), not this-run `gate_hits` and not new Firestore docs. “0 new stubs” is not a failed observation.

## Trap notes
1. `sort_keys=True` + volatile `acquired_date` in hash → false determinism.  
2. Wide content allowlist → enrichment remints. Narrowed to identity core.

## Gate
Default `--stub-gate-mode observe`; conjunctive Untitled∧no-id; full payload → local day JSONL (append) + per-run GCS object.

`ingest_metadata_to_firestore.sh` pins `--reject-log` and `--reject-gcs-uri` explicitly (do not rely on `--root` path arithmetic).

## Tests
`python cloud-run-backend/scripts/test_ingest_papers_id_stability.py`
- cross-process PYTHONHASHSEED  
- unexpected extra keys  
- title normalization  
- **enrichment (abstract+categories) → same id**  
- stub collapse  
- predicate conjunctive  

## Suggested commit (when approved)
```
Observe-mode stub gate; minimal-identity sha256 paper ids

Fingerprint title+first-author+year(+ids), not enrichment fields;
log full gate hits to GCS; default observe until ~97/day prediction checked.
```
