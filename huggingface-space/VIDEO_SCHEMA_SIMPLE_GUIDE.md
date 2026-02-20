# Simple Guide: Apply Video Database Schema

**Date:** January 10, 2025  
**Purpose:** Apply unified metadata schema to videos database  
**Database Type:** PostgreSQL (Cloud SQL) - NOT Firestore

## Quick Answer

**Your videos database uses PostgreSQL (Cloud SQL), not Firestore.**

**Difference:**
- **Firestore** = NoSQL (collections/documents) - No SQL statements
- **Cloud SQL (PostgreSQL)** = SQL database (tables/rows) - Uses SQL statements (ALTER TABLE)

**Why:** Your videos database needs structured queries (transcripts, channels, etc.), so it uses PostgreSQL.

## Easiest Method: Use Cloud Shell

Since you're already in Cloud Console, use **Cloud Shell** (terminal in browser):

**Step 1: Open Cloud Shell**
- In Cloud Console, click the **">_"** icon at the top right (Cloud Shell)
- Terminal opens in your browser

**Step 2: Connect to Database**
```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

**If it asks for password:**
```bash
# Set password first (if needed)
gcloud sql users set-password scienceviddb_user \
  --instance=scienceviddb-db \
  --project=regal-scholar-453620-r7
```

**Step 3: Get SQL File**
```bash
# Download the SQL file (or copy/paste from local file)
# The SQL is in: scienceviddb/docs/database_schema_enhancements.sql
```

**Step 4: Execute SQL**
- Once connected, paste the SQL statements
- Or copy the SQL file content and paste it

## What the SQL Does (Simple Explanation)

The SQL file adds **new columns** to your videos table:
- `related_papers` - To link videos to papers
- `related_processes` - To link videos to processes
- `keywords` - For better search
- `quality_score` - Quality metric
- `category` - Discipline category

**It's safe** - uses `IF NOT EXISTS` so it won't break existing data.

## Alternative: Check for Existing Migration Script

Your project has a migration script. Let's see if we can use it:

```bash
cd scienceviddb
npm run db:migrate
```

If this works, we can add the schema SQL to it. Otherwise, use Cloud Shell method above.

---

**Recommendation:** **Use Cloud Shell** - it's the simplest method and works from your browser!
