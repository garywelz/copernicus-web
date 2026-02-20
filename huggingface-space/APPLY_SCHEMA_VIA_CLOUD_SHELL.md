# Apply Video Schema via Cloud Shell (Easiest Method)

**Date:** January 10, 2025  
**Purpose:** Apply database schema using Cloud Shell (no local setup needed)

## Why Cloud Shell?

If you can't find the SQL editor in Cloud Console, **Cloud Shell** is the easiest alternative:
- Opens in your browser (no installation needed)
- Already authenticated with your Google Cloud account
- Can connect directly to Cloud SQL
- Can execute SQL statements

## Step-by-Step Instructions

### Step 1: Open Cloud Shell

1. In Cloud Console (where you are now)
2. Look for the **">_"** icon at the top right (Cloud Shell icon)
3. Click it to open Cloud Shell
4. This opens a terminal in your browser

### Step 2: Connect to Database

In Cloud Shell, run:

```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

**Note:** If it asks for a password, you may need to:
- Set a password first (if not set)
- Or use the connection string from Secrets Manager

**Alternative (if password not set):**
```bash
# Set password first
gcloud sql users set-password scienceviddb_user \
  --instance=scienceviddb-db \
  --project=regal-scholar-453620-r7
```

Then connect:
```bash
gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb
```

### Step 3: Download SQL File

In Cloud Shell, you can:

**Option A: Create SQL file in Cloud Shell**
```bash
# Create the SQL file directly
cat > /tmp/schema.sql << 'EOF'
-- Copy/paste SQL from database_schema_enhancements.sql
-- (copy the entire file content)
EOF
```

**Option B: Upload SQL file from local**
```bash
# Use Cloud Shell file upload (click upload icon)
# Or use gcloud to copy from local if accessible
```

**Option C: Copy SQL directly**
- Open `scienceviddb/docs/database_schema_enhancements.sql` locally
- Copy all the SQL
- Paste into Cloud Shell after connecting

### Step 4: Execute SQL

Once connected to database in Cloud Shell:

```sql
-- Paste SQL from database_schema_enhancements.sql
-- Or if you created a file:
\i /tmp/schema.sql
```

Or just paste the SQL statements one by one, or all at once.

## What If Cloud SQL Connect Doesn't Work?

**If `gcloud sql connect` fails:**

1. **Check if Public IP is enabled:**
   - In Cloud SQL instance page
   - Go to "CONNECTIONS" tab
   - Check if "Public IP" is enabled
   - If not, enable it (may need authorized networks)

2. **Use Cloud SQL Proxy instead:**
   ```bash
   # Download proxy
   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
   chmod +x cloud-sql-proxy
   
   # Run proxy in background
   ./cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb-db --port=5432 &
   
   # Connect via psql
   psql -h 127.0.0.1 -U scienceviddb_user -d scienceviddb
   ```

## Summary

**Easiest Method:**
1. Open Cloud Shell (">_" icon in Cloud Console)
2. Run: `gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb`
3. Copy/paste SQL from `database_schema_enhancements.sql`
4. Execute

**This avoids:**
- Finding SQL editor (may not be available)
- Installing Cloud SQL Proxy locally
- Complex setup

---

**Status:** ✅ Cloud Shell is the easiest method - try this first!
