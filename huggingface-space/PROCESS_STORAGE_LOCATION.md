# Process Database Storage Location

**Date:** January 10, 2025  
**Purpose:** Document where process databases are stored (local vs GCS)

## Summary

**All processes are stored LOCALLY** (primary storage).  
**GCS contains backups/uploads** for some databases, but local files are the primary source.

## Current Storage Status

### ✅ Local Storage (Primary) - 314 Process Files

All process databases are stored locally in the `huggingface-space` directory:

1. **Biology-processes-database/** 
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/biology-processes-database/processes/`
   - Count: 52 processes
   - Size: 1.2 MB
   - Status: ✅ Local (primary)

2. **Chemistry-processes-database/**
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/chemistry-processes-database/processes/`
   - Count: 91 processes
   - Size: 3.0 MB
   - Status: ✅ Local (primary)

3. **Physics-processes-database/**
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/physics-processes-database/processes/`
   - Count: 21 processes
   - Size: 736 KB
   - Status: ✅ Local (primary)

4. **Mathematics-processes-database/**
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/mathematics-processes-database/processes/`
   - Count: 20 processes
   - Size: 704 KB
   - Status: ✅ Local (primary)

5. **GLMP-processes-database/** (NEW - Downloaded today)
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/glmp-processes-database/processes/`
   - Count: 109 processes
   - Size: 2.8 MB
   - Status: ✅ Local (downloaded from GCS)
   - Original GCS: `gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/processes/`

6. **Computer Science-processes-database/**
   - Location: `/home/gdubs/copernicus-web-public/huggingface-space/computer-science-processes-database/processes/`
   - Count: 21 processes
   - Size: 568 KB
   - Status: ✅ Local (primary)

**Total Local Processes:** 314 process files (including non-migrated files)  
**Total Migrated Processes:** 293 processes (with backups)

### 📦 Google Cloud Storage (GCS) - Backup/Archive

GCS contains backups/uploads for some databases:

1. **GLMP processes (original source):**
   - `gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/processes/`
   - Status: ✅ Source repository (109 processes)
   - Local copy: ✅ Downloaded to `glmp-processes-database/processes/`

2. **Biology-processes-database (uploaded):**
   - `gs://regal-scholar-453620-r7-podcast-storage/biology-processes-database/processes/`
   - Status: ✅ Backup/archive in GCS
   - Contains: Process files, metadata.json, database-table.html

3. **Chemistry-processes-database (uploaded):**
   - `gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/`
   - Status: ✅ Backup/archive in GCS
   - Contains: Process files, metadata.json, database-table.html

4. **Other discipline databases (may exist):**
   - Physics, Mathematics, Computer Science databases may also have GCS backups
   - Status: ⚠️ Check if uploads exist

5. **GLMP viewer and metadata:**
   - `gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/`
   - `gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/metadata.json`
   - Status: ✅ Web viewer files

## Storage Strategy

### Primary Storage: Local Files ✅

- ✅ All process JSON files stored locally
- ✅ Version controlled (git)
- ✅ Easy to edit and maintain
- ✅ Fast access for scripts
- ✅ Primary source for migrations and development

### Backup/Archive: Google Cloud Storage

- ✅ GLMP processes stored in GCS (original source)
- ✅ Biology/Chemistry processes uploaded to GCS (backups)
- ✅ Used for web viewer access (GLMP viewer, database tables)
- ✅ Serves as backup/repository
- ✅ Public access for web viewers

## Migration Status

All 293 migrated processes:
- ✅ All processes have local JSON files
- ✅ All processes backed up (`.json.backup` files created)
- ✅ All processes in unified schema format
- ✅ Cross-modal linking fields added

## Future Plan: GCS as Primary Source 📋

**Current Phase:** Local Development ✅
- Working locally while generating and modifying processes
- Easy to edit, version control, fast iteration
- Unified schema migration completed (293 processes)

**Future Phase:** GCS as Primary Source (in a few days)
- Upload all refined process files to GCS
- Make GCS the primary source repository
- Keep local copies for development/editing
- Sync strategy: Edit locally → Upload to GCS

**Upload Script:** `scripts/upload_all_processes_to_gcs.sh` (ready for use)

See `PROCESS_GCS_MIGRATION_PLAN.md` for detailed migration plan.

---

**Summary:** 
- **Current Primary Storage:** All 314 processes stored **locally** (development phase)
- **GCS Storage:** GLMP source + backups/uploads for Biology/Chemistry
- **Future Plan:** Upload all refined processes to GCS as primary source
- **Migration:** 293 processes migrated locally, with backups created
