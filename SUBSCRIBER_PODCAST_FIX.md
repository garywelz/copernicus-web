# Subscriber Podcast List Fix - November 27, 2025

## 🐛 Bug Description
The admin dashboard was showing incorrect podcast lists for subscribers. For example, `john.covington@verizon.net` only created 1 podcast (about Covid 19), but the dashboard showed 61 podcasts in his list. Most of these podcasts were not actually created by this subscriber.

## 🔍 Root Cause
The `admin_get_subscriber_podcasts` endpoint in `cloud-run-backend/main.py` was querying ALL episodes from the RSS feed regardless of subscriber ownership. The query was:

```python
# BEFORE FIX (line 3771)
episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('submitted_to_rss', '==', True).limit(100)
```

This returned all RSS episodes for every subscriber, causing massive list inflation.

## ✅ Fix Applied

### 1. Fixed Episode Query to Filter by Subscriber ID
Changed the query to filter episodes by `subscriber_id`:

```python
# AFTER FIX (line 3771)
episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id)
```

Episodes already have a `subscriber_id` field (set in `_prepare_episode_document`), so we can properly filter by subscriber ownership.

### 2. Added Count Recalculation Endpoint
Added a new admin endpoint to recalculate subscriber podcast counts:
- `POST /api/admin/subscribers/{subscriber_id}/recalculate-count`
- Counts actual podcasts from `podcast_jobs` collection
- Updates the stored `podcasts_generated` count

## 📋 Files Changed

- `cloud-run-backend/main.py`
  - Modified `admin_get_subscriber_podcasts()` to filter episodes by subscriber_id (line ~3771)
  - Added `recalculate_subscriber_podcast_count()` endpoint (line ~3727)

## 🎯 Impact
- Subscribers now only see podcasts they actually created
- Podcast counts in admin dashboard match actual podcast lists
- Counts align with RSS feed and website

## 📦 Deployment
- **Deployed:** November 27, 2025
- **Service:** `copernicus-podcast-api`
- **Revision:** `copernicus-podcast-api-00132-hhq`

