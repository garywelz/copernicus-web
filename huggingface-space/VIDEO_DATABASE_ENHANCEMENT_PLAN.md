# Video Database Enhancement Plan

**Date:** January 11, 2025  
**Status:** ⚠️ In Progress

## Situation Analysis

### Two Collections Identified

1. **Database Collection (753 videos)** ✅
   - Location: PostgreSQL database (Cloud SQL)
   - Status: Schema enhancements applied (VIDEO_SCHEMA_APPLIED_SUCCESS.md)
   - Updated with category and year fields
   - This is the LARGER collection - **USE THIS ONE**

2. **Web App Collection (106-110 videos)** ⚠️
   - Location: https://scienceviddb-web-204731194849.us-central1.run.app/
   - Status: Only shows subset of videos (display/filtering issue)
   - This is the SMALLER collection - needs integration or deletion

## Plan

### Step 1: Export Database Videos ✅

**Script Created:** `scienceviddb/scripts/export_videos_metadata.ts`

**Purpose:** Export all 753 videos from PostgreSQL database to JSON metadata file

**To Run:**
```bash
cd /home/gdubs/scienceviddb
USE_SECRETS_MANAGER=true GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7 npm run export:videos
```

**Note:** This requires database connection. If local connection fails, need to:
- Use Cloud SQL Proxy, OR
- Run from Cloud Run/Cloud Shell, OR
- Query database via API endpoint

### Step 2: Create Video Database Viewer ✅

**File Created:** `videos-database-table.html`

**Features:**
- Similar design to Research Paper Database
- Search by title, description, channel
- Filter by category, discipline, year, transcript availability
- Sort by date, title, views
- Pagination (50 videos per page)
- Thumbnail display
- Channel information
- Transcript badges
- View counts and duration

### Step 3: Generate Metadata File

**File:** `videos-metadata.json` (to be generated)

**Location:** Upload to GCS: `gs://regal-scholar-453620-r7-podcast-storage/videos-metadata.json`

**Structure:**
```json
{
  "last_updated": "2025-01-11T...",
  "total_videos": 753,
  "videos": [...],
  "statistics": {
    "by_source": {...},
    "by_category": {...},
    "by_discipline": {...},
    "with_transcripts": 123
  }
}
```

### Step 4: Upload Files to GCS

1. Upload `videos-database-table.html` to GCS
2. Upload `videos-metadata.json` to GCS
3. Set public read permissions

### Step 5: Update Status Page

Update status dashboard to link to new video database viewer.

### Step 6: Handle Smaller Collection (106 videos)

**Option A: Integrate** (if they're different videos)
- Check if 106 videos are subset of 753
- If different, merge into database collection
- Regenerate metadata

**Option B: Delete/Ignore** (if they're duplicate/subset)
- If 106 videos are all in 753 collection, ignore web app collection
- Focus on database collection (753 videos)

## Current Status

✅ Video database viewer HTML created  
✅ Export script created  
⚠️ Need to run export script (requires database connection)  
⚠️ Need to generate metadata file  
⚠️ Need to upload files to GCS  

## Next Steps

1. Run export script to generate `videos-metadata.json`
2. Upload HTML and JSON to GCS
3. Test viewer
4. Update status page link
5. Investigate web app collection (106 videos) - integrate or ignore

---

**Status:** Viewer created, awaiting metadata export and upload.
