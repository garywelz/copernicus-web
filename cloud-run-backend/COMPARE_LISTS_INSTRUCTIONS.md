# Instructions: Compare Podcast Lists

## Goal
Find which podcast is in `gwelz@jjay.cuny.edu` account but NOT in the podcast database/list.

## Simple Comparison (79 GCS files vs Database)

### Step 1: Get List of Audio Files in GCS
There are **79 audio files** in:
```
gs://regal-scholar-453620-r7-podcast-storage/audio/
```

### Step 2: Get List of Podcasts in Database
- Go to admin dashboard → Podcast Database
- This shows all podcasts in the `episodes` collection
- Count should be ~64-65 podcasts

### Step 3: Get List for gwelz@jjay.cuny.edu
- Go to admin dashboard → Subscribers
- Click "View Podcasts" for gwelz@jjay.cuny.edu
- This shows ~57 podcasts (union of podcast_jobs + episodes)

### Step 4: Compare
For each podcast in the gwelz "View Podcasts" list:
- Is its filename in the podcast database list?
- If NO → This is the discrepancy!

## Quick Check Method

1. Open the "View Podcasts" modal for gwelz@jjay.cuny.edu
2. Note all 57 canonical filenames (e.g., `ever-chem-250021`)
3. Open the podcast database page
4. Search for each filename
5. The one that doesn't appear is the missing podcast

## What We're Looking For

A podcast that:
- ✅ Exists in `podcast_jobs` collection (so shows in account)
- ✅ Has audio file in GCS
- ❌ Does NOT exist in `episodes` collection (not in database)
- ❌ Or exists but assigned to different subscriber

This would explain why:
- "View Podcasts" shows 57 (includes podcast_jobs)
- Database shows 56 (episodes only)
- Difference = 1 podcast

## Next Steps After Finding It

Once we identify the missing podcast:
1. Check if it was deleted from episodes (why?)
2. Decide: Re-create in episodes OR remove from podcast_jobs OR reassign




