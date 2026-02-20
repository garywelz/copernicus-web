# GLMP Duplicate Fix ✅

**Date:** December 2025  
**Issue:** 222 files found, but only 111 unique processes  
**Status:** Fixed - deduplication added to sync script

---

## Problem Identified

**User was correct!** There are exactly 111 unique GLMP processes, but they're stored in duplicate locations:

- **Total files:** 222
- **Unique processes:** 111
- **Duplicates:** 111 files (each process appears twice)

### Duplicate Pattern

Each process exists in two locations:
1. **Subdirectory version:** `glmp-v2/processes/bacillus/bacillus_biofilm_formation.json`
2. **Root version:** `glmp-v2/processes/bacillus_biofilm_formation.json`

Some processes even appear 3 times (e.g., in multiple subdirectories).

---

## Solution Implemented

Updated `sync_glmp_processes.py` to:

1. **Deduplicate by process ID** - Uses the `id` field from JSON files
2. **Prefer subdirectory versions** - When duplicates exist, prefer the subdirectory version
3. **Use most recent** - If multiple subdirectory versions, use the most recently updated
4. **Fallback to root** - If no subdirectory version, use root version

### Deduplication Logic

```python
# For each process ID:
# 1. If only one file → use it
# 2. If multiple files:
#    a. Prefer subdirectory versions (e.g., bacillus/process.json)
#    b. If multiple subdirs, prefer most recent
#    c. Otherwise, use root version
```

---

## Verification

**Before fix:**
- Files found: 222
- Would sync: 222 (with duplicates)

**After fix:**
- Files found: 222
- Unique processes: 111
- Will sync: 111 (deduplicated)

---

## Test Results

```bash
📋 Fetching GLMP processes from Google Cloud Storage...
🔍 Deduplicating processes (removing duplicates)...
   Found 222 files, 111 unique processes
   Removed 111 duplicate files
```

✅ **Deduplication working correctly!**

---

## Updated Sync Count

- **Previous count:** 222 processes (incorrect - included duplicates)
- **Correct count:** 111 unique processes ✅
- **Files to sync:** 111 (one per unique process)

---

## Next Steps

Now safe to sync all GLMP processes:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/sync_glmp_processes.py
```

This will sync exactly 111 unique processes (no duplicates).

---

**Status:** Duplicate issue fixed! Ready to sync 111 unique GLMP processes! ✅

