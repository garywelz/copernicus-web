# Database Access Setup - Complete ✅

**Date:** December 2025  
**Status:** Research Metadata DB ✅ | Video DB ⚠️ (needs Cloud SQL proxy)

---

## Summary

### ✅ Research Paper Metadata Database - WORKING

**Location:** `/home/gdubs/copernicusai-research-metadata`  
**Database:** PostgreSQL (Cloud SQL)  
**Status:** ✅ Accessible and working

**Current Content:**
- **Total Papers:** 243
- **Mathematics Papers:** 238
- **Category Distribution:**
  - math.AT (Algebraic Topology): 50
  - math.NT (Number Theory): 50
  - math.RA (Rings and Algebras): 50
  - math.CO (Combinatorics): 36
  - math.AG (Algebraic Geometry): 31
  - Plus 15+ other math categories

**Access Method:**
```bash
cd /home/gdubs/copernicusai-research-metadata
source venv/bin/activate
python3 scripts/check_ingested_papers.py
```

**Next Steps:**
- Need to ingest ~260 more papers to reach 500+ target
- Papers are ready to sync to Firestore

---

### ⚠️ Science Video Database - Needs Cloud SQL Proxy

**Location:** `/home/gdubs/scienceviddb`  
**Database:** PostgreSQL (Cloud SQL)  
**Status:** ⚠️ Requires Cloud SQL proxy for local access

**Database URL:** `postgresql://scienceviddb_user:SciVidDB-Test-2024@localhost:5433/scienceviddb`

**Issue:** Connection refused on localhost:5433 (Cloud SQL proxy not running)

**Solution Options:**

#### Option 1: Run Cloud SQL Proxy (Recommended for Local Development)

```bash
# Install Cloud SQL Proxy (if not already installed)
# Download from: https://cloud.google.com/sql/docs/postgres/sql-proxy

# Get instance connection name
gcloud sql instances describe scienceviddb-db --project=regal-scholar-453620-r7 --format="value(connectionName)"

# Run proxy (replace INSTANCE_CONNECTION_NAME)
cloud-sql-proxy INSTANCE_CONNECTION_NAME --port=5433
```

#### Option 2: Use Direct Connection (If Public IP Enabled)

Update the database URL to use the public IP instead of localhost:
```bash
# Get public IP
gcloud sql instances describe scienceviddb-db --project=regal-scholar-453620-r7 --format="value(ipAddresses[0].ipAddress)"

# Update secret or use DATABASE_URL directly
export DATABASE_URL="postgresql://scienceviddb_user:SciVidDB-Test-2024@PUBLIC_IP:5432/scienceviddb"
```

#### Option 3: Check Content from Cloud Run/Production

If the database is accessible from Cloud Run, you can create a simple API endpoint to check counts, or access it from a Cloud Run job.

**Access Method (after proxy setup):**
```bash
cd /home/gdubs/scienceviddb
export USE_SECRETS_MANAGER=true
npm run verify-ingestion --workspace=packages/ingestion
```

---

## Current Status Summary

| System | Status | Papers/Videos | Access Method |
|--------|--------|---------------|---------------|
| Research Metadata DB | ✅ Working | 243 papers | `source venv/bin/activate` |
| Science Video DB | ⚠️ Needs proxy | Unknown | Cloud SQL proxy required |
| CopernicusAI Firestore | ✅ Working | 0 papers, 46 podcasts | Direct access |

---

## Next Steps

### Immediate (Can Do Now)

1. **Ingest More Papers** (Research Metadata DB is ready)
   ```bash
   cd /home/gdubs/copernicusai-research-metadata
   source venv/bin/activate
   python3 scripts/ingest_mathematics.py
   # Target: Ingest ~260 more papers to reach 500+
   ```

2. **Sync Papers to Firestore**
   - Create sync script (see CONTENT_INGESTION_PLAN.md)
   - Generate embeddings during sync
   - Store in Firestore `research_papers` collection

### After Video DB Setup

3. **Check Video Count**
   - Set up Cloud SQL proxy
   - Run verification script
   - Document current video count

4. **Expand Video Channels**
   - Add 50+ channels to registry
   - Ingest 1000+ videos

5. **Sync Videos to Firestore**
   - Create sync script
   - Generate embeddings from transcripts
   - Store in Firestore `science_videos` collection

---

## Database Connection Details

### Research Metadata Database

**Connection:** Working via venv activation  
**Environment:** Virtual environment has all dependencies  
**Location:** `/home/gdubs/copernicusai-research-metadata/venv`  
**Dependencies:** ✅ All installed (pydantic-settings, sqlalchemy, etc.)

### Science Video Database

**Connection:** Requires Cloud SQL proxy  
**Secret:** `scienceviddb-database-url` in Secrets Manager  
**Format:** `postgresql://user:pass@localhost:5433/database`  
**Proxy Port:** 5433

---

## Verification Commands

### Research Metadata DB
```bash
cd /home/gdubs/copernicusai-research-metadata
source venv/bin/activate
python3 scripts/check_ingested_papers.py
```

### Science Video DB (after proxy setup)
```bash
cd /home/gdubs/scienceviddb
export USE_SECRETS_MANAGER=true
npm run verify-ingestion --workspace=packages/ingestion
```

### Firestore
```bash
cd /home/gdubs/copernicus-web-public
python3 scripts/assess_content_status.py
```

---

## Notes

- Research metadata database is ready for ingestion ✅
- Video database needs Cloud SQL proxy setup for local access
- Both databases can be accessed from Cloud Run without proxy
- Firestore is ready and working ✅

