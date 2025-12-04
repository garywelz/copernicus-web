# Canonical Filename Status - December 1, 2025

## Current Situation

The database endpoint **already includes ALL podcasts**, including those that don't have canonical filenames yet. However:

1. **Podcasts created BEFORE the code update** may still be using `job_id` (UUID) instead of canonical filenames like `ever-bio-250040`

2. **Podcasts created AFTER the code update** should already have canonical filenames

3. **The assignment script hasn't been run yet** - so old podcasts haven't been updated

## What You Should See

In the podcast database table, you should see:
- ✅ Podcasts with canonical filenames: `ever-bio-250040`, `ever-phys-250041`, etc.
- ⚠️ Podcasts with job_ids (UUIDs): `a1b2c3d4-e5f6-...`, etc.

If you're not seeing the podcasts you expect:
1. They might be there but using `job_id` instead of canonical filename
2. They might need canonical filenames assigned (run the assignment script)

## How to Check

You can check the current status by:

1. **View the database table** - look at the "Canonical Filename" column
2. **Run the check script** (I just created it):
   ```bash
   python3 check_database_status.py
   ```

## To Assign Canonical Filenames

To actually assign canonical filenames to podcasts that don't have them:

```bash
python3 assign_all_canonical.py
```

This will:
- Find all podcasts missing canonical filenames
- Generate proper canonical filenames (e.g., `ever-bio-250041`)
- Update Firestore records
- Update RSS feed if needed

After running this, refresh the database page and you should see the canonical filenames!

