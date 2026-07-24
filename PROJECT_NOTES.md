# Project Notes

This file tracks two active threads that have shared one Cursor chat.

## Proof Graph Pilot

Goal: Publish and improve the Proof Graph Pilot as part of the ATAP site.

Current status:

- Pilot files were uploaded under the GCS mathematics-processes-database path.
- The live mathematics database table was updated with a visible **Proof Graph Pilot** link.
- The Markdown proof files were converted into companion HTML pages so Mermaid diagrams render in the browser instead of showing as plain Markdown.
- The pilot landing page links were updated to point to the rendered HTML proof pages.

Useful paths and URLs:

- Local database page: `huggingface-space/mathematics-processes-database/mathematics-database-table.html`
- Local proof graph source folder used earlier: `/mnt/c/Users/garyw/.cursor/projects/empty-window/proof-graphs/`
- Published pilot: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/mathematics-processes-database/proof-graphs/index.html`

Next likely work:

- Review the rendered proof pages visually.
- Improve graph readability, styling, navigation, or proof metadata.
- Decide whether to keep generated HTML pages as build artifacts or add a repeatable conversion script.

## GLMP Papers And Colab Analyses

Goal: Prepare GLMP paper sources and supporting analyses for review and submission.

Current status:

- Canonical Markdown sources were copied into `collaborations/krampis-virtual-cell/`.
- RPE1 replication notebooks were created under `rpe1-replication/`.
- Error-pattern analysis notebooks were created under `error-pattern-analysis/`.
- Paper III source was revised and pushed in commit `13bc59add`.
- Methods paper and Synthesis source were revised/validated and pushed in commit `39778337d`.

Useful paths:

- Paper sources: `collaborations/krampis-virtual-cell/`
- RPE1 replication: `rpe1-replication/`
- Error-pattern analysis: `error-pattern-analysis/`

Current interpretation:

- RPE1 replication is limited by benchmark score coverage: only 5 of 17 inherited Class III RPE1 genes had available scPerturBench scores.
- K562 error-pattern analysis supports larger Class III error magnitude, while bimodality and within-circuit correlation are underpowered or inconclusive with the available benchmark summaries.

Next likely work:

- Continue paper revisions after Krampis/Claude feedback.
- Revisit RPE1 if broader per-gene scores or model inference outputs become available.
- Revisit attractor-confusion tests if raw per-cell prediction residuals become available.
