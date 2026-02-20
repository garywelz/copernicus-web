# Process Database GCS Migration Plan

**Date:** January 10, 2025  
**Status:** 📋 Planned - Local development phase  
**Target:** Upload all processes to GCS as primary source

## Strategy

### Current Phase: Local Development ✅

**Status:** Working locally while generating and modifying processes
- ✅ All processes stored locally for easy editing
- ✅ Version controlled (git)
- ✅ Fast iteration and development
- ✅ Unified schema migration completed (293 processes)

### Future Phase: GCS as Primary Source 📋

**Timeline:** In a few days (after refinement complete)

**Plan:**
1. Upload all refined process files to GCS
2. Make GCS the primary source repository
3. Keep local copies for development/editing
4. Sync strategy: Edit locally → Upload to GCS

## Target GCS Structure

### Proposed GCS Organization

```
gs://regal-scholar-453620-r7-podcast-storage/
├── processes/
│   ├── biology/
│   │   └── *.json (52 processes)
│   ├── chemistry/
│   │   └── *.json (91 processes)
│   ├── physics/
│   │   └── *.json (21 processes)
│   ├── mathematics/
│   │   └── *.json (20 processes)
│   ├── glmp/
│   │   └── *.json (109 processes)
│   └── computer_science/
│       └── *.json (21 processes)
├── processes-metadata/
│   ├── metadata.json (collection metadata)
│   └── database-table.html (viewer)
└── glmp-v2/ (existing GLMP structure - keep as is)
```

**OR** maintain existing structure:

```
gs://regal-scholar-453620-r7-podcast-storage/
├── biology-processes-database/
│   └── processes/ (52 processes)
├── chemistry-processes-database/
│   └── processes/ (91 processes)
├── physics-processes-database/
│   └── processes/ (21 processes)
├── mathematics-processes-database/
│   └── processes/ (20 processes)
├── glmp-processes-database/
│   └── processes/ (109 processes)
└── computer-science-processes-database/
    └── processes/ (21 processes)
```

## Upload Checklist

### Pre-Upload

- [ ] All processes migrated to unified schema ✅ (DONE)
- [ ] All processes validated ✅ (DONE)
- [ ] All processes refined and finalized
- [ ] Backup local files
- [ ] Review GCS structure/organization

### Upload Process

- [ ] Upload biology processes (52 files)
- [ ] Upload chemistry processes (91 files)
- [ ] Upload physics processes (21 files)
- [ ] Upload mathematics processes (20 files)
- [ ] Upload GLMP processes (109 files) - or keep in glmp-v2/
- [ ] Upload computer science processes (21 files)
- [ ] Upload metadata files
- [ ] Upload database table HTML files
- [ ] Set public read permissions
- [ ] Verify uploads

### Post-Upload

- [ ] Update documentation
- [ ] Update web viewers to use GCS
- [ ] Test GCS access
- [ ] Create sync strategy for future edits

## Upload Script (Ready for Use)

See `scripts/upload_all_processes_to_gcs.sh` (to be created)

## Benefits of GCS as Primary Source

1. ✅ **Centralized storage** - Single source of truth
2. ✅ **Public access** - Web viewers can access directly
3. ✅ **Backup** - Cloud storage redundancy
4. ✅ **Versioning** - GCS object versioning
5. ✅ **Scalability** - Easy to add more processes
6. ✅ **Integration** - Works with web viewers, APIs

## Local Development Workflow (Future)

1. **Edit locally** - Make changes to local files
2. **Test locally** - Validate changes
3. **Upload to GCS** - Sync changes to primary source
4. **Update viewers** - Web viewers automatically use GCS

---

**Status:** 📋 Plan documented - Ready for upload in a few days after refinement
