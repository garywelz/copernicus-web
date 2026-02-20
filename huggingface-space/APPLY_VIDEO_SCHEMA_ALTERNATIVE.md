# Alternative: Apply Video Schema via Database Client

**Date:** January 10, 2025  
**Purpose:** Apply video database schema using existing database client (if available)

## Check if Database Client Can Apply Schema

Your `scienceviddb` project has a database client package. Let's check if it supports running SQL files directly.

**Option: Use Database Client Script**

If the database client can execute SQL files, we can create a simple script:

```bash
cd scienceviddb
# Create script to apply schema
node -e "
const { query } = require('./packages/db/src/client');
const fs = require('fs');
const sql = fs.readFileSync('./docs/database_schema_enhancements.sql', 'utf8');
// Split by semicolons and execute each statement
// (would need proper SQL parsing)
"
```

**However**, executing complex SQL files requires proper SQL parsing, which may not be available.

## Recommended: Use Cloud Console SQL Editor

Since the SQL file contains multiple statements (ALTER TABLE, CREATE INDEX, CREATE FUNCTION, CREATE TRIGGER, etc.), the easiest approach is:

1. **Find SQL Editor in Cloud Console:**
   - In the Cloud SQL instance page (where you are now)
   - Look for tabs: "OVERVIEW", "DATABASES", "USERS", "BACKUPS", etc.
   - Click **"DATABASES"** tab
   - Select your database (e.g., `scienceviddb` or `postgres`)
   - Look for **"SQL"** or **"QUERY"** tab/button

2. **If SQL Editor Not Available:**
   - Use Cloud Shell (click `>_` icon in Cloud Console)
   - Or use Cloud SQL Proxy + psql (as described in guide)

## What the Schema File Does (Non-Technical Summary)

The SQL file adds new **columns** to your videos table to support:
- Linking videos to papers (`related_papers`)
- Linking videos to processes (`related_processes`)
- Keywords for search (`keywords`)
- Quality scores (`quality_score`)
- Categories (`category`, `year`)

It's **safe to run** - uses `IF NOT EXISTS` so it won't break existing data.

---

**Bottom Line:** 
- Your videos database uses **PostgreSQL** (SQL database), not Firestore
- You need to run **SQL statements** (ALTER TABLE) to add columns
- **Easiest:** Find SQL editor in Cloud Console (DATABASES tab → SQL)
- **Alternative:** Use Cloud SQL Proxy + psql command line
