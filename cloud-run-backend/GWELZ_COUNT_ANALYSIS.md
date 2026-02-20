# gwelz@jjay.cuny.edu Count Analysis

## Problem
User reports that `gwelz@jjay.cuny.edu` shows 57 podcasts by their count, but needs to verify:
- Which podcasts are in the gwelz account
- Which podcasts are in the podcast database list
- Which podcasts are in the "all podcasts" list
- **Find which podcast is in the account but NOT in the others**

## Comparison Needed

### 1. Podcasts in gwelz@jjay.cuny.edu account
Sources:
- `podcast_jobs` collection where `subscriber_id` = gwelz's ID
- `episodes` collection where `subscriber_id` = gwelz's ID
- **Union of both** = what "View Podcasts" modal shows

### 2. Podcasts in podcast database list
- All podcasts in `episodes` collection (the database)

### 3. Podcasts in "all podcasts" list  
- This should be the same as the database list (all episodes)

## What to Find

For each podcast in the gwelz account, check:
- ✓ Is it in the episodes collection? (database)
- ✓ Is it assigned to gwelz@jjay.cuny.edu in episodes?

Find the podcast(s) that are:
- In `podcast_jobs` for gwelz (so shows in account)
- BUT NOT in `episodes` collection (so not in database)

OR

- In `podcast_jobs` for gwelz
- BUT assigned to a different subscriber in `episodes`

## Query Needed

```python
# Get gwelz subscriber_id
gwelz_id = get_subscriber_id("gwelz@jjay.cuny.edu")

# Get podcasts from podcast_jobs
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', gwelz_id).stream()
gwelz_jobs = {job.result.canonical_filename for job in jobs_query}

# Get podcasts from episodes  
episodes_query = db.collection('episodes').where('subscriber_id', '==', gwelz_id).stream()
gwelz_episodes = {ep.id for ep in episodes_query}

# Union (all in account)
gwelz_all = gwelz_jobs | gwelz_episodes

# Get ALL episodes
all_episodes = {ep.id for ep in db.collection('episodes').stream()}

# Find missing
missing = gwelz_all - all_episodes
```

## Next Steps

1. Run the comparison script to find the discrepancy
2. Identify which podcast filename is in the account but not in database
3. Decide: remove from podcast_jobs OR create in episodes OR reassign




