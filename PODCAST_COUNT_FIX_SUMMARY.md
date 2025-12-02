# Podcast Count Discrepancy Fix - December 1, 2025

## 🐛 Issue
- **Total Podcasts**: 57
- **Sum of Subscriber Counts**: 59 (50 + 8 + 1)
- **Discrepancy**: 2 podcasts

The sum of individual subscriber counts (50 + 8 + 1 = 59) was higher than the total count (57), indicating either:
1. Double counting in subscriber counts
2. Undercounting in total count
3. Podcasts assigned to multiple subscribers

## ✅ Fixes Applied

### 1. Updated Subscriber Count Logic
Changed from using `max(podcast_jobs_count, unique_episodes_count)` to counting unique podcasts by:
- Counting all unique canonical filenames from both `podcast_jobs` and `episodes` collections
- Using union of canonical filenames to avoid double counting
- Adding podcast_jobs without canonical filenames as separate items

### 2. Updated Total Count Logic  
Changed from using `max(podcast_jobs_count, episodes_count)` to:
- Building a set of all unique podcasts by canonical filename across both collections
- Counting each podcast exactly once globally

### 3. Updated Subscriber Podcast List Endpoint
Updated `/api/subscribers/podcasts/{subscriber_id}` to use the same comprehensive logic as the admin endpoint, ensuring consistency.

## 📋 Files Changed

- `cloud-run-backend/main.py`
  - Updated `list_all_subscribers()` counting logic (lines ~3856-3906)
  - Updated `recalculate_subscriber_podcast_count()` counting logic (lines ~3959-4008)
  - Updated `admin_get_all_podcasts()` total count calculation (lines ~5375-5401)
  - Updated `get_subscriber_podcasts()` to match admin endpoint logic

## 🎯 Expected Results

After deployment and recalculation:
- Total podcast count: Should match unique podcasts across all collections
- Subscriber counts: Should sum to the total count
- Each podcast counted exactly once

## 📦 Deployment
- **Deployed:** December 1, 2025
- **Service:** `copernicus-podcast-api`
- **Latest Revision:** `copernicus-podcast-api-00148-t8p`

## 🔍 Next Steps

The counting logic has been fixed to avoid double counting. The total count (57) should be the authoritative source. If subscriber counts still don't match, it may indicate:
- 2 podcasts are incorrectly assigned to gwelz@jjay.cuny.edu
- Or the total count needs to be recalculated

To verify: After refreshing the admin dashboard, check if the counts now match. If not, we may need to investigate specific podcasts that are causing the discrepancy.

