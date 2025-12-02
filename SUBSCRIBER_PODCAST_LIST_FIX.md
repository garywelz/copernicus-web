# Subscriber Podcast List Fix - November 27, 2025

## 🐛 Bug Description
The admin dashboard was showing only 16 podcasts for `gwelz@jjay.cuny.edu` when there should be approximately 48 podcasts for this subscriber.

## 🔍 Root Cause Analysis
The `admin_get_subscriber_podcasts` endpoint was querying episodes but might have been missing some that:
1. Don't have `subscriber_id` set (legacy episodes)
2. Don't have `job_id` set
3. Are linked only by canonical filename

The endpoint logic was updated to query episodes in multiple ways, but the count might not be capturing all matches.

## ✅ Fix Applied

### Enhanced Episode Lookup
Modified `admin_get_subscriber_podcasts()` to query episodes in THREE ways:
1. **By subscriber_id**: Direct match on episodes with subscriber_id field
2. **By job_id**: Episodes linked to this subscriber's podcast_jobs via job_id
3. **By canonical filename**: Look up episodes directly using canonical filenames from podcast_jobs

This ensures we capture all episodes for this subscriber, even if metadata fields are missing.

### Updated Subscriber Count Calculation
Modified `list_all_subscribers()` to calculate podcast counts using the same comprehensive logic:
- Count from podcast_jobs collection
- Count from episodes by subscriber_id
- Count from episodes by job_id
- Use the maximum to ensure accurate counts

## 📋 Files Changed

- `cloud-run-backend/main.py`
  - Enhanced `admin_get_subscriber_podcasts()` with comprehensive episode lookup (lines ~3911-4085)
  - Updated `list_all_subscribers()` to use comprehensive counting logic (lines ~3706-3745)

## 🎯 Expected Results
After deployment:
- `gwelz@jjay.cuny.edu` should show all ~48 podcasts in the list
- Subscriber count should match the actual number of podcasts returned

## 📦 Deployment
- **Deployed:** November 27, 2025
- **Service:** `copernicus-podcast-api`
- **Revision:** `copernicus-podcast-api-00140-lhz`

