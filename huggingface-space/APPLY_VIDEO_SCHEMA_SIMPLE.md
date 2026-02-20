# Simple Guide: Apply Video Database Schema

**Date:** January 10, 2025  
**Database:** PostgreSQL (Cloud SQL) - NOT Firestore

## The Difference Explained

**Firestore (NoSQL):**
- Document database (collections/documents)
- No SQL statements
- Found in: Cloud Console → Firestore section

**Cloud SQL - PostgreSQL (Your Videos Database):**
- SQL database (tables/rows)
- Uses SQL statements (ALTER TABLE, etc.)
- Found in: Cloud Console → SQL section → `scienceviddb-db`
- **This is what needs schema changes**

**Why different?** Your videos database uses PostgreSQL because it needs structured queries (transcripts, channels, relationships). Firestore wouldn't be as efficient.

## Easiest Method: Use Cloud Shell ✅

Since you're already in Cloud Console, use **Cloud Shell** (terminal in your browser):

### Step 1: Open Cloud Shell

1. In Cloud Console (where you are now)
2. Look for the **">_"** icon at the **top right** (Cloud Shell icon)
3. Click it - terminal opens in your browser

### Step 2: Connect to Database

In Cloud Shell, type:
```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

**If it asks for a password:**
- Enter password (if you know it)
- Or set one first (see below)

**If you need to set password:**
```bash
gcloud sql users set-password scienceviddb_user \
  --instance=scienceviddb-db \
  --project=regal-scholar-453620-r7
```

### Step 3: Copy/Paste SQL

**Option A: Download SQL file in Cloud Shell**
```bash
# In Cloud Shell (before connecting), download the SQL file
curl -o schema.sql https://raw.githubusercontent.com/YOUR_REPO/path/to/database_schema_enhancements.sql
# Or create it directly:
cat > schema.sql << 'EOF'
[paste SQL content here]
EOF
```

**Option B: Copy from local file**
1. Open `scienceviddb/docs/database_schema_enhancements.sql` on your local machine
2. Copy all the SQL content
3. In Cloud Shell (after connecting), paste the SQL
4. Press Enter to execute

### Step 4: Execute

Once connected, you'll see a `postgres=>` prompt. Paste the SQL statements and press Enter.

**Or if you created a file:**
```sql
\i schema.sql
```

## What Gets Added

The SQL adds these **columns** to your `videos` table:
- `related_papers` - Link videos to papers
- `related_processes` - Link videos to processes  
- `keywords` - For search
- `quality_score` - Quality metric
- `category` - Discipline category
- `year` - Publication year

**It's safe** - uses `IF NOT EXISTS` so it won't break existing data.

## Alternative: Find SQL Editor in Cloud Console

If Cloud Shell doesn't work, look for SQL editor:

1. In Cloud SQL instance page (where you are now)
2. Look for tabs: **"OVERVIEW"** | **"DATABASES"** | **"USERS"** | etc.
3. Click **"DATABASES"** tab
4. Select your database (e.g., `scienceviddb`)
5. Look for **"SQL"** or **"QUERY"** tab/button
6. Paste SQL and execute

---

**Recommendation:** **Use Cloud Shell** (">_" icon) - it's the simplest method!
