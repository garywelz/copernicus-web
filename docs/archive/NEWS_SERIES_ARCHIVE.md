# News Series — Archived (2026-09-29)

A record of the five-episode "News" format (Biology News, Chemistry News,
CompSci News, Math News, Phys News) — a one-off experiment from
March/July 2025, removed from public distribution on 2026-09-29 per Gary's
decision. Nothing was deleted. This note is where to look if the series is
restarted.

## Where everything lives

- **RSS feed**: items removed from `feeds/copernicus-mvp-rss-feed.xml` on
  2026-09-29. Pre-removal backup:
  `feeds/old feeds/copernicus-mvp-rss-feed.pre-news-removal-2026-09-29.xml`
  (bucket `regal-scholar-453620-r7-podcast-storage`).
- **Audio** (untouched, still in the bucket):
  `audio/news-bio-28032025.mp3`, `audio/news-chem-28032025.mp3`,
  `audio/news-compsci-28032025.mp3`, `audio/news-math-28032025.mp3`,
  `audio/news-phys-28032025.mp3`.
- **Transcripts**: none exist for any of the five episodes.
- **Firestore records** (database `copernicusai`, collection `episodes`):
  documents `news-bio-28032025`, `news-chem-28032025`,
  `news-compsci-28032025`, `news-math-28032025`, `news-phys-28032025`.
  Hidden from the website on 2026-09-29 by setting `submitted_to_rss: false`
  on each (was `true`; no other field was touched).
- **A sixth guid**, `ever-phys-250043`, carried an old "Phys News" copy in
  the RSS feed only. Its Firestore document under that ID has since been
  reused for an unrelated, current episode ("Quantum Computing chip
  advances") — there is no separate News record to restore for this one,
  and that document was deliberately left untouched.
- **Naming convention**: still recognized by
  `cloud-run-backend/services/canonical_service.py`
  (`news-{category}-{YYYYMMDD}-{serial}`), though no active generator
  currently produces this format.
- **Known prior issue**: `archive/one_off_scripts/2025-11/revert_news_podcasts.py`
  documents an earlier bug where News episode IDs were incorrectly
  migrated to the `ever-{category}-NNNNNN` format — read this before
  restarting the series, to avoid repeating the same ID collision.

## To restart the series

1. Reverse the hide: set `submitted_to_rss: true` on each of the 5
   Firestore documents above.
2. There is no live generator/prompt template for this format in the
   repo today — reconstruct the style ("premiere episode," rotating
   correspondents, "N major developments") from the existing
   `description_markdown` fields on those 5 documents, or from the
   backed-up RSS feed.
3. Decide whether to restore the old feed items as-is, or generate
   fresh ones — the old items' data (title, pubDate, enclosure) is
   preserved in the backup feed file above.

---
*Filed 2026-09-29.*
