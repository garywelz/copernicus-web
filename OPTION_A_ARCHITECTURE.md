# Option A Architecture Implementation

## Overview

We've implemented **Option A**: Using `episodes` collection as the **single source of truth** for RSS/public podcast status.

### Collections

- **`podcast_jobs`**: Complete generation history
  - All podcasts ever generated (tests, duplicates, drafts, final versions)
  - **102 podcasts** currently
  - Never deleted (complete archive)
  - You can fully manage this collection

- **`episodes`**: Curated public catalog
  - Only promoted podcasts that can be published
  - **64 episodes** currently (legacy promoted ones)
  - **Single source of truth** for RSS status
  - Only appears here when explicitly promoted

## Workflow

### 1. Generate Podcast (AUTO-PROMOTE by Default)
- Creates entry in `podcast_jobs` (complete history)
- **Automatically creates entry in `episodes`** (YouTube-style immediate publication)
- User can immediately add to RSS without waiting for admin approval
- Better UX: No delay, users control their own content

### 2. Promote Podcast (Re-promotion)
- **Endpoint**: `POST /api/admin/podcasts/{podcast_id}/promote`
- Used to re-promote podcasts that were previously unpromoted
- Creates/updates entry in `episodes` collection
- Makes podcast available for RSS publication again

### 3. Add to RSS
- **Endpoint**: `POST /api/admin/podcasts/{podcast_id}/rss`
- **Requires**: Podcast must be in `episodes` collection first
- **Auto-promotes** if not already promoted
- Updates `episodes.submitted_to_rss = true` (**single source of truth**)
- Adds to RSS feed

### 4. Unpromote Podcast (Moderation)
- **Endpoint**: `POST /api/admin/podcasts/{podcast_id}/unpromote`
- Removes podcast from `episodes` collection (moderation/censorship)
- **Keeps** podcast in `podcast_jobs` (generation record preserved)
- If in RSS, removes from RSS first
- Can be re-promoted later if needed
- **Use case**: Remove unacceptable content after publication (like YouTube takedowns)
- **Note**: Users should be notified when their podcast is unpromoted (future enhancement)

## Endpoints

### Promote Podcast
```bash
POST /api/admin/podcasts/{podcast_id}/promote
Headers: X-Admin-API-Key: <your-key>

# Response:
{
  "podcast_id": "...",
  "canonical": "...",
  "promoted": true,
  "submitted_to_rss": false,
  "message": "Podcast successfully promoted to episodes collection. Can now be added to RSS."
}
```

### Unpromote Podcast (Remove from Episodes)
```bash
POST /api/admin/podcasts/{podcast_id}/unpromote
Headers: X-Admin-API-Key: <your-key>

# Removes podcast from episodes collection (but keeps in podcast_jobs)
# If in RSS, removes from RSS first
# Can be re-promoted later

# Response:
{
  "podcast_id": "...",
  "canonical": "...",
  "unpromoted": true,
  "was_in_rss": false,
  "message": "Podcast successfully unpromoted. Can be re-promoted later."
}
```

### Add to RSS (auto-promotes if needed)
```bash
POST /api/admin/podcasts/{podcast_id}/rss
Headers: X-Admin-API-Key: <your-key>

# If not promoted, automatically promotes first, then adds to RSS
```

### Remove from RSS
```bash
DELETE /api/admin/podcasts/{podcast_id}/rss
Headers: X-Admin-API-Key: <your-key>

# Updates episodes.submitted_to_rss = false (single source of truth)
```

## Changes Made

✅ **Auto-promote by default** during generation (YouTube-style immediate publication)
✅ **Added unpromote endpoint** for moderation/removal from public catalog
✅ **Added promotion endpoint** to re-promote previously unpromoted podcasts
✅ **Updated RSS endpoints** to use episodes as single source of truth
✅ **Better UX**: Users don't wait for approval, can publish immediately

## What You Can Do

1. **View all podcasts** in `podcast_jobs` collection (102 podcasts)
2. **Promote good podcasts** to `episodes` collection (makes them public-ready)
3. **Add promoted podcasts to RSS** (makes them live)
4. **Keep tests/duplicates** in `podcast_jobs` without promoting

## Next Steps (TODO)

- [ ] Update admin dashboard UI to show promotion status
- [ ] Add "Promote" button in admin dashboard
- [ ] Show which podcasts are promoted vs not promoted
- [ ] Filter by promotion status

## RSS Status Source of Truth

**BEFORE (Complex)**:
- Checked both `podcast_jobs.submitted_to_rss` AND `episodes.submitted_to_rss`
- Could get out of sync
- Cross-referencing needed

**NOW (Simple)**:
- **Only check `episodes.submitted_to_rss`**
- Single source of truth
- No sync issues

