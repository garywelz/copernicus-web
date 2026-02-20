# Step-by-Step: Apply Video Schema via Cloud Shell

**Date:** January 10, 2025  
**Purpose:** Apply unified metadata schema to videos database  
**Method:** Cloud Shell (easiest - no local setup)

## Why Cloud Shell?

- ✅ Opens in your browser (no installation)
- ✅ Already authenticated with Google Cloud
- ✅ Can connect directly to Cloud SQL
- ✅ No local database setup needed

## Steps

### Step 1: Open Cloud Shell

1. You're in Cloud Console at: https://console.cloud.google.com/sql/instances/scienceviddb-db/overview
2. Look for the **">_"** icon at the **top right** of the Cloud Console
3. Click it - Cloud Shell opens in your browser (terminal window)

### Step 2: Create SQL File in Cloud Shell

In Cloud Shell, create the SQL file:

```bash
cat > schema_enhancements.sql << 'EOF'
```

Then, **open the SQL file locally** (`scienceviddb/docs/database_schema_enhancements.sql`) and **copy all its content**, then paste it into Cloud Shell, then type:

```bash
EOF
```

**Or simpler:** Just copy/paste the SQL directly after connecting (Step 3).

### Step 3: Connect to Database

In Cloud Shell, run:

```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

**If it asks for password:**
- Type the password (if you know it)
- Or press Enter if no password set

**If connection fails:**
- Check if Public IP is enabled (Cloud SQL instance → Connections tab)
- Or use Cloud SQL Proxy (more complex)

### Step 4: Execute SQL

Once connected, you'll see: `postgres=>`

**Option A: Paste SQL directly**
1. Copy all SQL from `database_schema_enhancements.sql`
2. Paste into Cloud Shell (right-click → Paste, or Ctrl+Shift+V)
3. Press Enter
4. SQL executes line by line

**Option B: Use SQL file (if created)**
```sql
\i schema_enhancements.sql
```

### Step 5: Verify

After execution, you should see:
- Success messages for each statement
- Or "already exists" messages (which is fine)

**Check if columns were added:**
```sql
\d videos
```

You should see the new columns:
- `related_papers`
- `related_processes`
- `keywords`
- `quality_score`
- `category`
- `year`
- etc.

### Step 6: Exit

```sql
\q
```

This exits the database connection.

---

## Summary

**In Cloud Console:**
1. Click **">_"** icon (Cloud Shell) at top right
2. Run: `gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb`
3. Paste SQL from `database_schema_enhancements.sql`
4. Press Enter
5. Done!

**That's it!** ✅
