# Zenodo Upload: Dense Retrieval Track A Bundle (June 2026)

Companion deposit to the May 2026 evaluation freeze (https://doi.org/10.5281/zenodo.18463303).

## File to upload

`papers/dense_track_a_bundle_20260608.zip` (~280 MB; includes `openai_doc_embeddings.npz`)

## Suggested metadata

- **Publication type:** Dataset
- **Title:** CopernicusAI dense retrieval benchmark (track A) — 30-query OpenAI embedding evaluation
- **Description:** Offline dense retrieval evaluation over frozen `research_papers_20260526.jsonl.gz` (59,499 documents) using OpenAI `text-embedding-3-small` (1536d). Includes rankings, expanded judgments (558 pairs), metrics manifest, and reproduction script. Corpus and lexical baseline remain in the parent Zenodo deposit.
- **Related identifier:** Is supplement to https://doi.org/10.5281/zenodo.18463303
- **Keywords:** dense retrieval, embeddings, nDCG, OpenAI, reproducibility

## After publish

1. Replace `*[to be added on upload]*` in `knowledge_engine_vision.md` roadmap item (A) with the new DOI.
2. Add DOI to `manifest.json` as `eval_dense_archive_doi`.
3. Notify co-authors / journal if resubmitting.
