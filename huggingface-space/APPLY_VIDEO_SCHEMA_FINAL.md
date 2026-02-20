# Apply Video Database Schema - Final Instructions

**Date:** January 10, 2025  
**Database:** PostgreSQL (Cloud SQL) - NOT Firestore

## Quick Answer

**Your videos database uses PostgreSQL (SQL database), not Firestore (NoSQL).**

**Why:** PostgreSQL is better for structured data (transcripts, channels, relationships). Firestore is for document storage (collections/documents).

**You need to run SQL statements (ALTER TABLE) to add columns.**

## Easiest Method: Use Your Existing Migration Script ✅

Good news! I've created a migration script that uses your existing database client:

**Step 1: Run the migration script**
```bash
cd /home/gdubs/scienceviddb
npm run db:migrate:enhancements
```

**That's it!** The script will:
- Connect to your database (uses existing credentials)
- Read the SQL file (`docs/database_schema_enhancements.sql`)
- Execute all SQL statements
- Add the new columns to your videos table

**If it fails:**
- Check if database credentials are configured
- Make sure `USE_SECRETS_MANAGER=true` and `GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7`
- Check database connection

## Alternative: Cloud Shell (If Script Doesn't Work)

**Step 1: Open Cloud Shell**
- In Cloud Console, click the **">_"** icon at the top right (Cloud Shell)
- Terminal opens in your browser

**Step 2: Connect to Database**
```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

**Step 3: Execute SQL**
- Copy SQL from `scienceviddb/docs/database_schema_enhancements.sql`
- Paste into Cloud Shell
- Execute

## What Gets Added

The SQL adds these **columns** to your `videos` table:
- `related_papers` - To link videos to papers
- `related_processes` - To link videos to processes  
- `keywords` - For better search
- `quality_score` - Quality metric
- `category` - Discipline category
- `year` - Publication year
- Plus indexes and constraints

**It's safe** - uses `IF NOT EXISTS` so it won't break existing data.

---

**Recommendation:** **Try `npm run db:migrate:enhancements` first** - it's the easiest!
