# Apply Video Schema Using Cloud SQL Proxy

**Date:** January 10, 2025  
**Method:** Cloud SQL Proxy (handles authentication automatically)

## Why Cloud SQL Proxy?

The `gcloud sql connect` command requires an interactive password prompt, which doesn't work well in this terminal. **Cloud SQL Proxy** handles authentication automatically using your Google Cloud credentials.

## Step-by-Step

### Step 1: Download Cloud SQL Proxy (if not installed)

```bash
# Check if already installed
which cloud-sql-proxy

# If not found, download it
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
```

### Step 2: Start Cloud SQL Proxy (in background)

```bash
./cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb-db --port=5432 &
```

**Note:** This runs in the background. Keep this terminal open or run in a separate terminal.

### Step 3: Get Database Password

We need the database password. Let's try to get it from Secrets Manager:

```bash
# Try to get password from Secrets Manager
gcloud secrets versions access latest --secret="scienceviddb-db-password" --project=regal-scholar-453620-r7
```

**Or if password is stored elsewhere:**
- Check your environment variables
- Check your local config files
- Or reset the password (see below)

**If you need to reset the password:**
```bash
gcloud sql users set-password scienceviddb_user \
  --instance=scienceviddb-db \
  --project=regal-scholar-453620-r7
```

### Step 4: Connect to Database

```bash
PGPASSWORD='YOUR_PASSWORD_HERE' psql -h 127.0.0.1 -U scienceviddb_user -d scienceviddb
```

**Or use .pgpass file (more secure):**
```bash
# Create .pgpass file (one-time setup)
echo "127.0.0.1:5432:scienceviddb:scienceviddb_user:YOUR_PASSWORD" > ~/.pgpass
chmod 600 ~/.pgpass

# Then connect without password
psql -h 127.0.0.1 -U scienceviddb_user -d scienceviddb
```

### Step 5: Paste SQL (THIS IS WHEN YOU PASTE IT!)

Once connected, you'll see: `scienceviddb=>`

**Now paste the SQL:**
1. Open `scienceviddb/docs/database_schema_enhancements.sql`
2. Copy ALL the SQL (all 150 lines)
3. Paste it into the terminal (after the `scienceviddb=>` prompt)
4. Press Enter
5. Wait for execution to complete

**Or use SQL file:**
```sql
\i /home/gdubs/scienceviddb/docs/database_schema_enhancements.sql
```

### Step 6: Verify

After execution, check if columns were added:

```sql
\d videos
```

You should see the new columns in the output.

### Step 7: Exit

```sql
\q
```

This exits the database connection.

---

## Alternative: Use Cloud Shell in Browser (Easier!)

If Cloud SQL Proxy is complicated, use **Cloud Shell in your browser**:

1. Go to Cloud Console
2. Click **">_"** icon (Cloud Shell) at top right
3. Run: `gcloud sql connect scienceviddb-db --user=scienceviddb_user --database=scienceviddb`
4. Enter password when prompted
5. Paste SQL
6. Done!

**Cloud Shell supports interactive password prompts**, so it's easier than local terminal.

---

## Summary

**When to paste SQL:**
- ✅ **AFTER** you're connected (you see `scienceviddb=>` prompt)
- ✅ Paste ALL the SQL from `database_schema_enhancements.sql`
- ✅ Press Enter to execute

**Where:**
- In the terminal where you ran `psql` command
- After the database prompt (`scienceviddb=>`)
