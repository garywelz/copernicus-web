# Sync Scripts Ready ✅

**Date:** December 2025  
**Status:** Scripts created and ready to use

---

## Summary

All three tasks are complete:

1. ✅ **Ingested 260 more mathematics papers** - Now have 490 papers total (close to 500+ target)
2. ✅ **Created paper sync script** - Syncs papers from PostgreSQL to Firestore with embeddings
3. ✅ **Created video sync script** - Syncs videos from Science Video Database to Firestore with embeddings

---

## Scripts Created

### 1. Paper Sync Script

**Location:** `cloud-run-backend/scripts/sync_research_papers.py`

**Purpose:** Sync research papers from PostgreSQL (research metadata database) to Firestore

**Features:**
- Reads papers from PostgreSQL
- Generates embeddings using Vertex AI
- Writes to Firestore `research_papers` collection
- Skips existing papers (optional)
- Dry-run mode for testing
- Progress reporting

**Usage:**
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend

# Dry run (test first)
python3 scripts/sync_research_papers.py --dry-run --limit 10

# Sync all papers
python3 scripts/sync_research_papers.py

# Sync with limit
python3 scripts/sync_research_papers.py --limit 100

# Don't skip existing (re-sync)
python3 scripts/sync_research_papers.py --no-skip-existing
```

### 2. Video Sync Script

**Location:** `cloud-run-backend/scripts/sync_videos.py`

**Purpose:** Sync videos from Science Video Database (PostgreSQL) to Firestore

**Features:**
- Reads videos from Science Video Database PostgreSQL
- Fetches transcripts if available
- Generates embeddings from title, description, and transcript
- Writes to Firestore `science_videos` collection
- Skips existing videos (optional)
- Dry-run mode for testing
- Progress reporting

**Requirements:**
- `psycopg2-binary` package: `pip install psycopg2-binary`
- Database URL: Set `SCIENCEVIDDB_DATABASE_URL` environment variable or use Secrets Manager

**Usage:**
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend

# Install dependency first
pip install psycopg2-binary

# Set database URL (or use Secrets Manager)
export SCIENCEVIDDB_DATABASE_URL="postgresql://user:pass@host:port/database"

# Dry run (test first)
python3 scripts/sync_videos.py --dry-run --limit 10

# Sync all videos
python3 scripts/sync_videos.py

# Sync with limit
python3 scripts/sync_videos.py --limit 50

# Don't skip existing (re-sync)
python3 scripts/sync_videos.py --no-skip-existing
```

---

## Current Status

### Research Papers
- **PostgreSQL:** 490 papers ✅
- **Firestore:** 0 papers (ready to sync)
- **Target:** 500+ papers (need 10 more, or sync current 490)

### Videos
- **PostgreSQL:** 151+ videos (per web interface: https://scienceviddb-web-204731194849.us-central1.run.app/)
- **Firestore:** 0 videos (ready to sync)
- **Target:** 1000+ videos (need to ingest more, but can sync existing 151 first)

### Podcasts
- **Firestore:** 46 podcasts (45 with embeddings) ✅
- **Status:** Complete, no sync needed

---

## Next Steps

### Immediate (Can Do Now)

1. **Sync Papers to Firestore**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   python3 scripts/sync_research_papers.py --dry-run --limit 10  # Test first
   python3 scripts/sync_research_papers.py  # Sync all
   ```

2. **Create Firestore Collection for Videos**
   - The `science_videos` collection will be created automatically on first write
   - Need to create vector index after first sync:
   ```bash
   gcloud firestore indexes composite create \
     --project=regal-scholar-453620-r7 \
     --database="copernicusai" \
     --collection-group=science_videos \
     --query-scope=COLLECTION \
     --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
   ```

3. **Sync Videos to Firestore**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   pip install psycopg2-binary  # If not already installed
   export SCIENCEVIDDB_DATABASE_URL="..."  # Or use Secrets Manager
   python3 scripts/sync_videos.py --dry-run --limit 10  # Test first
   python3 scripts/sync_videos.py  # Sync all
   ```

### After Sync

4. **Update Vector Search Tools**
   - Extend `search_semantic` to include `science_videos` collection
   - Update RAG service to include video transcripts in context

5. **Test Vector Search & RAG**
   - Test semantic search across all content types
   - Test RAG with questions that should use video content

---

## Firestore Collections

After syncing, you'll have:

1. **`research_papers`** - Research paper metadata with embeddings
2. **`science_videos`** - Video metadata + transcripts with embeddings
3. **`podcast_jobs`** - Podcast metadata with embeddings (already exists)

All three collections will support vector search once indexes are created.

---

## Vector Indexes Needed

### Already Created ✅
- `research_papers` - Vector index for embeddings
- `podcast_jobs` - Vector index for embeddings

### Need to Create
- `science_videos` - Vector index for embeddings (create after first video sync)

---

## Notes

- Both sync scripts use dry-run mode for safe testing
- Scripts skip existing documents by default (use `--no-skip-existing` to re-sync)
- Embeddings are generated automatically during sync
- Scripts handle errors gracefully and continue processing
- Progress is reported every 10 items

---

## Troubleshooting

### Paper Sync Issues

**Import errors:**
- Make sure you're running from `cloud-run-backend` directory
- Ensure research metadata database is accessible
- Check that venv is activated if needed

**Firestore connection:**
- Verify GCP credentials are set up
- Check that `GCP_PROJECT_ID` is set correctly

### Video Sync Issues

**psycopg2 not found:**
```bash
pip install psycopg2-binary
```

**Database connection:**
- Set `SCIENCEVIDDB_DATABASE_URL` environment variable
- Or ensure Secrets Manager access is configured
- May need Cloud SQL proxy if connecting to Cloud SQL

**Transcript fetching:**
- Some videos may not have transcripts
- Script continues even if transcript fetch fails

---

**Status:** All scripts ready. Can begin syncing content to Firestore! 🚀

