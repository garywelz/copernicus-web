# Database Access Requirements

**Date:** January 10, 2025  
**Purpose:** Document what's needed to query Firestore and Cloud SQL databases

## Current Status

### ✅ Already Accessible
- **Google Cloud Storage:** ✅ Accessible via `gsutil`
- **Local Files:** ✅ Accessible (processes, podcasts, papers)
- **Science Video Database Web App:** ✅ Visible at https://scienceviddb-web-204731194849.us-central1.run.app/ (110 videos)

### ⚠️ Requires Setup
- **Firestore:** Database exists, need to query
- **Cloud SQL (PostgreSQL):** Instance exists, need connection

## Science Video Database Status

**Web App:** https://scienceviddb-web-204731194849.us-central1.run.app/  
**Total Videos:** 110 indexed  
**Breakdown:**
- Biology: 10 videos
- Chemistry: 17 videos
- Computer Science: 37 videos
- Mathematics: 33 videos
- Physics: 13 videos

**Status:** ✅ Working and accessible via web interface

## Firestore Access

### What We Need
1. **Google Cloud Authentication** - Already configured (via `gcloud auth`)
2. **Project Access** - Already have project: `regal-scholar-453620-r7`
3. **Firestore API Enabled** - Should already be enabled
4. **Collection Names** - Need to discover what collections exist

### To Query Firestore

**Option 1: gcloud CLI (Already Available)**
```bash
# List collections
gcloud firestore collections list --project=regal-scholar-453620-r7

# List documents in a collection
gcloud firestore documents list COLLECTION_NAME --project=regal-scholar-453620-r7

# Get a document
gcloud firestore documents get DOCUMENT_PATH --project=regal-scholar-453620-r7
```

**Option 2: Firestore Admin SDK (Python/Node.js)**
- Requires `google-cloud-firestore` package
- Uses Application Default Credentials (already configured)

**Option 3: Google Cloud Console**
- Navigate to: https://console.cloud.google.com/firestore/databases
- Select project: `regal-scholar-453620-r7`
- Browse collections and documents

### No Additional Credentials Needed
- ✅ gcloud CLI is authenticated
- ✅ Project is configured
- ✅ Firestore database exists
- ✅ Should be able to query immediately

## Cloud SQL (PostgreSQL) Access

### What We Need
1. **Database Connection String** - Available in Secrets Manager
2. **Connection Method** - Choose one:
   - **Cloud SQL Proxy** (recommended for local)
   - **Public IP** (if enabled)
   - **Private IP** (requires VPC)
   - **Cloud Run/Compute Engine** (direct connection)

### Current Setup
**Database:** `regal-scholar-453620-r7:us-central1:scienceviddb-db` (PostgreSQL)  
**Secret:** `copernicus-db-url` or `scienceviddb-database-url` (in Secrets Manager)

### Connection Options

#### Option 1: Cloud SQL Proxy (Local Development)
```bash
# Download Cloud SQL Proxy (if not installed)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Run proxy (in background)
./cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb-db \
  --port=5432 &

# Connect via psql
psql -h 127.0.0.1 -U USERNAME -d DATABASE_NAME
```

**Requires:**
- Cloud SQL Proxy binary
- Database username/password (from secrets or create)
- Local PostgreSQL client (`psql`)

#### Option 2: Use Existing Database Client (TypeScript)
```bash
# From scienceviddb project
cd scienceviddb
npm run db:state  # Uses existing database client
```

**Requires:**
- Environment variables: `USE_SECRETS_MANAGER=true`, `GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7`
- Database client package (already installed)
- Application Default Credentials

#### Option 3: Google Cloud Console (SQL)
- Navigate to: https://console.cloud.google.com/sql/instances
- Select instance: `scienceviddb-db`
- Use SQL editor or connect via web console

**Requires:**
- Browser access to Cloud Console
- Login credentials

#### Option 4: Execute on Cloud Run
```bash
# Deploy/run script on Cloud Run
gcloud run deploy check-db-state \
  --source . \
  --service-account=service-account@project.iam.gserviceaccount.com \
  --add-cloudsql-instances=regal-scholar-453620-r7:us-central1:scienceviddb-db \
  --set-env-vars="USE_SECRETS_MANAGER=true,GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7"
```

**Requires:**
- Cloud Run deployment setup
- Service account with Cloud SQL Client role

### What You Need to Provide

**For Firestore:**
- ✅ Nothing additional needed - we can query now
- Optional: Collection names if you know them

**For Cloud SQL:**
- **Option A:** Database username/password (if using direct connection)
- **Option B:** Confirm Cloud SQL Proxy is acceptable approach
- **Option C:** Use existing database client scripts (already set up)

**Recommended:** Use existing database client scripts (Option 2) since they're already configured.

## Quick Test: Query Firestore

Let's try querying Firestore right now:

```bash
# List collections
gcloud firestore collections list --project=regal-scholar-453620-r7

# If collections exist, list documents
gcloud firestore documents list COLLECTION_NAME --project=regal-scholar-453620-r7
```

**No additional credentials needed** - uses existing gcloud authentication.

## Quick Test: Query Cloud SQL

Since the database client is already set up, we can try:

```bash
cd scienceviddb
USE_SECRETS_MANAGER=true GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7 npm run db:state
```

**May need:**
- Service account credentials
- Or Cloud SQL Proxy if connection fails

## Summary

### Firestore
- ✅ **No additional setup needed**
- ✅ Can query via gcloud CLI immediately
- ✅ Or use Firestore Admin SDK

### Cloud SQL
- ⚠️ **Requires connection setup**
- **Option 1:** Use existing database client (recommended)
- **Option 2:** Cloud SQL Proxy for local
- **Option 3:** Cloud Console for manual queries

**Recommendation:** 
1. Try Firestore query first (no setup needed)
2. Use existing database client scripts for Cloud SQL (already configured)

---

**Next Steps:**
1. Try querying Firestore now (no additional setup)
2. Test database client script for Cloud SQL
3. If needed, set up Cloud SQL Proxy
