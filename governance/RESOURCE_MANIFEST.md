# Resource Pointer Manifest

*Shared reference. Canonical source in GitHub; copies in each Project's knowledge
base. **Do not upload the resources themselves into any Project** — the shared
collections grow autonomously via cron and any upload is stale on arrival. List
the pointer here once; fetch live with a plain (non-cache-busted) request.*

*`⟨FILL IN⟩` marks a canonical URL/ID I don't have — please supply or correct.*

---

## Hugging Face Spaces

| Resource | URL |
|---|---|
| CopernicusAI (Knowledge Engine) | https://huggingface.co/spaces/garywelz/copernicusai |
| Programming Framework | https://huggingface.co/spaces/garywelz/programming_framework |
| GLMP | https://huggingface.co/spaces/garywelz/glmp |
| Metadata Database | https://huggingface.co/spaces/garywelz/metadata_database |
| Science Video DB | https://huggingface.co/spaces/garywelz/sciencevideodb |

## GitHub

| Resource | URL |
|---|---|
| Owner | https://github.com/garywelz |
| GLMP repo | https://github.com/garywelz/glmp |
| Cloud-run backend | Not a separate repo — path `cloud-run-backend/` inside `copernicus-web` (no nested `.git`/submodule; e.g. `cloud-run-backend/main.py`, `cloud-run-backend/endpoints/content/routes.py`) |
| GLMP GitHub Pages | https://garywelz.github.io/glmp |
| Other suite repos | https://github.com/garywelz/progframe · https://github.com/garywelz/sciencevideodb · https://github.com/garywelz/metadata-database · https://github.com/garywelz/mathematics-database (repo names per `CLAUDE.md:35-44`; not independently confirmed to exist on GitHub). **Planned — not yet live:** `biology-database`, `chemistry-database`, `computer-science-database`, `physics-database` — `CLAUDE.md:41-44` marks their Spaces "not yet created" |

## Cloud (records of truth)

| Resource | ID / URI |
|---|---|
| GCP project (quota) | regal-scholar-453620-r7 |
| GCS bucket(s) | Public: `regal-scholar-453620-r7-podcast-storage` (confirmed, e.g. `cloud-run-backend/canonical_helpers.py:85`, `CLAUDE.md:24`). Private: `regal-scholar-453620-r7-internal` — **user-supplied, not repo-verified**: hosts the GLMP master TODO |
| Firestore collection | `research_papers`, project `regal-scholar-453620-r7`, database `copernicusai` (`cloud-run-backend/check_sources.py:11-12,15`) |

## Status pages

| Page | URL |
|---|---|
| Knowledge Engine status | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.html (`huggingface-space/ENHANCEMENT_PLAN.md:9`; JSON source `components/knowledge-engine/constants.ts:6-7`) |
| GLMP status | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/GLMP_STATUS.html — **user-supplied, not repo-verified**: no reference to this file found in this repo |

## Shared resource collections (cron-grown; available to ALL initiatives)

| Collection | Access pointer |
|---|---|
| Metadata database | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/papers-database-table.html (`components/knowledge-engine/constants.ts:35-36`) |
| Science video DB | https://huggingface.co/spaces/garywelz/sciencevideodb (`docs/planning/CONTENT_INGESTION_PLAN.md:66-67`) — same Space already listed above; no separate query endpoint found in this repo |
| Mermaid chart collection | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/glmp-database-table.html (`components/knowledge-engine/constants.ts:26`) |
| Podcast collection (~90) | `GET https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/content/browse?content_type=podcasts` (`components/knowledge-engine/constants.ts:4`; `cloud-run-backend/endpoints/content/routes.py:15,97-99`) |

## Zenodo (DOIs)

*Recorded DOIs are **concept DOIs** (resolve to the latest version) — a concept DOI and its
version DOI differ by one integer by design, so a one-digit gap against another citation of
the same record is not necessarily an error.*

| Work | Concept DOI |
|---|---|
| CopernicusAI knowledge-engine paper | 10.5281/zenodo.18463303 |
| Programming Framework companion paper | 10.5281/zenodo.18463441 |
| GLMP methods paper | 10.5281/zenodo.20831780 — confirmed on the Zenodo record as the **concept DOI** ("Cite all versions"); `20831781` is the version-1.4 DOI for the same paper, not a different work |
| Proofs-as-graphs (math) paper | 10.5281/zenodo.20510602 — confirmed via the Zenodo API as the **concept DOI** (`conceptrecid: 20510602`), currently resolving to v2.0 "Proof Graphs and Algorithm Capsules: A Corpus Study of Diagonalization Proofs from Cantor to Gödel to Goodstein". `20510603` is the superseded v1.0 DOI (`is_last: false`), cited under an earlier title in `nsf-proposal/Gary_Welz_Resume.md:51-52` — that citation is stale, not this manifest |
| Citable eval corpus (May freeze) | No Zenodo deposit exists — corpus lives at the GCS mirror only: `gs://regal-scholar-453620-r7-podcast-storage/research_data/snapshots/research_papers_20260526.jsonl.gz` (`papers/meta_partial.json:10`) |

## Identity

| Item | Value |
|---|---|
| ORCID | 0009-0005-7806-0892 |
| Google Scholar | https://scholar.google.com/citations?user=3wTcI6EAAAAJ |
| Affiliation | CUNY Graduate Center — New Media Lab |
