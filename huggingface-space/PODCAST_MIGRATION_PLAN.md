# Podcast Migration Plan - RSS Feed Source

**Date:** January 10, 2025  
**Source:** Google Cloud Storage RSS Feed (not local files)  
**RSS Feed:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml

## Current Status

### ✅ Podcast Data Sources

**RSS Feed:**
- **Location:** GCS RSS feed
- **URL:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml
- **Count:** **79 podcasts** in RSS feed ✅
- **Categories:**
  - Biology: 19
  - Computer Science: 18
  - Physics: 16
  - Mathematics: 16
  - Chemistry: 10

**Audio Files in GCS:**
- **Location:** `gs://regal-scholar-453620-r7-podcast-storage/audio/`
- **Count:** **97 audio files** (`.mp3`)
- **Note:** 18 more audio files than RSS feed items (may include podcasts not yet in RSS feed)

**Total Expected:** ~82 podcasts (as mentioned)

### ❌ Not Using Local Files
- **Local `podcasts.json`:** 32 podcasts - **NOT using this**
- **Source:** RSS feed and GCS bucket only

## Migration Strategy

### Step 1: Extract from RSS Feed ✅

**Script:** `scripts/podcasts/extract_podcasts_from_rss.py`

**What it does:**
- Fetches RSS feed from GCS
- Parses XML and extracts podcast metadata
- Extracts: title, guid, description, audio URL, thumbnail, duration, published date, category
- Extracts references (DOIs, PMIDs, arXiv IDs) from descriptions
- Extracts keywords/hashtags from descriptions
- Converts to unified schema format

**Status:** ✅ Created and tested - extracts 79 podcasts

### Step 2: Migrate to Unified Schema ✅

**Script:** `scripts/podcasts/migrate_rss_podcasts_to_unified_schema.py`

**What it does:**
- Takes RSS feed podcasts (from Step 1)
- Adds cross-modal linking fields (`related_papers[]`, `related_videos[]`, `related_processes[]`)
- Adds required fields (`source`, `acquired_date`, `category`)
- Extracts paper IDs from references
- Generates proper IDs (`podcast_{guid}`)
- Outputs unified schema JSON

**Status:** ✅ Created and ready

### Step 3: Check for Additional Podcasts

**To Do:**
- Compare RSS feed (79 podcasts) with audio files (97 files)
- Identify audio files not in RSS feed
- Extract metadata for additional podcasts if needed
- Add to migration output

**Potential Sources:**
- Audio files in GCS not yet in RSS feed
- Other JSON files in GCS bucket
- API endpoint data

## Migration Execution

### Option 1: Migrate RSS Feed Podcasts (Recommended)

**Step 1: Extract from RSS**
```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
python3 scripts/podcasts/extract_podcasts_from_rss.py \
  --output podcasts_from_rss.json
```

**Step 2: Migrate to Unified Schema**
```bash
python3 scripts/podcasts/migrate_rss_podcasts_to_unified_schema.py \
  --output podcasts_migrated.json
```

**Step 3: Validate**
```bash
python3 scripts/podcasts/validate_podcast_metadata.py \
  podcasts_migrated.json \
  --threshold 0.85
```

### Option 2: Check for Additional Podcasts

**Compare RSS feed with audio files:**
```bash
# Extract GUIDs from RSS feed
python3 scripts/podcasts/extract_podcasts_from_rss.py --output temp_rss.json
python3 -c "import json; d=json.load(open('temp_rss.json')); print('\n'.join([p['guid'] for p in d]))" > rss_guids.txt

# List audio files
gsutil ls gs://regal-scholar-453620-r7-podcast-storage/audio/*.mp3 | \
  sed 's/.*\///' | sed 's/\.mp3$//' > audio_guids.txt

# Find differences
diff rss_guids.txt audio_guids.txt
```

## Next Steps

1. ✅ **Extract RSS Feed Podcasts** - Script ready, tested (79 podcasts)
2. ✅ **Migrate to Unified Schema** - Script ready
3. ⚠️ **Check for Additional Podcasts** - Compare RSS (79) with audio files (97)
4. ✅ **Validate Migrated Data** - Validation script ready
5. ⚠️ **Handle Additional Podcasts** - If found, extract metadata and add to migration

## Summary

**Current Status:**
- ✅ RSS feed accessible: 79 podcasts
- ✅ Audio files in GCS: 97 files
- ✅ Extraction script ready and tested
- ✅ Migration script ready
- ✅ Validation script ready
- ⚠️ Need to check for additional podcasts (97 audio files vs 79 RSS items)

**Recommendation:**
1. Run migration with RSS feed podcasts (79 podcasts)
2. Check for additional podcasts from audio files
3. Add additional podcasts if found

---

**Status:** ✅ Ready to migrate RSS feed podcasts, ⚠️ Need to check for additional podcasts
