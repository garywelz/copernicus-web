# Video Database Schema Enhancement Guide

**Date:** January 10, 2025  
**Purpose:** Apply unified metadata schema enhancements to video database  
**Database:** PostgreSQL (Cloud SQL) - NOT Firestore

## Understanding the Difference

### Firestore vs Cloud SQL (PostgreSQL)

**Firestore (NoSQL Document Database):**
- NoSQL document database (like MongoDB)
- Collections and documents (JSON-like structure)
- Access via: Firestore SDK, gcloud CLI, Cloud Console
- Example: Used for some metadata storage

**Cloud SQL (PostgreSQL) - Videos Database:**
- **Relational SQL database** (like MySQL, PostgreSQL)
- Tables with rows and columns
- Access via: SQL queries, psql, Cloud Console SQL editor
- Example: Your **videos database** uses PostgreSQL in Cloud SQL
- **This is what needs schema changes**

### Why the Difference?

Your **Science Video Database** uses **PostgreSQL** (Cloud SQL) because:
- Videos have structured metadata (title, description, transcript segments, etc.)
- SQL is better for relational queries (channels → videos, transcripts, etc.)
- Better for full-text search, indexing, and complex queries

This is **different** from Firestore, which is a NoSQL document database.

## How to Apply Schema Changes

### Option 1: Cloud Console SQL Editor (Easiest)

**Step 1: Navigate to Database**
- You're already at: https://console.cloud.google.com/sql/instances/scienceviddb-db/overview?project=regal-scholar-453620-r7
- ✅ You're in the right place!

**Step 2: Open SQL Editor**
1. In the Cloud SQL instance page, look for a **"Query"** or **"SQL"** tab/button
2. Or look for **"Databases"** → Select your database → **"SQL"** tab
3. Or use the left sidebar: **"Databases"** → Click on database name → **"SQL"** or **"Query"**

**Alternative Path:**
- Click on **"Databases"** in the left sidebar or tabs
- Select the database (usually `scienceviddb` or `postgres`)
- Look for **"SQL"** or **"Query"** tab/button
- This opens the SQL query editor

**Step 3: Copy SQL from File**
1. Open the SQL file: `scienceviddb/docs/database_schema_enhancements.sql`
2. Copy all the SQL statements
3. Paste into the SQL editor in Cloud Console

**Step 4: Execute**
1. Click **"Run"** or **"Execute"** button
2. SQL statements will execute sequentially
3. Check for success messages or errors

### Option 2: Use Cloud Shell (Alternative)

**Step 1: Open Cloud Shell**
- In Cloud Console, click the **">_"** icon (Cloud Shell) at the top right
- This opens a terminal in your browser

**Step 2: Connect to Database**
- Use `gcloud sql connect` command
- Or use `psql` if Cloud SQL Proxy is available

**Step 3: Execute SQL**
- Copy SQL from file
- Paste into terminal
- Or use: `psql < database_schema_enhancements.sql`

### Option 3: Database Client Script (If Configured)

**If your database client supports migrations:**
```bash
cd scienceviddb
# If migration script exists
npm run db:migrate
# Or
npm run migrate
```

**Check if migration script exists:**
```bash
cd scienceviddb
npm run | grep migrate
```

## What the SQL File Does

The `database_schema_enhancements.sql` file:

1. **Adds new columns** to `videos` table:
   - `related_papers` (TEXT[] array)
   - `related_processes` (TEXT[] array)
   - `related_videos` (TEXT[] array)
   - `keywords` (TEXT[] array)
   - `entities` (JSONB array)
   - `quality_score` (DECIMAL)
   - `category` (VARCHAR)
   - `year` (VARCHAR)

2. **Creates indexes** for performance:
   - GIN indexes for arrays (related_papers, keywords)
   - Indexes for category and year

3. **Adds constraints**:
   - Category values must match schema enum
   - Quality score must be 0.0-1.0

4. **Creates triggers**:
   - Auto-populate category from disciplines
   - Auto-populate year from published_at

5. **Updates existing data**:
   - Populate category and year from existing fields

## Finding the SQL Editor in Cloud Console

The SQL editor location varies by Cloud Console version:

**Common Locations:**
1. **Main instance page:**
   - Look for tabs: "OVERVIEW" | "DATABASES" | "USERS" | "BACKUPS" | etc.
   - Click on **"DATABASES"** tab
   - Select your database
   - Look for **"SQL"** or **"QUERY"** tab

2. **Sidebar navigation:**
   - Look for "Databases" in left sidebar
   - Click to expand
   - Select database name
   - SQL editor should appear

3. **Alternative:**
   - Look for "Query insights" or "SQL insights" link
   - Or "Run a query" button
   - Or search for "SQL" in the page

**If you can't find it:**
- The SQL editor may require Cloud Shell
- Or may require enabling "Public IP" or "Authorized networks"
- Or may need to use `gcloud sql connect` command

## Alternative: Use Cloud SQL Proxy (Command Line)

If the SQL editor isn't accessible, use Cloud SQL Proxy:

**Step 1: Download Cloud SQL Proxy** (if not installed)
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
```

**Step 2: Run Proxy**
```bash
./cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb-db --port=5432 &
```

**Step 3: Connect with psql**
```bash
psql -h 127.0.0.1 -U USERNAME -d DATABASE_NAME
```

**Step 4: Execute SQL**
```sql
-- Copy/paste SQL from database_schema_enhancements.sql
-- Or use:
\i /path/to/database_schema_enhancements.sql
```

## Quick Check: What Database Type Is It?

**To confirm your videos database uses PostgreSQL:**
- The instance name: `scienceviddb-db` (Cloud SQL)
- The connection string uses PostgreSQL format
- The schema uses SQL DDL (CREATE TABLE, ALTER TABLE)

**Firestore:**
- Would be in "Firestore" section of Cloud Console
- Would use document/collection structure
- Would NOT use SQL

## Summary

**Your Videos Database:**
- ✅ Uses **PostgreSQL** (Cloud SQL)
- ✅ Needs **SQL schema changes** (ALTER TABLE statements)
- ⚠️ Requires **SQL editor** or **psql** to apply changes

**The SQL File:**
- Location: `scienceviddb/docs/database_schema_enhancements.sql`
- Contains: ALTER TABLE statements to add columns
- Safe to run: Uses `IF NOT EXISTS` clauses

**Next Steps:**
1. Find SQL editor in Cloud Console (DATABASES tab → SQL tab)
2. Or use Cloud SQL Proxy + psql
3. Copy/paste SQL from file
4. Execute

---

**Status:** ⚠️ SQL file ready, waiting for database access to apply  
**Question:** Can you see a "DATABASES" tab or "SQL" button in the Cloud Console?
