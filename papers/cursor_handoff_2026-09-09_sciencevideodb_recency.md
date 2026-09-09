# Handoff — 9 September 2026 (ScienceVideoDB not receiving new rows — video corpus frozen)

**From:** Claude Code
**To:** Cursor
**Repos:** `copernicus-web` @ `fbfe1efa3` (main, origin)
**Regenerate from a fresh fetch before acting.**

Share this file as-is.

---

## The ask

Find out why **ScienceVideoDB** (the Postgres instance `regal-scholar-453620-r7:us-central1:scienceviddb-db`) has stopped receiving new YouTube video rows, and report back — no SSH access here (neither Claude Code nor Claude Chat has it), so this is Cursor-sized.

## What this is not

**Not a `sync_recent_videos.sh` / `sync_videos.py` problem — that side looks healthy.** The daily 21:30 America/New_York cron (`sync_recent_videos.sh`) starts the Cloud SQL Auth Proxy, runs `sync_videos.py --since-days 14`, and writes to Firestore's `science_videos` collection — the wrapper and script logic look correct. The trouble is upstream: **Postgres isn't handing it anything new to sync.**

Please don't re-diagnose or touch the sync script/cron wrapper — that part's presumed fine pending evidence otherwise.

## Evidence

Queried Firestore (`copernicusai` database, `science_videos` collection) directly today:

- Newest `created_at` across the whole collection: **2026-08-26T14:00:23** — nothing has landed in 14 days.
- Public `knowledge-engine-status.json` video count has been flat at **918** every time it's been checked from 2026-08-27 through today (2026-09-09), while the paper count kept climbing daily (118,066 → 118,686) over the same window.
- This isn't a new problem — it was already flagged in `cursor_handoff_2026-08-15_ke_ingest.md` (leftover item 5): *"ScienceVideoDB recency — cron works; the last-14-days query returned 0. If new YouTube rows are not landing in Postgres, the KE video corpus will freeze at 753."* The corpus did grow past that (753 → 918, presumably from a backlog catch-up), but it's now frozen again at 918.

## What would help

- Whatever process is supposed to insert new YouTube video rows into ScienceVideoDB Postgres — locate it (I couldn't find an active acquisition/scout script for it in this repo; there's only an archived, static `local_archive/huggingface-space/sciencevideodb/` with no scout code) and check: is it cron-scheduled anywhere (Jetson or elsewhere)? Still installed? Failing silently?
- If it's a YouTube Data API-based scout: check API key validity/quota — a quota exhaustion or revoked key would silently produce zero new rows without erroring the sync job downstream.
- Direct Postgres check, if convenient: `SELECT MAX(published_at), COUNT(*) FROM videos WHERE created_at > now() - interval '14 days';` (or equivalent — table/column names per `cloud-run-backend/scripts/sync_videos.py`'s `get_all_videos()`) to confirm nothing new is arriving at the source, not just that sync isn't finding it.

No need to fix blind — just report what you find (script located and its cron/log status, or confirmation no such acquisition job exists and one needs to be built).

## Key files

- `cloud-run-backend/scripts/sync_videos.py` — ScienceVideoDB → Firestore `science_videos`
- `huggingface-space/scripts/scheduler/scout/sync_recent_videos.sh` — cron wrapper (21:30 daily, `SINCE_DAYS=14`)
- `local_archive/huggingface-space/sciencevideodb/` — static leftovers only, no active scout code found here
