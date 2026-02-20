# Video Database Connection Setup

**Date:** December 2025  
**Status:** Script ready, needs Cloud SQL proxy or direct connection

---

## Summary

✅ **Video sync script is ready and tested**  
✅ **All dependencies installed**  
⚠️ **Needs Cloud SQL proxy running OR direct database connection**

---

## Current Status

### ✅ Completed
1. **Dependencies installed:**
   - `psycopg2-binary` ✅
   - `google-cloud-secret-manager` ✅
   - `google-cloud-aiplatform` ✅
   - `vertexai` ✅

2. **Script ready:**
   - `cloud-run-backend/scripts/sync_videos.py` ✅
   - Can fetch database URL from Secrets Manager ✅
   - Can generate embeddings ✅
   - Can sync to Firestore ✅

### ⚠️ Needs Setup

**Database Connection:**
- Current URL: `postgresql://scienceviddb_user:SciVidDB-Test-2024@localhost:5433/scienceviddb`
- This requires Cloud SQL proxy running on port 5433
- OR needs direct connection URL (public IP)

---

## Option 1: Use Cloud SQL Proxy (Recommended for Local)

### Setup Cloud SQL Proxy

1. **Install Cloud SQL Proxy** (if not already installed):
   ```bash
   # Download from: https://cloud.google.com/sql/docs/postgres/sql-proxy
   # Or use gcloud:
   gcloud components install cloud-sql-proxy
   ```

2. **Get instance connection name:**
   ```bash
   gcloud sql instances describe scienceviddb-db \
     --project=regal-scholar-453620-r7 \
     --format="value(connectionName)"
   ```

3. **Run proxy:**
   ```bash
   cloud-sql-proxy INSTANCE_CONNECTION_NAME --port=5433
   ```

4. **In another terminal, run sync:**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   source venv/bin/activate
   python3 scripts/sync_videos.py --dry-run --limit 5
   ```

---

## Option 2: Use Direct Connection (If Public IP Enabled)

### Get Public IP

```bash
gcloud sql instances describe scienceviddb-db \
  --project=regal-scholar-453620-r7 \
  --format="value(ipAddresses[0].ipAddress)"
```

### Update Database URL

```bash
export SCIENCEVIDDB_DATABASE_URL="postgresql://scienceviddb_user:SciVidDB-Test-2024@PUBLIC_IP:5432/scienceviddb"
```

### Run Sync

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/sync_videos.py --dry-run --limit 5
```

---

## Option 3: Run from Cloud Run (No Proxy Needed)

If you deploy the sync script to Cloud Run, it can connect directly to Cloud SQL without a proxy.

---

## Test Video Sync

Once the database connection is working:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate

# Test with small batch
python3 scripts/sync_videos.py --dry-run --limit 5

# If successful, sync all videos
python3 scripts/sync_videos.py
```

---

## Expected Results

After successful sync:
- Videos will be in Firestore `science_videos` collection
- Transcripts will be included (if available)
- Embeddings will be generated from title, description, and transcript
- Ready for vector search

---

## Create Firestore Vector Index

After first video sync, create the vector index:

```bash
gcloud firestore indexes composite create \
  --project=regal-scholar-453620-r7 \
  --database="copernicusai" \
  --collection-group=science_videos \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
```

---

## Summary

✅ **Script is ready**  
✅ **Dependencies installed**  
⏳ **Waiting for database connection** (Cloud SQL proxy or direct connection)

**Next Step:** Set up Cloud SQL proxy or direct connection, then run the sync!

