# What's Needed to Query Firestore and Cloud SQL

**Date:** January 10, 2025  
**Current Status:** 
- ✅ Science Video Database: 110 videos visible at https://scienceviddb-web-204731194849.us-central1.run.app/
- ✅ Google Cloud authenticated (garywelz@gmail.com)
- ✅ Project configured (regal-scholar-453620-r7)

## Science Video Database Status

**Web App:** https://scienceviddb-web-204731194849.us-central1.run.app/  
**Total:** 110 videos indexed ✅  
**Breakdown:**
- Biology: 10 videos
- Chemistry: 17 videos  
- Computer Science: 37 videos
- Mathematics: 33 videos
- Physics: 13 videos

**Status:** ✅ Working and accessible

## Firestore Database

### What You Need to Provide: Nothing! ✅

**Current Setup:**
- ✅ Google Cloud authenticated
- ✅ Project configured  
- ✅ Firestore database exists
- ✅ Can query via Admin SDK

**To Query Firestore:**

I've created a Python script (`scripts/query_firestore.py`) that can query Firestore. It requires:

1. **Google Cloud Python SDK** - May need to install:
   ```bash
   pip install google-cloud-firestore
   ```

2. **Application Default Credentials** - Already set up (via gcloud auth)

**That's it!** No additional credentials or setup needed from you.

### Run Firestore Query:
```bash
# Install SDK if needed
pip install google-cloud-firestore

# Run query
python3 scripts/query_firestore.py
```

**No additional information needed from you** - uses existing authentication.

## Cloud SQL (PostgreSQL) Database

### What You Need to Provide: Minimal

**Current Setup:**
- ✅ Database instance exists: `scienceviddb-db`
- ✅ Database client scripts already configured
- ✅ Connection string in Secrets Manager

### Option 1: Use Existing Database Client (Recommended) ✅

**What's Needed:**
- ✅ Already configured in `scienceviddb` project
- ✅ Uses Secrets Manager for connection string
- ✅ Uses Application Default Credentials

**Just Run:**
```bash
cd scienceviddb
USE_SECRETS_MANAGER=true GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7 npm run db:state
```

**No additional credentials needed** - it's already set up!

### Option 2: Cloud SQL Proxy (If Option 1 Fails)

**What's Needed:**
- Database username/password (or create new user)
- Or use existing connection string from Secrets Manager

**Setup:**
```bash
# Download Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Get connection string from secrets
gcloud secrets versions access latest --secret="scienceviddb-database-url" --project=regal-scholar-453620-r7

# Run proxy (uses connection string or instance name)
./cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb-db --port=5432
```

**Only need:** Database username/password if using direct connection, or connection string from secrets.

### Option 3: Google Cloud Console

**What's Needed:**
- ✅ Just browser access (you already have this)
- Navigate to: https://console.cloud.google.com/sql/instances/scienceviddb-db

**No additional setup needed** - can query directly in browser.

## Summary: What You Need to Provide

### Firestore: **Nothing!** ✅
- Already authenticated
- Can query immediately
- Just need to install Python SDK: `pip install google-cloud-firestore`

### Cloud SQL: **Try Existing Script First** ✅

**Recommendation:** Use existing database client script (Option 1)
- No additional setup needed
- Already configured
- Just run: `npm run db:state` in scienceviddb directory

**If that fails:**
- Option A: Use Cloud Console (browser - no setup needed)
- Option B: Cloud SQL Proxy (need username/password or connection string)
- Option C: Connection string from Secrets Manager

**Most Likely:** Option 1 will work - the database client is already set up!

## Next Steps

### Immediate (No Setup Needed):
1. ✅ **Check Science Video Database** - Already visible (110 videos)
2. ✅ **Try Firestore Query** - Just install SDK and run script
3. ✅ **Try Cloud SQL Query** - Use existing database client script

### If Scripts Fail:
1. **Firestore:** Check Application Default Credentials
2. **Cloud SQL:** Get connection string from Secrets Manager, or use Cloud Console

**Bottom Line:** 
- **Firestore:** Install Python SDK, then ready to query
- **Cloud SQL:** Try existing script first (should work), if not, use Cloud Console or get connection details
