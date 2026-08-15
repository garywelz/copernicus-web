# Resource Pointer Manifest

*Shared reference. Canonical source in GitHub; copies in each Project's knowledge
base. **Do not upload the resources themselves into any Project** — the shared
collections grow autonomously via cron and any upload is stale on arrival. List
the pointer here once; fetch live with a plain (non-cache-busted) request.*

*`⟨FILL IN⟩` marks a canonical URL/ID I don't have — please supply or correct.*

*Last verified against reality: 2026-08-04 — every file-path citation checked
against current `main` (`governance/check_citations.py`, exit 0), two dead
citations found and fixed, one further correction (a claimed stale DOI that
turned out current) caught by direct file inspection, not by the checker.
The "Scope of a Resource collection" subsection below was added 2026-08-05,
after this pass — it is not covered by the above check and carries no
verification claim of its own; flipping this date to cover it would repeat
the false-claim pattern this field exists to prevent.*

---

## Hugging Face Spaces

| Resource | URL |
|---|---|
| CopernicusAI (Knowledge Engine) | https://huggingface.co/spaces/garywelz/copernicusai |
| Programming Framework | https://huggingface.co/spaces/garywelz/programming_framework |
| GLMP | https://huggingface.co/spaces/garywelz/glmp |
| ATAP (Axiomatic Theories, Algorithms and Proofs) | https://huggingface.co/spaces/garywelz/atap — renamed 2026-07-23 from `mathematics-database`; old URL redirects but is no longer canonical |
| Metadata Database | https://huggingface.co/spaces/garywelz/metadata_database |
| Science Video DB | https://huggingface.co/spaces/garywelz/sciencevideodb |

## GitHub

| Resource | URL |
|---|---|
| Owner | https://github.com/garywelz |
| GLMP repo | https://github.com/garywelz/glmp |
| ATAP repo | https://github.com/garywelz/atap — renamed 2026-07-23 from `mathematics-database`; sibling of the GLMP repo (both are engines, not nested under a discipline), not part of "Other suite repos" below. Old URL redirects but is no longer canonical |
| Cloud-run backend | Not a separate repo — path `cloud-run-backend/` inside `copernicus-web` (no nested `.git`/submodule; e.g. `cloud-run-backend/main.py`, `cloud-run-backend/endpoints/content/routes.py`) |
| GLMP GitHub Pages | https://garywelz.github.io/glmp |
| Other suite repos | https://github.com/garywelz/progframe · https://github.com/garywelz/sciencevideodb · https://github.com/garywelz/metadata-database (repo names per `CLAUDE.md:35-44`; not independently confirmed to exist on GitHub). **Planned — not yet live:** `biology-database`, `chemistry-database`, `computer-science-database`, `physics-database` — `CLAUDE.md:41-44` marks their Spaces "not yet created" |

## Cloud (records of truth)

| Resource | ID / URI |
|---|---|
| GCP project (quota) | regal-scholar-453620-r7 |
| GCS bucket(s) | Public: `regal-scholar-453620-r7-podcast-storage` (confirmed, e.g. `huggingface-space/scripts/generate_status_page.py:26`, `CLAUDE.md:24`). Private: `regal-scholar-453620-r7-internal` — **user-supplied, not repo-verified**: hosts the GLMP master TODO |
| Firestore collection | `research_papers`, project `regal-scholar-453620-r7`, database `copernicusai` (project + database: `huggingface-space/scripts/media_catalog/export_episodes_catalog.py:26`; collection: `huggingface-space/scripts/export_research_papers_jsonl.py:3,7`) |

## Status pages

| Page | URL |
|---|---|
| Knowledge Engine status | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.html (`huggingface-space/ENHANCEMENT_PLAN.md:9` — **(archived)**, moved out of the tree in an earlier cleanout; JSON source still live at `components/knowledge-engine/constants.ts:6-7`, which evidences the `.json` endpoint but **not** this `.html` page) |
| GLMP status | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/GLMP_STATUS.html — **user-supplied, not repo-verified**: no reference to this file found in this repo |

## Shared resource collections (cron-grown; available to ALL initiatives)

| Collection | Access pointer |
|---|---|
| Metadata database | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/papers-database-table.html (`components/knowledge-engine/constants.ts:35-36`) |
| Science video DB | https://huggingface.co/spaces/garywelz/sciencevideodb (`docs/planning/CONTENT_INGESTION_PLAN.md:66-67`) — same Space already listed above; no separate query endpoint found in this repo |
| Mermaid chart collection | https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/glmp-database-table.html (`components/knowledge-engine/constants.ts:26`) |

*The podcast collection is not listed here — it's an engine-authored output, not a
gathered-external input. See **Products** below.*

### Scope of a Resource collection

*Proposed 2026-08-05 (Claude Chat), placed here 2026-08-05 — not covered by the
verification pass dated above; see the note on this document's header.*

A Resource collection is **one researcher's working literature**, not a
discipline's library.

The collection serving GLMP and ATAP is a single shared corpus, because both are
Gary Welz's projects and these are his sources. The foundational papers
demonstrate why: paper-I, paper-II, and paper-III draw on Voevodsky and homotopy
type theory alongside Shen-Orr's *E. coli* network motifs, Rice's theorem
alongside the Gardner toggle switch — 73 references across the three (see
`GLMP_MASTER_TODO.md` item 46 for the independently re-counted figure), mixing
GLMP and ATAP sources in the same argument. Partitioning by discipline would cut
those papers in half.

**A different scientist, with different projects, would have a different
collection.** The collection is indexed to a researcher's programme, not to a
subject heading. This is what distinguishes a Resource from a database.

**Charts are a best current approximation, not a certified result.** A
biologist review can make a GLMP chart better. It does not verify the
chart the way a Lean proof verifies a theorem. Acquisition may record
that a chart currently names a paper; it does not elect a canonical
source. See A2 requirement 4 (restated 2026-08-15).

**Bounded by relevance, not by volume.** The boundary is topical, not numeric.
Within the fields the projects work in — molecular genetics and gene regulation
for GLMP; logic, foundations, graph theory, and proof theory for ATAP — the
collection aims at depth a working specialist would recognise as adequate: the
classics through to the frontier. Beyond those fields, the collection does not
expand by breadth, but it admits work from adjacent disciplines — philosophy,
computer science, physics — when semantic relationship earns it. That is not a
tolerated leak in the boundary; it is the point. Embedding-based retrieval is
what makes this tractable: relevance is measured by meaning rather than by
subject tag.

*The mechanism, not just the principle: each project's `docs/research_focus.json`
declares its own adjacent fields in a `horizons` list (confirmed 2026-08-05 —
see `huggingface-space/scripts/acquire_papers/A2-standing-acquisition-contract.md`,
requirement 1). This paragraph states why adjacency is admitted; `horizons` is
where a project says which adjacency it means.*

**What this rules out:**
- **Undirected volume targets.** Acquiring *n* papers per run, where *n* is the
  goal, optimises the wrong thing. A run that acquires many papers against
  declared research questions and field-coverage gaps is doing its job; a run
  that acquires papers because a number is the number is not.
- **Size as an achievement metric.** "~62,900 papers" describes the collection;
  it does not commend it. On 2026-08-05 the collection held ~62,900 papers and
  216 of the 217 papers GLMP's own flowcharts cite were absent from it. A
  collection missing the works its own project depends on is not succeeding at
  scale, whatever the count.
- **Discipline as a filter.** A relevance judgment that rejects a paper for
  being mathematics when the reader is a biologist defeats the collection's
  purpose.
- **Ungated bibliography ingest.** Pulling every reference from every
  admitted paper is undirected volume in a new costume: one hop from a few
  thousand papers is tens of thousands of candidates; a second hop is the
  million-paper collection this scope statement exists to prevent. A stored
  reference list is Map metadata, not an acquisition queue. Citation
  expansion, when used, is one hop from named seed classes (chart sources,
  flagged and researcher-cited papers, later a small attributed scout
  slice), capped, never recursive, and is not a change to the daily scout
  cron. See `huggingface-space/scripts/acquire_papers/A2-standing-acquisition-contract.md`
  requirement 8 (decided 2026-08-15).

**The measure:** coverage against what the projects declare they are working on,
and against what a specialist would expect to find in the field. Both are
reportable. Neither is a count of documents. See `GLMP_MASTER_TODO.md` item 46
(the standing acquisition contract, A2) for the mechanism this scope statement
is meant to constrain.

## Products (engine-authored outputs)

| Product | Access pointer |
|---|---|
| CopernicusAI podcast collection (~90) | `GET https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/api/content/browse?content_type=podcasts` (`components/knowledge-engine/constants.ts:4`; `cloud-run-backend/endpoints/content/routes.py:15,97-99`) — this is its authored home; the same endpoint is also where it's registered into Resources for downstream consumption (`governance/SUITE_REORG_PLAN.md` §1, "Products → Resources") |

## Zenodo (DOIs)

*Recorded DOIs are **concept DOIs** (resolve to the latest version) — a concept DOI and its
version DOI differ by one integer by design, so a one-digit gap against another citation of
the same record is not necessarily an error.*

| Work | Concept DOI |
|---|---|
| CopernicusAI knowledge-engine paper | 10.5281/zenodo.18463303 |
| Programming Framework companion paper | 10.5281/zenodo.18463441 |
| GLMP methods paper | 10.5281/zenodo.20831780 — confirmed on the Zenodo record as the **concept DOI** ("Cite all versions"); `20831781` is the version-1.4 DOI for the same paper, not a different work |
| Proofs-as-graphs (math) paper | 10.5281/zenodo.20510602 — confirmed via the Zenodo API as the **concept DOI** (`conceptrecid: 20510602`), currently resolving to v2.0 "Proof Graphs and Algorithm Capsules: A Corpus Study of Diagonalization Proofs from Cantor to Gödel to Goodstein". `20510603` is the superseded v1.0 DOI (`is_last: false`) |
| Citable eval corpus (May freeze) | No Zenodo deposit exists — corpus lives at the GCS mirror only: `gs://regal-scholar-453620-r7-podcast-storage/research_data/snapshots/research_papers_20260526.jsonl.gz` (`papers/meta_partial.json:10`) |

## Identity

| Item | Value |
|---|---|
| ORCID | 0009-0005-7806-0892 |
| Google Scholar | https://scholar.google.com/citations?user=3wTcI6EAAAAJ |
| Affiliation | CUNY Graduate Center — New Media Lab |
