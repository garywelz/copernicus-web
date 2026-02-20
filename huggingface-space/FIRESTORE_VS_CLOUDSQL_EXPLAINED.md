# Firestore vs Cloud SQL Explained

**Date:** January 10, 2025  
**Purpose:** Clarify the difference between Firestore and Cloud SQL (PostgreSQL)

## The Difference

### Firestore (NoSQL Document Database)

**What it is:**
- **NoSQL** document database (like MongoDB)
- Stores data as **collections** and **documents** (JSON-like)
- Access via: Firestore SDK, gcloud CLI, Cloud Console
- **Example structure:**
  ```json
  {
    "collection": "videos",
    "documents": [
      {
        "id": "video1",
        "title": "Video Title",
        "description": "..."
      }
    ]
  }
  ```

**Where to find it:**
- Cloud Console → **Firestore** section
- Not in SQL instances

**How to query:**
- Firestore queries (no SQL)
- Document/collection API
- No ALTER TABLE statements

### Cloud SQL - PostgreSQL (Your Videos Database)

**What it is:**
- **Relational SQL database** (PostgreSQL)
- Stores data in **tables** with **rows** and **columns**
- Access via: SQL queries, psql, Cloud Console SQL editor
- **Example structure:**
  ```sql
  CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    ...
  );
  ```

**Where to find it:**
- Cloud Console → **SQL** section → Instances
- Your instance: `scienceviddb-db`
- **This is where you are now!**

**How to query:**
- SQL queries (SELECT, INSERT, UPDATE, ALTER TABLE, etc.)
- Standard SQL syntax
- **This is why we need SQL statements (ALTER TABLE)**

## Why Your Videos Database Uses PostgreSQL

Your **Science Video Database** uses **PostgreSQL** (Cloud SQL) because:
- Videos have **structured metadata** (title, description, transcript segments, etc.)
- **SQL is better** for relational queries (channels → videos, transcripts, etc.)
- Better for **full-text search**, **indexing**, and **complex queries**
- Better for **transcript segments** with timestamps
- Better for **cross-modal linking** with structured arrays

## Finding the SQL Editor

Since you're using **PostgreSQL** (Cloud SQL), you need to run **SQL statements** (ALTER TABLE).

**In Cloud Console SQL Instance Page:**

**Step 1: Look for "Databases" tab or link**
- You're currently on the **"OVERVIEW"** tab
- Look for tabs at the top: "OVERVIEW" | "DATABASES" | "USERS" | "BACKUPS" | etc.
- Click on **"DATABASES"** tab

**Step 2: Select your database**
- You'll see a list of databases (e.g., `scienceviddb`, `postgres`)
- Click on your database name (usually `scienceviddb`)

**Step 3: Look for SQL editor**
- After selecting database, look for:
  - **"SQL"** tab/button
  - **"Query"** tab/button
  - **"Run a query"** button
  - Or a text area where you can type SQL

**If you don't see SQL editor:**
- Some Cloud SQL instances don't have web-based SQL editor
- Alternative: Use Cloud Shell (see below)
- Alternative: Use Cloud SQL Proxy + psql (see guide)

## Alternative: Use Your Existing Database Client

Your `scienceviddb` project has a database client with a `migrate` script. Let's check if we can use it to apply the schema:

**Check existing migrate script:**
```bash
cd scienceviddb
npm run db:migrate
```

If this exists and works, we can add the schema SQL to the migration system.

---

**Bottom Line:**
- **Your videos database = PostgreSQL (Cloud SQL)** - uses SQL (ALTER TABLE)
- **Firestore = NoSQL** - uses collections/documents (no SQL)
- **You need SQL editor** to run ALTER TABLE statements
- **Location:** DATABASES tab → Select database → SQL tab
