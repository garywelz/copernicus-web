# When and Where to Paste the SQL - Step by Step

**Date:** January 10, 2025  
**File to paste:** `scienceviddb/docs/database_schema_enhancements.sql`

## The Problem

You tried `gcloud sql connect` but it needs an interactive password prompt. We need a different approach.

## Solution: Use the Password Directly

I found the password in your code: `SciVidDB-Test-2024`

## Step-by-Step: When to Paste SQL

### Step 1: Connect Using Password

Run this command (replace with actual password if different):

```bash
PGPASSWORD='SciVidDB-Test-2024' psql -h 34.31.235.165 -U scienceviddb_user -d scienceviddb
```

**Note:** The IP address `34.31.235.165` is from your connection attempt.

### Step 2: Wait for Connection

You should see:
```
psql (14.x)
Type "help" for help.

scienceviddb=>
```

**THIS IS WHEN YOU PASTE THE SQL!** ✅

### Step 3: Paste the SQL (RIGHT HERE!)

1. You should see the prompt: `scienceviddb=>`
2. **NOW** open the file: `scienceviddb/docs/database_schema_enhancements.sql`
3. **Copy ALL the SQL** (all 150 lines)
4. **Paste it** into the terminal (after the `scienceviddb=>` prompt)
5. Press Enter

**Example:**
```
scienceviddb=> -- Science Video Database - Schema Enhancements...
scienceviddb=> ALTER TABLE videos 
scienceviddb-> ADD COLUMN IF NOT EXISTS related_papers TEXT[] DEFAULT '{}',
scienceviddb-> ...
```

PostgreSQL will show `=>` for complete statements and `->` for continuation lines.

### Step 4: Wait for Completion

After pasting, you'll see:
- Messages like "ALTER TABLE" (for each statement)
- "CREATE INDEX" messages
- "CREATE FUNCTION" messages
- etc.

When it's done, you'll see the prompt again: `scienceviddb=>`

### Step 5: Verify (Optional)

Check if columns were added:

```sql
\d videos
```

You should see the new columns in the output.

### Step 6: Exit

```sql
\q
```

## Alternative: Use SQL File Directly

If pasting doesn't work, you can use the file:

```sql
\i /home/gdubs/scienceviddb/docs/database_schema_enhancements.sql
```

This reads and executes the SQL file directly.

## If Password Doesn't Work

Try getting the actual password:

```bash
gcloud secrets versions access latest --secret="cloud-sql-password" --project=regal-scholar-453620-r7
```

Then use that password instead.

## Summary

**When to paste:** ✅ **AFTER** you see `scienceviddb=>` prompt  
**Where to paste:** ✅ **In the same terminal** where you ran `psql`  
**What to paste:** ✅ **ALL the SQL** from `database_schema_enhancements.sql`

---

**Quick Command:**
```bash
PGPASSWORD='SciVidDB-Test-2024' psql -h 34.31.235.165 -U scienceviddb_user -d scienceviddb
```

Then paste the SQL when you see the prompt!
