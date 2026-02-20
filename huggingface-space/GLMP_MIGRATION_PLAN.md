# GLMP Database Migration Plan

**Date:** January 10, 2025  
**Status:** ❌ GLMP was NOT included in the process migration  
**Action:** Download from GCS and migrate to unified schema

## Current Status

**GLMP Database:**
- **Location:** Google Cloud Storage (`gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/`)
- **Content:** 50+ biological processes (biochemical/molecular level)
- **Format:** JSON files
- **Status:** ❌ Not migrated to unified schema

**What Was Migrated (184 processes):**
- ✅ Biology-processes-database: 52 processes
- ✅ Chemistry-processes-database: 91 processes
- ✅ Physics-processes-database: 21 processes
- ✅ Mathematics-processes-database: 20 processes

## Why GLMP Wasn't Included

1. **GLMP is stored in Google Cloud Storage**, not in local directories
2. **Migration script only migrated local directories**
3. **No local GLMP processes directory** exists
4. **GLMP needs to be downloaded first** before migration

## Migration Plan

### Step 1: Download GLMP Processes from GCS

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space

# Create GLMP processes directory
mkdir -p glmp-processes-database/processes

# Download all JSON files from GCS
gsutil -m cp gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/*.json glmp-processes-database/processes/
```

### Step 2: Run Migration Script

```bash
# Run migration on GLMP processes
python3 scripts/processes/migrate_processes_to_unified_schema.py glmp-processes-database/processes/ --backup
```

**Note:** The migration script already has code to detect GLMP processes:
```python
if "glmp" in process.get("id", "").lower() or "glmp" in process.get("subcategory", "").lower():
    process["source"] = "glmp"
```

### Step 3: Validate GLMP Processes

```bash
# Validate migrated GLMP processes
python3 scripts/processes/validate_process_metadata.py glmp-processes-database/processes/ --threshold 0.85
```

### Step 4: Update Collection Status

After migration, update:
- Total process count (add GLMP processes)
- Collection status documents
- Migration completion status

## Expected Results

- **~50+ GLMP processes** migrated to unified schema
- **Cross-modal linking fields** added (`related_papers[]`, `related_videos[]`, `related_podcasts[]`)
- **Required fields** added (`source: "glmp"`, `acquired_date`)
- **All processes validated** (quality score >= 85%)

## Integration with Existing Processes

**GLMP processes are distinct from biology-processes-database:**
- **GLMP:** Biochemical/molecular processes (DNA replication, transcription, metabolic pathways)
- **Biology-processes-database:** Organismal/ecological processes (endocrine signaling, nervous system signaling)

Both will be in unified schema format and can be linked cross-modally.

---

**Next Step:** Would you like me to download GLMP from GCS and migrate it now?
