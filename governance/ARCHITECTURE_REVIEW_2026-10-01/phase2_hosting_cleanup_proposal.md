# Hosting cleanup, Phase 2: proposal (draft, nothing executed)

*Core lane (Claude Code), 2026-10-04. Read-only review. For Gary's decision on or after
2026-10-05, as BULLETIN entries 005, 006, 007, 008, 009, 010 and 011 ask. No deletion, IAM
change, config change or API enablement was made to produce this. The only writes were this file
(on a branch) and one private note in the internal bucket (see "Filed privately").*

**Items filed privately** (AGENT_ROLES rule 17). Rows for items whose fix is not yet live are
left out of the tables and totals below; each carries its own action, which Gary has been told
about separately. **One item is no longer private:** `glmp-service` was closed to the public on
2026-10-04 with Gary's approval and is described in BULLETIN entry 018 (merged in PR #37), so it now
appears below as a retire row.

---

## 1. Summary

| | Count | Recommendation |
|---|---|---|
| Cloud Run services shown (the 6 function-backed services are counted under Cloud Functions) | 9 | 6 RETIRE, 3 KEEP |
| Cloud Functions | 6 | 3 RETIRE, 3 KEEP |
| Cloud Run jobs (missing from the system map) | 2 | 2 KEEP |
| Cloud SQL instances | 4 | 3 RETIRE (export, stop first), 1 KEEP and harden |
| Buckets | 15 | 4 RETIRE (2 redundant backups whole, 2 build-archive buckets in part), 11 KEEP |
| Artifact Registry repos (not in the request) | 4 | RETIRE unreferenced and stale images |
| Data stores: Firestore (17 collections), canonical process JSON, public database tables, internal bucket | see 4I | KEEP only, no action commands |
| Vercel projects | 32 (10 named in governance, 22 unknown from this seat) | Gary's dashboard only |
| Pending items | 4 shown | see section 4H |

**Estimated spend that this proposal touches, about $85 a month, of which about $35 to $50 is
removable** (section 6 gives the derivation and its caveats). The larger prize is attack surface:
six closed services, three functions and three databases that nothing calls would stop existing.

Nothing in this file is urgent. The privately filed items are, and Gary has been told separately.

**Order of work (lowest to highest risk).** Details and commands are in section 5.

| Batch | When | What | Reversible? |
|---|---|---|---|
| 1 | on approval, from 2026-10-05 | back up configs; harden databases; trim the network entry on one database; prune old Cloud Run revisions | yes, all |
| 2 | after Batch 1, about 2026-10-06 | stop (not delete) three databases, `glmp-db` after its export; Vercel deployment protection is deferred | yes, one command or one toggle |
| 3 | after 7 quiet days on Batch 2, about 2026-10-13 | delete 6 Cloud Run services and 1 function (`copernicus-podcast-form`); delete the disabled key (entry 005), not before 2026-10-13. `generate-podcast` and `glmp_process_suggestion` wait for the GLMP lane | yes, from saved config while the image exists; the key deletion is not reversible |
| 4 | not before 2026-10-11 | delete revision -00262-kfx; trim old build archives; delete two redundant backup buckets; delete unreferenced images | partly (7-day undelete on archives; backups recopyable; images need a rebuild) |
| 5 | after at least 30 days stopped | delete 3 databases; delete retired Vercel projects (deferred) | no, or only by import / recreate |

---

## 2. What this review could and could not see

- **Requests.** Cloud Monitoring `run.googleapis.com/request_count`, 2026-09-04 to 2026-10-04,
  cross-checked against 18,740 Cloud Run request-log entries for the same window. The two agree on
  which six services had any traffic (podcast-api 18,269 by metric vs 18,275 by log; frontend 391 vs
  404; the rest within one or two). Retention is 30 days, so nothing earlier is visible.
- **The "zero" results were checked, not assumed** (rule 7). An empty result could mean the
  instrument does not record rejected calls. It does: one unauthenticated GET to the closed
  `copernicus-api` during this review returned 403 and appeared in the request log within a minute.
  So a closed service with no 403s in its log was not called. (That probe is the one 403 now in
  `copernicus-api`'s log.)
- **Two instrument bugs caught and fixed along the way.** Windows `gcloud` output carries a `\r`
  that silently broke a shell loop (every item but the last reported "not public"); the bucket
  comparison first compared names with a `#generation` suffix still attached and reported
  "nothing matches". Both were re-run after the fix; the figures below come from the corrected runs.
- **Billing is not readable.** The Cloud Billing API is disabled on this project and was left
  disabled. Cost figures are therefore *estimates from quantities* (tier, hours, GB). The pricing
  pages would not render through the fetch tool, so the unit prices in section 6 are remembered list
  prices, **unverified**; confirm them in Billing → Reports before relying on any dollar figure.
- **Vercel is invisible from this seat** (no CLI, no token). Section 4G uses only what governance
  and the request logs show.
- **Key-usage history for the disabled key could not be obtained.** The policy-intelligence query
  returned nothing and stalled; it needs an API that this review did not enable.
- **Counts of bucket requests include this session's own listing and metadata calls** (about one or
  two per bucket), so a count of 1 or 2 means untouched.

---

## 3. Phase 1 watch: did anything break since 2026-09-28?

Entry 006 asked for approval "if nothing has broken", and told agents to report any failure that
traces to a closed item. Result: **no failure traces to any of the seven.**

| Item | Closed (UTC, 2026-09-28) | Requests, 30 days | Log entries after closure | Callers found in code |
|---|---|---|---|---|
| copernicus-backend | 23:21:44 | 0 | none (no 403s either) | none |
| copernicus-research-backend | 23:21:54 | 0 | none | none |
| copernicus-podcast-generator | 23:22:04 | 0 | none | none |
| research-metadata-api | 23:22:13 | 0 | none | none |
| copernicus-podcast-form (function) | 23:22:23 | 0 | none | none found (its own source is `cloud-function/main.py`) |
| copernicus-filestore (bucket, empty) | 23:22:32 | 16 API calls, all admin or listing: 8 ListObjects, 5 GetIamPolicy, 2 GetBucketMetadata, 1 SetIamPolicy; **0 object reads or writes** | n/a | none |
| generate-podcast (function) | 23:24:29 | 7, all `GET` returning 405 between 22:58:13 and 22:58:59, **26 minutes before closure**, scripted-looking | none | `glmp/podcast_form.html:189`, `glmp/test_podcast_system.py:21`, `glmp/basic_test.py:27`, `glmp/simple_analysis.py:40`, `glmp/DEPLOYMENT_GUIDE.md:72,79,94` |

Also closed under entry 005 (23:00:15): `copernicus-api`, 0 requests, no caller.

The one thing to know about `generate-podcast`: `glmp/podcast_form.html` still points at it, so
that form would fail if someone opened it. Nothing in the logs shows it was used, and nothing shows
it published (no copy in the public bucket). Entry 005 already says the glmp-root podcast tooling
belongs in this repo; retiring the function should wait for that move.

---

## 4. Inventory and recommendations

Key: **Req** = requests in the 30 days to 2026-10-04. **~$/mo** is an estimate (section 6).
**Batch / who** points to section 5. "Gary" means a dashboard action; "CC" means Claude Code
after Gary approves.

### 4A. Cloud Run services

| Service | Public? | Req | Caller in code | ~$/mo | Rec | Reason | Batch / who |
|---|---|---|---|---|---|---|---|
| copernicus-api | no (closed 09-28) | 0 | none (prose mentions only: `governance/CONSTITUTION.md:66`, `glmp/docs/MASTER_TODO_DASHBOARD.html:702`) | ~0 | **RETIRE** | no traffic in 30 days; nothing calls it; 39 old revisions; attached to `copernicus-db` | 3 / CC |
| copernicus-backend | no (closed 09-28) | 0 | none | ~0 | **RETIRE** | closed, silent for a week, no caller | 3 / CC |
| copernicus-research-backend | no (closed 09-28) | 0 | none | ~0 | **RETIRE** | same | 3 / CC |
| copernicus-podcast-generator | no (closed 09-28) | 0 | none | ~0 | **RETIRE** | same; superseded by `cloud-run-backend/` | 3 / CC |
| research-metadata-api | no (closed 09-28) | 0 | none | ~0 | **RETIRE** | same; its database has no consumer either (4D) | 3 / CC |
| glmp-service | no (closed 2026-10-04, BULLETIN 018) | 10 in the 30 days, all before the closure | none: only `glmp/glmp-cloud-service/test_service.sh:4` and its own docs; the GLMP lane confirmed no caller, Jetson cron included (glmp#23, `glmp-cloud-service/RETIRED.md`) | ~0 | **RETIRE** | the GLMP lane has marked it retired; nothing calls it; the closure is verified | 3 / CC |
| copernicus-frontend | yes (intended) | 391 | `huggingface-space/index.html:246,653,791`; `huggingface-space/knowledge-engine-status.html:184` | ~0 | **KEEP** | the Knowledge Engine UI; 53 revisions retained, prune the old ones | 1 / CC |
| copernicus-podcast-api | yes (intended) | 18,269 | `public/index.html:188,203`; `api/episodes/index.js:9`; `app/episodes/[episodeId]/page.tsx:21`; `huggingface-space/index.html:932` | ~25 (one always-on 2 vCPU / 2 GiB instance) | **KEEP** | the live API; 266 revisions retained, prune the old ones | 1 / CC |
| scienceviddb-web | yes | 39 (34 successful: crawlers plus a few people) | linked as a live demo: `huggingface-space/README.md:325`, `nsf-proposal/NSF_Biographical_Sketch_Welz.md:85` | ~0 | **KEEP** | documented public demo; its database is live | none |

### 4B. Cloud Functions (gen2; each runs as one of the 15 Cloud Run services)

| Function | Public? | Req | Caller in code | ~$/mo | Rec | Reason | Batch / who |
|---|---|---|---|---|---|---|---|
| copernicus-podcast-form | no (closed 09-28) | 0 | none found | ~0 | **RETIRE** | closed, silent, no caller | 3 / CC |
| generate-podcast | no (closed 09-28) | 7, all before closure | `glmp/podcast_form.html:189` and the tests listed in section 3 | ~0 | **RETIRE** | superseded by `/generate-podcast` in `cloud-run-backend`; first move or delete the glmp-root callers | 3 / CC, after the GLMP lane moves the callers |
| glmp_feedback | yes (a feedback form) | 5 (all 09-29, GET, referer a bucket page, crawler-like agent) | `glmp/glmp-v2/viewer/modules/config.js:7` | ~0 | **KEEP** | referenced by the GLMP viewer | none |
| glmp_view_suggestions | yes | 0 | `glmp/glmp-v2/view-suggestions.html:195` | ~0 | **KEEP** | referenced by a live page; the GLMP lane decides | none |
| glmp_simple_suggestion | yes | 0 | `glmp/glmp-v2/simple-suggestion.html:242` | ~0 | **KEEP** | same | none |
| glmp_process_suggestion | yes | 0 | `glmp/glmp-v2/process-suggestion-chat.html:246`; the GLMP lane already archived it as unused, `glmp/docs/archive/unused_cloud_functions/glmp_process_suggestion/README.md:6` | ~0 | **RETIRE** | replaced by `glmp_simple_suggestion`; needs the GLMP lane's OK and the page edited first | 3 / CC |

The four `glmp_*` functions are GLMP-lane assets that happen to live in this project; rule 10
applies, so the last three decisions are the GLMP lane's, and Gary's.

### 4C. Cloud Run jobs (not in the system map)

| Job | Public? | Runs, 30 days | Caller in code | ~$/mo | Rec | Reason |
|---|---|---|---|---|---|---|
| add-research-math-channels | no (jobs are not HTTP-invoked) | 0 (last 2025-12-16) | `sciencevideodb/packages/ingestion` | ~0 | **KEEP** | free while idle; the sciencevideodb lane's |
| ingest-all-channels | no | 0 (last 2026-01-06; one failed run on 2025-12-16) | same | ~0 | **KEEP** | same |

Both use `scienceviddb-ingestion:latest`, so that image is *in use*, not stale.

### 4D. Cloud SQL (all four: PostgreSQL 15, db-f1-micro, 10 GB SSD, single zone, always on, public IPv4 address, no deletion protection)

| Instance | Data | Connections (daily max, 30 days) | Attached to | Caller in code | ~$/mo | Rec | Reason | Batch / who |
|---|---|---|---|---|---|---|---|---|
| copernicus-db | 77 MB used (near empty) | 1 to 2 on `copernicus` (the platform poll, see below) | copernicus-api (0 requests) | none in code; docs only (`sciencevideodb/docs/INFRASTRUCTURE_INTEGRATION.md:38`) | ~10 to 12 | **RETIRE** (stop first) | no consumer, no backups, no deletion protection | 1 export; 2 stop; 5 delete / CC |
| research-metadata-db | 99 MB | 2, constant | research-metadata-api (0 requests) | none; `glmp/docs/GLMP_MASTER_TODO.md:1643` says no secret or proxy exists anywhere | ~10 to 12 | **LOCK DOWN, then RETIRE** | one authorized network entry (a single /32); no consumer | 1 trim entry; 2 stop; 5 delete / CC |
| glmp-db | 76 MB (an empty instance's baseline) | 1, constant (the platform poll, see below) | nothing | cited as holding the dataset in an archived draft, `glmp/docs/archive/old_files/misc_files/glmp_paper_101625_FINAL_CLEAN.txt:339` | ~10 to 12 | **RETIRE** (export, stop, delete) | its `glmp` database holds 0 rows and nothing connects to it; the GLMP data is in Firestore. Daily backups and deletion protection stay on until Batch 5 | 1.7b export; 2 stop; 5 delete / CC |
| scienceviddb-db | 306 MB | 1 to 10 | scienceviddb-web | `sciencevideodb/docs/SCITV_ROADMAP.md:163`, `sciencevideodb/packages/db/` | ~10 to 12 | **KEEP, harden** | the only live database, and it has **no automated backups and no deletion protection** | 1 enable both / CC |

Network settings, read from the instance configuration (no database connection): **no instance
allows 0.0.0.0/0 or any broad range.** Three have no authorized network at all; `research-metadata-db`
has the single /32 noted above. All four have a public IPv4 address and accept unencrypted
connections; tightening that is listed under "not proposed" in section 7.

**The constant sessions are a platform poll, not an application.** Every instance shows the same
pattern: about 5,760 new connections a day to *each* database, one every 15 seconds, identical
for the application database and for `postgres`. Thirty-day totals, application database and
`postgres`: `glmp-db` 172,696 and 172,696; `copernicus-db` 172,692 and 172,691;
`research-metadata-db` 172,692 and 172,691; `scienceviddb-db` 172,946 and 172,695. Beyond that
baseline the application databases saw 0 to 1 real connections in 30 days on the three instances
to retire, and about 250 on `scienceviddb-db`, the live one. I did not connect to any database
(that needs credentials from Secret Manager, out of scope here). Stopping an instance stays the
test for any client the metrics cannot see, which is why Batch 2 stops before Batch 5 deletes.

**`glmp-db`: what is in it, seen without connecting (Gary's belief: the data now lives in Firestore).**

| What I looked at | Result |
|---|---|
| Databases and users (instance metadata) | databases `postgres` and `glmp`; users: the built-in `postgres` and one IAM login (Gary's own). No application user |
| Wiring | no Secret Manager entry for it (the only database secrets are `copernicus-db-url`, `scienceviddb-database-url` and `cloud-sql-password`); no Cloud Run service or job attaches it; the `glmp_*` functions and `glmp-service` have no database setting (their environment variables are `BUCKET_NAME`, `PROJECT_ID`, `LOG_EXECUTION_ID`) |
| Rows (Cloud Monitoring `tuple_size`) | `glmp` database: **0 live and 0 dead tuples**. The metric reads real data elsewhere: `scienceviddb` 377,041, `research_metadata` 14,317, `copernicus` 4 |
| Size | 76.2 MB used on the instance, the baseline of an empty instance (`copernicus-db`, with 7 near-empty tables, uses 76.8 MB) |
| Connections | 172,696 new in 30 days, equal to the `postgres` database: the platform poll and nothing else |
| Backups | 7 daily automated backups, 2026-09-29 to 2026-10-05, all successful; their sizes are not visible without a restore |
| Firestore today | `glmp_processes` 217 documents, `glmp_circuits` 19 |
| History | instance created 2025-10-14, two days before the paper draft (2025-10-16) that mentions it; the glmp repo's `database_schema_with_logic.sql` (6 tables, last touched 2025-09-12) predates the instance and only an archived inventory refers to it |
| **Not visible** | table names and row contents (they need a connection); statement counts and application names (Query Insights is off, so those metrics returned no series, which means "not collected", not zero) |

**Conclusion: nothing suggests data exists only in `glmp-db`.** It has zero rows, no application
user or secret, no connection beyond the platform poll, and the GLMP data is in Firestore. The
zero-row reading is a statistics gauge, so step 1.7b exports the database first. If the export
turns out to hold rows, they are compared with `glmp_processes` and `glmp_circuits` before
anything is stopped. Daily backups keep running until the instance is stopped (a stopped instance
takes no new backup; the seven existing ones stay until the instance is deleted), and the
deletion protection set in 1.5 stays until Batch 5.

### 4E. Buckets

| Bucket | Public? | API calls (30 d) | Size / objects | ~$/mo | Rec | Reason | Batch / who |
|---|---|---|---|---|---|---|---|
| regal-scholar-453620-r7-podcast-storage | **yes (intended)** | 78,822 | 1.95 GB; 4,080 objects counting old versions (2,762 live) | ~0.05 plus egress | **KEEP** | the reader-facing surface; versioning is on | none |
| regal-scholar-453620-r7-internal | no | 647 | 42 MB; 117 | ~0 | **KEEP** | the private archive | none |
| …-podcast-storage-backup-20250707 | no | 1 | 595 MB; 129 | ~0.02 | **KEEP** | **the only home of 93 files**: they are absent from the main bucket, counting its old versions too; the other 36 are identical in main | none |
| …-podcast-storage-backup-20250708 | no | 1 | 14 MB; 1 | ~0 | **RETIRE** | redundant: its one file is identical to the copy in the 20250707 bucket | 4 / CC |
| …-podcast-storage-backup-20250708-0713 | no | 1 | 536 MB; 106 | ~0.01 | **RETIRE** | redundant: 28 files are identical in main, the other 78 identical in the 20250707 bucket (checksums compared, no name has two different contents) | 4 / CC |
| regal-scholar-453620-r7_cloudbuild | no | 45 | 24.7 GB; 247 | ~0.6 | **RETIRE** old objects | Cloud Build source archives; 207 of 247 (22.5 GB) were created before July 2026 | 4 / CC |
| run-sources-regal-scholar-453620-r7-us-central1 | no | 1 | 24.2 GB; 180 | ~0.5 | **RETIRE** old objects | source-deploy archives; all 180 were created before July 2026 | 4 / CC |
| gcf-v2-sources-204731194849-us-central1 | no | 16 | 70 KB; 10 | ~0 | **KEEP** | the only copy of each function's source zip; needed to redeploy a retired function | none |
| copernicus-filestore | no (closed 09-28) | 12 | empty | 0 | **KEEP** | empty; deleting it would free the name for anyone to claim | none |
| copernicus-assets | no | 10 | empty | 0 | **KEEP** | empty; same reason | none |
| copernicus-media-audio | no | 2 | empty | 0 | **KEEP** | empty; same reason | none |
| copernicus-media-video | no | 2 | empty | 0 | **KEEP** | empty; same reason | none |
| copernicus-audio-regal-scholar-453620-r7 | no | 1 | empty | 0 | **KEEP** | empty; same reason | none |
| copernicus-temp-regal-scholar-453620-r7 | no | 1 | empty | 0 | **KEEP** | empty; same reason | none |
| gcf-v2-uploads-204731194849.us-central1.cloudfunctions.appspot.com | no | 1 | empty | 0 | **KEEP** | managed by Cloud Functions | none |

"Empty" was checked by listing each bucket with errors visible, and the monitoring series are
absent for exactly those seven; a non-empty bucket listed normally in the same run.
Public status: only `podcast-storage` carries `allUsers`. The three backup buckets use per-object
ACLs, so I also requested one object from each anonymously; all three returned 403.
The backup comparison counted the main bucket's old versions as well as its live files.

### 4F. Artifact Registry (container images; not in the request, but the largest storage bill)

| Repo | Size | Notes | ~$/mo | Rec | Batch / who |
|---|---|---|---|---|---|
| gcr.io | about 95 GB, 235 images | 129 are podcast-api builds, 42 frontend, 21 are `copernicus` prototypes from 2025-04 that **no revision uses**, plus 1 unused research-backend build | ~9.5 | **RETIRE** the 22 unreferenced images now, the rest as old revisions go | 4 / CC |
| cloud-run-source-deploy | about 71 GB | holds the source-deploy images of services Batch 3 retires | ~7 | **RETIRE** after Batch 3's hold | 4 / CC |
| copernicus-ai, gcf-artifacts | under 1 MB | | ~0 | KEEP | none |

Nearly every image is held by an existing revision (383 digests referenced), which is why revision
pruning (Batch 1) must come first. I could not read per-image sizes, so I do not promise how much of
the 166 GB frees up.

### 4G. Vercel (Gary, by dashboard; no CLI or token here)

Only 10 of the 32 project names are recoverable from governance. Evidence below is from
the request logs of `copernicus-podcast-api` (page loads from a Vercel deployment call it, and the
`referer` names the deployment).

| Project | Public? | Evidence | Rec | Action |
|---|---|---|---|---|
| copernicus-web-public | yes: www.copernicusai.fyi, www.copernicusai.app | 714 API calls with those referers | **KEEP** | none |
| copernicus-rss-web | unknown | git disconnected 09-29 (entry 007); the feed is served from the bucket | **RETIRE** after checking no domain is attached | Gary, batch 5 |
| copernicusai-site | yes: copernicusai.org | 2026-10-01 check returned 404 | **KEEP** until Gary decides on copernicusai.org | none |
| copernicus-web, copernicus-web-2025, copernicus-web-8pvc, copernicusai-web-032725, copernicusai-podcast-2025, copernicus-podcast-web (all git-disconnected since 09-28) | yes (deployment URLs) | old deployments are still being loaded: about 45 API calls in 30 days arrived from `copernicusai-podcast-2025` deployment URLs and from two other old `copernicus*` deployment hostnames I could not map to a project name | **LOCK DOWN**, watch 7 days, then **RETIRE** | Gary: Settings → Deployment Protection, batch 2; delete, batch 5 |
| the other 22 | unknown | names not recoverable from this seat | unknown | Gary: export the project list from both teams so the next version can cover them |

### 4H. Pending items

| Item | State (verified 2026-10-04) | Evidence | Rec | Reason | Batch / who |
|---|---|---|---|---|---|
| Service-account key `8ee8790b0a4cfecbe671db4c7c7f77aac48d26d3` (entry 005) | `disabled: True`, user-managed, created 2025-04-04 | no usage history obtainable (section 2); its ID appears at `governance/BULLETIN.md:276` and nowhere else in governance, the root docs or the glmp docs | **RETIRE** (delete) | entry 005 already says delete after 2026-10-05 if nothing broke; no break reported; Gary decided 2026-10-05 to delete it with Batch 3 | 3 / CC, not before 2026-10-13 |
| Revision `copernicus-podcast-api-00262-kfx` (entry 009) | 0% traffic; created 2026-08-26 | 12,097 requests in the window, last 2026-09-30 04:51 UTC, i.e. until the 09-30 cutover; image `…@sha256:6aaad70fb52f05d188d4ef19db94fa72b4f865aa218d9fb5421e9e5568b66016` | **RETIRE** | three newer rollback points exist; rolling back to -00262-kfx would bring back the five generator bugs entry 009 fixed | 4, not before 2026-10-11 / CC |
| Revision `copernicus-podcast-api-00268-muc` | 0% traffic; created 2026-10-02 | 4,603 requests, last 2026-10-04 15:53 UTC; image `…@sha256:b13a822cb20221c6d5c59737b82048022f9508cef3f04d8ea0aa2b15465ba795` | **KEEP** until at least 2026-10-11 | today's backend rollback (entry 017) | none |
| Revision `copernicus-frontend-00052-zif` | 0% traffic; created 2026-10-01 | 38 requests, last 2026-10-04 16:22 UTC; image `…@sha256:251a05d3741cc8b1a726e4bd5f701ef3f67842d76e1d3e75a21defc2c182ed18` | **KEEP** until at least 2026-10-11 | today's frontend rollback (entry 017) | none |

The three stale revision tags on `copernicus-podcast-api` (`fixes0930`, `test` and `lockdown`) were removed on 2026-10-04 per BULLETIN entry 018; rollback goes by revision name, not by tag.

### 4I. Data stores: KEEP only, no action commands

Nothing in Batches 1 to 5 reads, writes, deletes or changes the permissions of anything below.
The one way any of it is touched is add-only: backup copies are written *into* the internal bucket.
Deleting anything here is not proposed, now or later; a change to any of it would be its own
proposal under rule 16 (generated content) or rule 18 (public objects).

**Firestore**, database `copernicusai`, the only database on the project: **KEEP only.**
17 collections, document counts read 2026-10-04:

| Collection | Docs | What it holds |
|---|---|---|
| research_papers | 119,400 | the shared paper corpus |
| science_videos | 1,123 | sciencevideodb's video index |
| atap_graphs | 237 | ATAP proof-graph corpus |
| glmp_processes | 217 | GLMP process charts (decoder keys moved out, BULLETIN 016) |
| chemistry_processes | 124 | Programming Framework demonstration corpus |
| episodes | 104 | published podcast episode catalog |
| podcast_jobs | 77 | podcast generation jobs |
| computer_science_processes | 72 | Programming Framework demonstration corpus |
| biology_processes | 56 | Programming Framework demonstration corpus |
| physics_processes | 28 | Programming Framework demonstration corpus |
| glmp_circuits | 19 | canonical DNA-decoder output (BULLETIN 016) |
| subscribers | 18 | subscriber accounts; **personal data, not inspected beyond the count** |
| podcasts | 9 | purpose not disambiguated from `episodes` (system map) |
| scheduler_status | 8 | heartbeat records for the nightly chain |
| rate_limits | 5 | new since the 2026-10-01 system map; named for the rate limits added in BULLETIN 015, purpose inferred |
| users | 2 | purpose not inspected |
| system_metrics | 1 | purpose not inspected |

**Canonical process JSON**, in `regal-scholar-453620-r7-podcast-storage` (the public bucket), **KEEP only.**
`glmp-v2/processes` (default `GLMP_BUCKET_PATH`, `cloud-run-backend/mcp_server/config.py:41`; read by
`cloud-run-backend/scripts/sync_glmp_processes.py:152`) and `mathematics-processes-database/processes/`
(`cloud-run-backend/scripts/sync_math_processes.py:36-37`) are what the manual sync scripts copy into
`glmp_processes` and `atap_graphs`. By object count the prefixes are `mathematics-processes-database`
(679), `glmp-v2` (416), `chemistry-processes-database` (347), `biology-processes-database` (127),
`glmp-processes-database` (126), `computer-science-processes-database` (112),
`physics-processes-database` (75), `glmp-archive` (61), `computer_science-processes-database` (22,
an alternate spelling), `mathematics-dependency-graphs` (3) and `glmp` (4). The link from the
discipline prefixes to their Firestore collections was not traced this pass.

**Public database tables and status pages**, same bucket, **KEEP only**, and gated by rule 18:
`papers-database-table.html`, `glmp-database-table.html`, `podcast-database-table.html`,
`videos-database-table.html`, `podcast-database.html`, `test-database.html`, `GLMP_STATUS.html`,
`knowledge-engine-status.html`, `knowledge-engine-status.json`, and the RSS feed under `feeds/`.

**Internal bucket**, `regal-scholar-453620-r7-internal`, **KEEP only**: the private archive and
the destination for every backup in section 5. No command here changes its permissions, lifecycle
or contents beyond adding copies.

---

## 5. Action sheets

Conventions. `P=regal-scholar-453620-r7`, region `us-central1`,
`I=gs://regal-scholar-453620-r7-internal/phase2-2026-10`. Every backup goes to `$I`, a private bucket.
Config exports (`--format=export`) can contain plaintext environment values: copy them to `$I` and
never print them (rule 3). Batch 1, steps 1.1 to 1.7, was run on 2026-10-05 with Gary's approval; no other command here has been run.

### Batch 1: back up, harden, trim, prune (all reversible)

| # | Action | Backup first | Reversal | Who |
|---|---|---|---|---|
| 1.1 | Save the config of each service to retire: for `S` in `copernicus-api copernicus-backend copernicus-research-backend copernicus-podcast-generator research-metadata-api`: `gcloud run services describe $S --region us-central1 --project $P --format=export > $S.yaml && gcloud storage cp $S.yaml $I/$S.yaml`. **`glmp-service` is already saved** (2026-10-04: `$I/glmp-service.yaml` and `$I/glmp-service-iam-before.json`, size and MD5 verified), so skip it | this is the backup | delete the copies | CC |
| 1.2 | Save each function to retire (`NAME`, `ENTRY`): copernicus-podcast-form (`main`), generate-podcast (`generate_podcast`), glmp_process_suggestion (`glmp_process_suggestion`): `gcloud functions describe NAME --gen2 --region us-central1 --project $P --format=yaml > NAME.yaml`, then `gcloud storage cp NAME.yaml $I/` and `gcloud storage cp gs://gcf-v2-sources-204731194849-us-central1/NAME/function-source.zip $I/NAME-function-source.zip` | this is the backup | delete the copies | CC |
| 1.3 | Record the digest list of every image to be removed in Batch 4 (`gcloud artifacts docker images list us-docker.pkg.dev/$P/gcr.io --include-tags --format=csv > images.csv`, then copy to `$I/`) | this is the backup | none needed | CC |
| 1.4 | **scienceviddb-db**: `gcloud sql instances patch scienceviddb-db --project $P --backup-start-time=04:00 --deletion-protection` | none (adds protection) | `gcloud sql instances patch scienceviddb-db --project $P --no-backup --no-deletion-protection` | CC |
| 1.5 | **glmp-db**: `gcloud sql instances patch glmp-db --project $P --deletion-protection` | none | `gcloud sql instances patch glmp-db --project $P --no-deletion-protection` | CC |
| 1.6 | **research-metadata-db**: remove its one authorized network entry: `gcloud sql instances patch research-metadata-db --project $P --clear-authorized-networks` | the entry's value is recorded in the private note in the internal bucket | `gcloud sql instances patch research-metadata-db --project $P --authorized-networks=<value from that note>` | CC |
| 1.7 | **Export the two databases to retire, through a scratch bucket so the internal bucket's permissions never change.** `T=gs://regal-scholar-453620-r7-sql-export-tmp`; `gcloud storage buckets create $T --project $P --location=us-central1 --uniform-bucket-level-access --public-access-prevention`; for each `INST`/`DB` (`copernicus-db`/`copernicus`, `research-metadata-db`/`research_metadata`): `SA=$(gcloud sql instances describe INST --project $P --format='value(serviceAccountEmailAddress)')`; `gcloud storage buckets add-iam-policy-binding $T --member=serviceAccount:$SA --role=roles/storage.objectAdmin`; `gcloud sql export sql INST $T/INST-DB.sql.gz --database=DB --project $P`; `gcloud storage cp $T/INST-DB.sql.gz $I/` (an add-only copy); compare the two checksums; then `gcloud storage rm -r $T`. **Creating and deleting a scratch bucket and one temporary grant on it needs Gary's explicit OK.** | the export is the backup | delete the export objects from `$I`; the scratch bucket and its grant are gone with `rm -r` | CC |
| 1.7b | **Export `glmp-db`/`glmp` the same way as 1.7** (added 2026-10-05 at Gary's request; it needs Gary's go-ahead because 1.7 was approved for two databases). Create the scratch bucket `T=gs://regal-scholar-453620-r7-sql-export-tmp` as in 1.7; `SA=$(gcloud sql instances describe glmp-db --project $P --format='value(serviceAccountEmailAddress)')`; grant it `roles/storage.objectAdmin` on `$T`; `gcloud sql export sql glmp-db $T/glmp-db-glmp.sql.gz --database=glmp --project $P`; add-only copy to `$I/`; compare checksums; `gcloud storage rm -r $T`. Then count tables and `COPY` blocks in memory (no content printed) and, if any rows exist, compare them with Firestore `glmp_processes` and `glmp_circuits` before Batch 2 | the export is the backup | delete the export object from `$I`; the scratch bucket and its grant are gone with `rm -r` | CC |
| 1.8 | Prune old Cloud Run revisions on `copernicus-podcast-api` (266 retained) and `copernicus-frontend` (53 retained): list revisions older than the rollback chain and delete them oldest first, **keeping the newest 10 of each, and every revision named in section 4H.** `gcloud run revisions delete REVISION --region us-central1 --project $P --quiet`. Cloud Run refuses to delete a revision that still serves traffic, and any such refusal is listed, not forced. | digest list from 1.3 | redeploy an image from the saved digest list: `gcloud run deploy copernicus-podcast-api --image gcr.io/$P/copernicus-podcast-api@sha256:DIGEST --no-traffic --region us-central1 --project $P` (this creates a new revision under a new name; follow `cloud-run-backend/DEPLOY.md`) | CC |

### Batch 2: stop, protect (reversible with one command or toggle)

| # | Action | Backup first | Reversal | Who |
|---|---|---|---|---|
| 2.1 | Stop `copernicus-db`, `research-metadata-db` and `glmp-db` (the last only after 1.7b): `gcloud sql instances patch INST --project $P --activation-policy=NEVER`. Watch 7 days for any error that names them. Storage is still billed while stopped, and a stopped instance takes no new automated backup (the existing ones stay). | 1.7 and 1.7b | `gcloud sql instances patch INST --project $P --activation-policy=ALWAYS` | CC |
| 2.2 | For the six git-disconnected Vercel projects: Settings → Deployment Protection → Vercel Authentication on. | note each project's current setting | switch it back off | Gary |

### Batch 3: delete the silent services and functions (after 7 quiet days on Batch 2)

| # | Action | Backup first | Reversal | Who |
|---|---|---|---|---|
| 3.1 | `gcloud run services delete S --region us-central1 --project $P` for the five services in 1.1 **and for `glmp-service`** (image `…/cloud-run-source-deploy/glmp-service@sha256:2f604b7fc71f813e8b4b15ac8abe69eb5f04f338fa33dc0db300af272316b441`, kept until Batch 4) | 1.1 and the image digests (kept until Batch 4) | `gcloud run services replace $S.yaml --region us-central1 --project $P` after fetching `$I/$S.yaml`; the service URL returns. The service stays closed until an IAM binding is added deliberately. | CC |
| 3.2 | `gcloud functions delete NAME --gen2 --region us-central1 --project $P` for `copernicus-podcast-form` only. **`generate-podcast` and `glmp_process_suggestion` are held out of this batch** until the GLMP lane has archived the `generate-podcast` callers and OKs `glmp_process_suggestion` | 1.2 (all three are saved anyway) | `gcloud functions deploy NAME --gen2 --region us-central1 --project $P --runtime python311 --entry-point ENTRY --trigger-http --no-allow-unauthenticated --source=./unzipped-NAME` (unzip the saved zip; restore environment variables from `NAME.yaml`) | CC |
| 3.3 | `gcloud iam service-accounts keys delete 8ee8790b0a4cfecbe671db4c7c7f77aac48d26d3 --iam-account=copernicus-service@regal-scholar-453620-r7.iam.gserviceaccount.com` | none possible (no key material is held); the key's ID and creation date are recorded in 4H | **none.** A key cannot be restored after deletion; issue a new one with `gcloud iam service-accounts keys create` and update whatever uses it | CC, not before 2026-10-13, together with 3.1 |

### Batch 4: storage and images (not before 2026-10-11)

| # | Action | Backup first | Reversal | Who |
|---|---|---|---|---|
| 4.1 | Delete revision -00262-kfx: `gcloud run revisions delete copernicus-podcast-api-00262-kfx --region us-central1 --project $P` | digest `sha256:6aaad70fb52f05d188d4ef19db94fa72b4f865aa218d9fb5421e9e5568b66016` recorded here and in 1.3 | `gcloud run deploy copernicus-podcast-api --image gcr.io/$P/copernicus-podcast-api@sha256:6aaad70fb52f05d188d4ef19db94fa72b4f865aa218d9fb5421e9e5568b66016 --no-traffic --region us-central1 --project $P` (new revision name) | CC |
| 4.2 | Delete build archives older than 95 days (at 2026-10-11 that is anything created before about 2026-07-08; 207 of the 247 cloudbuild objects and all 180 run-sources objects today) in `regal-scholar-453620-r7_cloudbuild` and `run-sources-regal-scholar-453620-r7-us-central1`, by lifecycle rule: write `{"rule":[{"action":{"type":"Delete"},"condition":{"age":95}}]}` to `lc.json`, then `gcloud storage buckets update gs://BUCKET --lifecycle-file=lc.json` for each | `gcloud storage ls -l --json -r gs://BUCKET/** > manifest-BUCKET.json`, copied to `$I/` (names, sizes, checksums) | `gcloud storage buckets update gs://BUCKET --clear-lifecycle` stops further deletes; deleted objects can be restored for **7 days** from soft delete (`gcloud storage restore gs://BUCKET/OBJECT#GENERATION`), then they are gone | CC |
| 4.3 | Delete the 22 unreferenced images, then images freed by Batch 1 and Batch 3: `gcloud artifacts docker images delete us-docker.pkg.dev/$P/gcr.io/IMAGE@sha256:DIGEST --delete-tags` | 1.3 (digests, tags, dates) | rebuild from the git commit with `cloud-run-backend/DEPLOY.md` (podcast-api); for the 2025-04 `copernicus` prototypes there is **no reversal**, which is why they go last | CC |

| 4.4 | Delete the two redundant backup buckets: `gcloud storage rm -r gs://regal-scholar-453620-r7-podcast-storage-backup-20250708 gs://regal-scholar-453620-r7-podcast-storage-backup-20250708-0713` | a name, size and checksum manifest of both buckets, plus the comparison result (every object identical in main or in the 20250707 bucket), copied to `$I/`; re-run the comparison the same day, since main changes | recreate the bucket (`gcloud storage buckets create gs://BUCKET --location=US`) and copy the listed objects back from `gs://regal-scholar-453620-r7-podcast-storage-backup-20250707` or main according to the manifest | CC |

### Batch 5: irreversible (after at least 30 days stopped)

| # | Action | Backup first | Reversal | Who |
|---|---|---|---|---|
| 5.1 | `gcloud sql instances delete INST --project $P` for `copernicus-db`, `research-metadata-db` and `glmp-db` (remove deletion protection first with `--no-deletion-protection`; `glmp-db` has it from 1.5) | the 1.7 and 1.7b exports, size and checksum re-verified the same day. Note that an instance's own backups are deleted with it | `gcloud sql instances create INST --database-version=POSTGRES_15 --tier=db-f1-micro --region=us-central1 --storage-type=SSD --storage-size=10 --project $P`, then `gcloud sql databases create DB --instance=INST`, then `gcloud sql import sql INST $I/INST-DB.sql.gz --database=DB`. Roles and passwords are not in the export and would have to be recreated. | CC |
| 5.2 | Delete the Vercel projects chosen in 4G (Dashboard → project → Settings → General → Delete) | export each project's environment variables and domain list from its settings first | re-import the repo as a new project and re-add domains and variables; deployment history is not recoverable | Gary |

### C1. Separate gated change: `copernicus-podcast-api` minimum instances 1 to 0 (proposal; the live service is not changed)

**What and why.** Gary wants the always-on instance dropped, to save about $25 a month. The
service bills by request (CPU throttled, startup CPU boost already on), so only a *minimum*
instance bills while idle. With a minimum of 0, an idle instance shuts down after about 15
minutes and stops billing.

**What the data says** (read-only, 2026-10-05):

| Fact | Value | Source |
|---|---|---|
| Container startup, with startup CPU boost already on | p50 29.8 s, p95 72.0 s, p99 74.3 s | Cloud Monitoring `container/startup_latencies`, 30 days, all revisions |
| Idle gaps over 15 minutes (each would end in a cold start) | 390 in 30 days: **13 a day**, in every hour of the day; median gap 40 min, longest 5.9 h | the 18,275 request-log entries, 2026-09-04 to 2026-10-04 |
| Warm server-side latency | `/health` about 0.1 s; episode request p50 0.11 s, p95 0.38 s; episode list p50 0.75 s | request logs |
| Warm time to first byte from this laptop, live service, 3 trials | `/health` 0.19 to 0.27 s; `/api/episodes/<id>` 0.18 to 0.26 s | measured 2026-10-05 |
| Requests that already took over 20 s | 7 in 30 days (`/api/content/browse`, `/api/vector-search/semantic`, `/api/rag/answer`) | request logs |
| Who calls it | mostly pages in the public bucket (about 14,900 of 18,300 calls), the Vercel site and the HF Space | request-log referers |

So with a minimum of 0, about 13 requests a day would wait roughly 30 to 70 seconds, if the
startup metric is representative of a cold start on a request. The callers are pages running in
visitors' browsers; whether their code gives up before 30 seconds was not checked.

**Savings.** Billable instance time for this service was about 1.77 million instance-seconds in
the last 7 days (about 2.9 instances running around the clock). Most of that came from tagged
0%-traffic revisions that carry a minimum instance: a tag keeps such a revision warm and billed.
The tag removal of 2026-10-04 released three; hourly instance counts now show only `-00268-muc`
(tag `step2`) and the live `-00270-puh`. This change releases the live revision's warm instance:
about one instance, roughly $22 to $25 a month at the unverified price in section 6, less request
time and about 13 cold starts a day. Removing `step2` after the hold is worth about the same
again.

**Procedure,** following `cloud-run-backend/DEPLOY.md`, with one stated exception: step 4's
"only the image may differ" becomes "the image is identical and only the minimum-instances
setting differs".

1. Create a tagged, no-traffic revision with the same image and only that setting changed:
   `gcloud run services update copernicus-podcast-api --region us-central1 --project $P --min-instances=0 --no-traffic --tag=mininst0`.
   `services update` patches only what it is given, so the image digest and every other setting
   carry over (the three flags exist on this command). **This creates a new revision**, numbered
   after `-00270-puh`. Nothing else changes: traffic stays 100% on `-00270-puh`, and `-00268-muc`
   keeps its tag at 0%.
2. Diff it against `-00270-puh` (DEPLOY.md step 4). Only the name, tag, timestamps and
   `autoscaling.knative.dev/minScale` (1 to 0) may differ.
3. Smoke-test the tag URL (DEPLOY.md step 5): `/health`, and the sorted list of episode IDs
   identical to the live service.
4. Run the cold-start measurement below.
5. Gary decides from the numbers. If yes, move traffic:
   `gcloud run services update-traffic copernicus-podcast-api --region us-central1 --project $P --to-revisions=<new revision>=100`.
   Then DEPLOY.md step 7, plus instance count falling to 0 after 20 idle minutes and request
   latency over the following days.
6. Remove the tag when its hold ends (DEPLOY.md step 9):
   `--remove-tags=mininst0`. Reversal: `--update-tags=mininst0=<new revision>`.

**Interaction with the `-00268-muc` hold (until 2026-10-11).** Creating the revision deletes
nothing and moves no traffic, so `-00268-muc` stays a valid rollback. After a cutover the
rollback chain is: new revision, then `-00270-puh` (it still carries the tag `gap1-engine`, which
keeps it warm, so rolling back to it is instant), then `-00268-muc`. Recommendation: do steps 1
to 4 (no traffic) once Gary approves, and do step 5 **not before 2026-10-11**, so the hold covers
the same release unchanged and only one change is in flight at a time. The `step2` tag keeps one
instance warm on `-00268-muc` until it is removed; rollback by revision name does not need the tag,
but a rollback to a revision with no warm instance cold-starts for about 30 to 70 seconds. That is
a decision for Gary (section 8).

**Reversal.** Fast: `gcloud run services update-traffic copernicus-podcast-api --region us-central1 --project $P --to-revisions=copernicus-podcast-api-00270-puh=100`
(instant while that revision keeps its tag; remove the tag only after the watch period).
Permanent: `gcloud run services update copernicus-podcast-api --region us-central1 --project $P --min-instances=1 --no-traffic --tag=restore`,
then route to it.

**Cold-start measurement plan,** on the tagged no-traffic revision. The live service is not touched.

- **Setup.** The revision from step 1. Its tag URL is public but serves the same code as the live
  service, so it exposes nothing the live service does not.
- **Idle.** Before each trial, confirm the revision has 0 instances (`container/instance_count`
  for that revision) and has received no request for at least 20 minutes.
- **Trials.** Six cold trials, alternating `/health` and an episode request (`GET /api/episodes/<id>`
  with one fixed real id from the live list): health, episode, health, episode, health, episode.
  That is 3 per endpoint, at least 20 minutes apart, about 2 hours 10 minutes in all.
- **Record** for each, from `curl -s -o /dev/null -m 120 -w`: `time_namelookup`, `time_connect`,
  `time_starttransfer` (time to first byte), `time_total` and `http_code`. Straight after each cold
  request, one warm request to the *other* endpoint as a within-trial control.
- **Server side** for the same window: `container/startup_latencies` and the request-log `latency`
  of those requests.
- **Baseline.** The warm live numbers above, re-taken (3 trials) at the end to catch drift.
- **Decision threshold, for Gary to set.** My suggestion: switch only if the cold time to first
  byte of the episode request is 10 seconds or less in all three trials. The data above predicts
  it will not be (startup alone is about 30 s with boost already on). If it is not, the choices
  are to keep a minimum of 1, to accept the cold starts, or to shorten application startup, which
  is a code change and its own proposal.
- **Cleanup.** Remove the tag (DEPLOY.md step 9) when the measurement is done.

---

## 6. Cost estimate and its limits

**Quantities (verified live):** four Cloud SQL db-f1-micro instances, 10 GB SSD each, running 24/7;
about 166 GB in Artifact Registry (95 GB + 71 GB); about 50 GB of build archives plus 2.5 GB of
everything else in Cloud Storage; one Cloud Run instance kept warm at 2 vCPU / 2 GiB; everything
else scales to zero.

**Unit prices used (remembered list prices, unverified; the pricing pages did not render):**

| Item | Assumed price | Gives |
|---|---|---|
| Cloud SQL db-f1-micro (PostgreSQL), per instance | about $8 to $10 a month, plus SSD about $0.17 per GB-month | about $10 to $12 each, $40 to $48 for four |
| Artifact Registry | about $0.10 per GB-month above a small free allowance | about $16 for 166 GB |
| Cloud Storage standard | about $0.020 (single region) and $0.026 (US multi-region) per GB-month | about $1.2 for the build archives; pennies for the rest |
| Cloud Run warm instance, idle rate | about $0.0000025 per vCPU-second and per GiB-second | about $25 for podcast-api, plus request time |

**Total touched: about $85 a month. Removable by this proposal: the three databases (about $30 to
$36), the build archives (about $1) and part of the images (anywhere from a few dollars to $16)**,
so about $35 to $50. The minimum-instance change in section 5 (C1) is separate and not counted here. Treat these as orders of magnitude. To replace them with real numbers, enable
the Billing export or open Billing → Reports for this project; the Billing API stayed disabled here.

**Warm instances are the largest running cost I can see, and tags drive it.** Billable instance-seconds for
`copernicus-podcast-api` were about 1.77 million in 7 days, mostly from tagged 0%-traffic revisions that
carry a minimum instance. Three were released by the tag removal of 2026-10-04; `-00268-muc` (tag `step2`) still holds one.
Treat any tag on a revision with a minimum instance as a running cost until it is removed (DEPLOY.md step 9).

---

## 7. Things worth knowing that are not clean-up

- **`scienceviddb-db` is the only live database and has no backup and no deletion protection.**
  Batch 1.4 fixes both for pennies.
- **The constant sessions on the databases are a platform poll**, one new connection every 15
  seconds per database on every instance, not an application (see 4D). Batch 2's stop-first order
  still guards against any client the metrics cannot see.
- **One backup bucket matters.** 93 files exist only in `…-backup-20250707`; the other two
  backups add nothing beyond it and main. It costs about two cents a month; keep it, or archive the
  93 files to the internal bucket under rule 16 and then retire it.
- **Cloud Run Jobs and Artifact Registry were missing from the system map**, and so were 266
  retained revisions of one service. The next map revision should add them.
- **Not proposed here:** tightening Cloud SQL to encrypted-only connections, a lifecycle rule for
  old object versions in `podcast-storage`, and enabling the Billing export. Each is its own change.

## 8. Decisions

Recorded 2026-10-05 from Gary's decisions on this PR.

1. **Batch 1: approved**, including the scratch bucket and temporary grant in 1.7.
2. **Batch 2: approved.** **Batch 3: approved** to follow after 7 quiet days on Batch 2 (about 2026-10-13 at the earliest). It includes deleting `glmp-service`, which the GLMP lane has marked retired (glmp#23).
3. **GLMP lane items.** The `generate-podcast` callers in the glmp root: the GLMP lane will **archive** them (not move them). `glmp_process_suggestion` awaits the GLMP lane's OK. **Both functions stay out of Batch 3 until then.** Still open: whether the `glmp-db` claim in the paper draft is live.
4. **Vercel: deferred** until Gary exports the project lists (both teams).
5. **Disabled key `8ee8790b…` (entry 005): delete together with Batch 3, not before 2026-10-13** (moved from Batch 5 to row 3.3).
6. The privately filed items: separate approvals, given outside this file.

### Proposed 2026-10-05, awaiting Gary

7. **`glmp-db` to the retire track** (4D, step 1.7b): export through the scratch bucket, stop in
   Batch 2 with a 7-day watch, delete in Batch 5; its daily backups and deletion protection stay
   until Batch 5. Evidence: zero rows, no application user or secret, no connection beyond the
   platform poll. Needs a go-ahead for 1.7b, which is new work beyond the approved 1.7.
8. **Minimum instances 1 to 0 on `copernicus-podcast-api`** (section 5, C1). The data predicts cold
   starts of about 30 s, up to 72 s, about 13 times a day. Recommendation: approve steps 1 to 4
   (a tagged revision with no traffic, then the measurement) and decide on the cutover from the
   numbers, not before 2026-10-11. Gary sets the threshold.
9. **The `step2` tag on `-00268-muc`** keeps one instance warm (about $25 a month at the assumed
   price) until it is removed. Remove it now, accepting that a rollback to `-00268-muc` would then
   cold-start, or keep it until the hold ends on 2026-10-11?

*Evidence kept in the session scratchpad only; no secret values were read or printed. The
commands above were proposals; execution is reported in the PR description, not in this file.*
