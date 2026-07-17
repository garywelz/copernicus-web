# Diagnostic plan — `research_papers` stub ingestion leak

**Date:** 2026-07-17 (revised same day after Claude Chat review)  
**Status:** Phases **1–2 EXECUTED** — see `papers/STUB_LEAK_PHASE12_FINDINGS_2026-07-17.md`. Still no deletes / cleanup / gate implementation.  
**Repo:** `copernicus-web` only (do not copy to `glmp/docs`)  
**Context:** `papers/KNOWLEDGE_ENGINE_BROWSE_LINKS_HANDOFF_2026-07-17.md`  
**Constraint:** May eval freeze untouched; July ops snapshot stays ops-only  

---

## Finding that drives this

| | May 2026-05-26 | July 2026-07-17 |
|---|---:|---:|
| n | 59,499 | 64,164 |
| Untitled stubs | 182 | 1,441 |
| Any-link % | 99.69% | 97.73% |

Marginal rate since May: **~1,259 stubs / ~4,665 new docs ≈ 27%**.  
Corpus-wide 2.25% dilutes years of good ingest. Stubs are evidence — **do not clean before distinguishing the hypotheses below.**

Stub fingerprint (July gzip, **all 1,441** matching Untitled ∧ no id):
- `firestore_id` = `paper_*` (100%)
- `sources` = `[]` (100%)
- **`abstract` empty (100%)** — see §“Content check”
- `embedding_model` set on **1,162 / 1,441** (80.6%)

---

## Competing hypotheses (highest-value distinction)

`_doc_id_for_paper` last resort:

```python
return f"paper_{abs(hash(json.dumps(paper, sort_keys=True, default=str)))}"
```

Python randomizes `hash()` per process unless `PYTHONHASHSEED` is fixed. **Same payload → different id → no upsert collision → new document every run.**

| Hypothesis | Meaning | Expected Phase-2 histogram | Expected cosine on stub vectors |
|---|---|---|---|
| **H-remint** | Small bad batch re-ingested daily by cron; stub count is a *clock* | ~linear **~24/day** since late May (~1259/52) | Few tight clusters (near-duplicate `"Untitled"` embeds) |
| **H-junk-flood** | Many distinct bad papers ingested once | Step change + plateau, or irregular bursts | Many distinct / diffuse clusters |

**Fixes differ:** stable content-hash id + idempotent upsert (H-remint) vs upstream metadata quality + reject (H-junk-flood). Distinguishing them is the point of Phases 1–2.

Arithmetic check favoring H-remint a priori: **~24 stubs/day ≈ daily scout cadence.**

---

## Two gates failed (code-grounded)

### Gate 1 — Write path accepts junk *and* breaks idempotency

**Primary suspect:** `cloud-run-backend/scripts/ingest_papers_from_metadata_json.py`

| Behavior | Code |
|---|---|
| Defaults missing title to `"Untitled"` | `title = paper.get("title") or "Untitled"` |
| Empty `sources` when no pmid/arxiv/source | `_infer_sources` → `[]` |
| Unstable `paper_*` ids | `paper_{abs(hash(...))}` — **breaks idempotency** |

Wired by: `run_daily_scout_with_ingest.sh` → `ingest_metadata_to_firestore.sh` → that script  
Cron: `install_daily_scout_cron_with_ingest_1015_ny.sh` (NY 10:15).

Named sources remain 100% linkable in July audit — leak is the fallback path and/or bad JSON that reaches it.

**Secondary writers to rule out:** `sync_research_papers.py`, papers API upload endpoints.

### Gate 2 — Embed path has no quality precondition

`auto_embedding.py` / index paths embed truthy title `"Untitled"` even with empty abstract.  
July: 1,162 stubs already carry `embedding_model` (mostly `text-embedding-3-small`).

---

## Content check (done on July ops gzip — read-only)

**Question:** Are stubs recoverable papers (title missing but abstract present)?

**Answer:** **No.** Of 1,441 Untitled ∧ no-identifier stubs:
- `empty_abstract`: **1,441 (100%)**
- `combined_beyond_title`: **0**
- Embed text is effectively `"Untitled"` alone

⇒ Q4 reject framing stays valid for this population: not “throw away real papers with content,” but “stop writing empty shells.” Repair-from-abstract is **not** available for these 1,441. (If Phase 1 finds a *different* non-stub population, revisit.)

---

## Phase 1 — Who writes these? (approved)

1. Confirm cron → shell → `ingest_papers_from_metadata_json.py` flags/root.  
2. On Jetson: join stub ids / empty-title JSON under `metadata-database/papers/`; grep `ingest.log` / `cron.log` May–July.  
3. Note: unstable `paper_*` ids may **not** join to on-disk JSON by id — join by path/mtime/content or log lines; mark join failure as a finding.  
4. Rule secondary writers in/out.

---

## Phase 2 — When / remint vs flood? (approved)

### Timestamp projection (ops-only)
July minimal gzip has no timestamps. Export a **new** ops file (not May freeze):

Fields: `firestore_id, title, doi, pmid, arxiv_id, sources, created_at, updated_at, ingested_at, embedding_model, raw_source_id`  
(prefer adding `--projection timestamps` to exporter; else `--projection full` and strip locally).

Then histogram Untitled∧no-id stubs by `created_at` day (fallback `ingested_at`, then `updated_at` — **label which**).  
**Decisive:** linear ~24/day → H-remint; step+plateau → H-junk-flood.

### Duplicate test pulled forward (was Q3)
Stubs already embedded — **no new export required for vectors if Firestore holds `embedding`.**

When executing:
1. Fetch embeddings for the 1,441 stub ids (or sample if full pull is costly — say so).  
2. Pairwise cosine (1,441² is fine in numpy) or cluster.  
3. If vectors collapse to a handful of near-identical clusters → **H-remint confirmed** independent of timestamps.  
4. Timestamps + cosine together are decisive.

**Limit:** If live docs only have `embedding_model` marker and vectors live only in Vertex without easy export, mark that limit and rely on timestamp histogram + offline embed of the string `"Untitled"` as a weaker proxy.

---

## Q3 — Retrieval impact (after 1–2; still cheap)

- Do **not** re-run nDCG on July; May freeze stays citable.  
- Optional: 5 live semantic queries; count Untitled `paper_*` neighbors.  
- Cosine/cluster work moved into Phase 2 above.

---

## Q4 — Gates (proposal only — do not implement)

### Write-time
Reject when title blank/`Untitled` **and** no doi/pmid/arxiv/bibcode.

### Idempotency fix (propose regardless of H-*)
**Never** use `abs(hash(...))` for ids. Propose:

```text
doc_id = "paper_" + sha256(canonical_payload).hexdigest()[:32]
# canonical_payload e.g. normalized title + "\n" + abstract, or raw source JSON bytes
```

Stable across processes → upsert/`skip-existing` actually works → **closes remint leak by construction.**

### Embed-time
Skip when same reject predicate holds, or embed text ∈ {`"Untitled"`, empty}.

**Order later:** confirm H-* → ship write id+reject + embed skip → *then* decide fate of the 1,441.

---

## Execution order (after “go”)

| Phase | Action | Destructive? |
|---|---|---|
| 1 | Writer + Jetson join + logs | No |
| 2 | Timestamp projection + histogram + stub cosine/cluster | Read-only export + read embeddings |
| 3 | Optional live neighbor probes | Read-only |
| 4 | Gate + sha256-id **PR for review** | Code only after review; no stub deletes |

---

## Out of scope

Browse titled-only filter; non-GLMP viewers; next-auth; stub deletes; July → eval freeze; copying this plan to `glmp/docs`.

---

## Ask for Gary

Phases 1–2 are approved in substance. Reply **go** to execute them in this `copernicus-web` Cursor chat (Jetson may be needed for log/JSON join).

---

*End of revised diagnostic plan.*
