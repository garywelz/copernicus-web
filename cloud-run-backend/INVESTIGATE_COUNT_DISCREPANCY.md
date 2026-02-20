# Count Discrepancy Investigation

## Problem
- Admin dashboard subscriber list shows: 6 podcasts for gary.welz@me.com
- "View Podcasts" modal shows: 7 podcasts for gary.welz@me.com

## User's Hypothesis
There may be a podcast in gwelz@jjay.cuny.edu's list (or gary.welz@me.com's list) that:
1. Is NOT in the podcast database (episodes collection), OR
2. Was deleted from the database but not removed from the subscriber's account

## Investigation Approach

### Step 1: Compare Sources
The "View Podcasts" modal uses union counting (podcast_jobs + episodes), while the subscriber count might use episodes only.

### Step 2: Find the Discrepancy
For each subscriber, check:
- Podcasts in `podcast_jobs` collection (by subscriber_id)
- Podcasts in `episodes` collection (by subscriber_id)
- Find podcasts in `podcast_jobs` but NOT in `episodes`

### Step 3: Check Database
For any podcast found in `podcast_jobs` but not in `episodes`:
- Does it exist in `episodes` at all? (might be deleted)
- Is it assigned to a different subscriber in `episodes`?

## Solution

### Option 1: Make subscriber count match "View Podcasts"
Update the subscriber count endpoint to use UNION counting (podcast_jobs + episodes), just like the "View Podcasts" endpoint does.

### Option 2: Clean up orphaned podcasts
If a podcast exists in `podcast_jobs` but not in `episodes` (and is truly deleted), either:
- Remove it from `podcast_jobs`, OR
- Re-create it in `episodes` if it should exist

## Next Steps

1. Run a script to compare podcast_jobs vs episodes for gary.welz@me.com
2. Identify which podcast is causing the discrepancy
3. Decide: fix the count logic OR clean up the data




