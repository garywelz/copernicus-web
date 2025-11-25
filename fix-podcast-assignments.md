# Fixing Podcast Assignment and Architecture Discussion

## Immediate Issue: Mis-assigned Podcasts

Some legacy podcasts were assigned to john.covington instead of gwelz@jjay.cuny.edu.

### Solution:
I've added a new admin endpoint: `POST /api/admin/podcasts/reassign`

This allows you to reassign podcasts from one subscriber to another.

### To Fix the Issue:

1. First, find the subscriber IDs:
   - `gwelz@jjay.cuny.edu` subscriber_id = SHA256 hash of the email
   - Need to check what john.covington's subscriber_id is

2. Call the reassign endpoint with admin API key:
```json
POST /api/admin/podcasts/reassign
{
  "from_subscriber_id": "<john_covington_subscriber_id>",
  "to_subscriber_id": "<gwelz_subscriber_id>",
  "podcast_ids": null  // null = reassign all podcasts from john to gwelz
}
```

## Architecture Discussion: Two Collections

### Current Setup:
- **`podcast_jobs` collection**: All generation records (102 podcasts)
- **`episodes` collection**: Canonical/public catalog (64 episodes in RSS)

### Problem:
- Cross-referencing RSS status from `episodes` to `podcast_jobs` is complex
- State can get out of sync between collections
- Two sources of truth for "what's published"

### Better Approach (Future Refactor):

**Option 1: Single Source of Truth**
- Make `episodes` the ONLY source for RSS status
- `podcast_jobs` is just generation history
- Always check RSS status from `episodes` collection (no duplication)

**Option 2: Sync Function**
- Keep both collections
- Create a sync job that ensures `podcast_jobs.submitted_to_rss` matches `episodes.submitted_to_rss`
- Run this sync regularly

**Option 3: Simplify**
- Move all published podcasts from `podcast_jobs` to `episodes`
- Only keep failed/incomplete jobs in `podcast_jobs`
- Use `episodes` as the primary collection for all published content

### Recommendation:
For now, keep cross-referencing (Option 2), but in the future, Option 1 would be cleaner.

