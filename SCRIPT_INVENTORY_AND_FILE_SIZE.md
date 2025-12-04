# Script Inventory and File Size Constraints

## 📋 Available Scripts to Run

### **Scripts You Should Run to See Complete Picture**

#### **1. `find_all_missing_podcasts.py`** ✅ READY
**Purpose**: Find podcasts missing from database, search for specific ones

**What it does**:
- Fetches all podcasts from database endpoint
- Checks for podcasts missing canonical filenames
- Searches for specific podcasts (like "Parkinson's Disease")
- Shows summary counts

**Run**: `python3 find_all_missing_podcasts.py`

**Output**: 
- Database count
- Missing canonical filenames list
- Search results for "Parkinson"

---

#### **2. `check_database_status.py`** ✅ READY
**Purpose**: Check canonical filename status of all podcasts

**What it does**:
- Shows total podcasts in database
- Categorizes by canonical filename status
- Lists podcasts without canonical filenames

**Run**: `python3 check_database_status.py`

**Output**: Shows how many podcasts have/don't have canonical filenames

---

#### **3. `run_fix_all_issues.py`** ⚠️ REQUIRES CONFIRMATION
**Purpose**: Fix news podcasts and titles

**What it does**:
- Reverts 5 news podcasts back to `news-` format
- Removes "Copernicus AI: Frontiers of Science - " prefix from titles
- Updates Firestore and RSS feed

**Run**: `python3 run_fix_all_issues.py` (asks for confirmation)

---

## 🔍 Scripts Still Needed

### **A. Find ALL Podcasts (Complete Count Analysis)**
**What it should do**:
- Count ALL `podcast_jobs` entries directly from Firestore
- Count ALL `episodes` entries
- Compare with database endpoint count
- Identify the 3 missing podcasts (64 → 61)
- List podcasts using job IDs instead of canonical filenames

**Status**: ❌ Not created yet

---

### **B. Diagnose YouTube Audio Corruption**
**What it should do**:
- Find the 6 failed podcasts by title:
  1. "Quantum Computing Advances"
  2. "Silicon compounds"
  3. "Quantum Computing chip advances"
  4. "Prime Number Theory update"
  5. "New materials created using AI"
  6. "Matrix Multiplication advances"
- Check if audio files exist in GCS
- Verify audio file integrity
- Report which files are corrupt/missing

**Status**: ❌ Not created yet

---

### **C. Fix YouTube Audio Corruption**
**What it should do**:
- Regenerate audio for the 6 failed podcasts
- Update RSS feed with new audio URLs
- Verify fixes

**Status**: ❌ Not created yet

---

## ⚠️ File Size Constraint Issue

### **Current Status**
- **`cloud-run-backend/main.py`**: **8,166 lines** - VERY LARGE! ⚠️

### **Problems with Large Files**
1. **Slow Performance**: Takes longer to load/edit
2. **Hard to Navigate**: Difficult to find specific code
3. **Merge Conflicts**: More likely to conflict in Git
4. **Maintenance**: Harder to understand and maintain
5. **Deployment**: Slower deployments

### **Recommended Solutions**

#### **Option 1: Split by Domain** ⭐ RECOMMENDED
Break into logical modules:

```
cloud-run-backend/
├── main.py                    (~500 lines - FastAPI app setup only)
├── endpoints/
│   ├── __init__.py
│   ├── admin.py              (~1500 lines - all admin endpoints)
│   ├── subscriber.py         (~800 lines - subscriber endpoints)
│   ├── podcast.py            (~2000 lines - podcast generation)
│   ├── rss.py                (~1000 lines - RSS feed management)
│   └── health.py             (~200 lines - health checks)
├── services/
│   ├── __init__.py
│   ├── audio_service.py
│   ├── thumbnail_service.py
│   └── ...
└── utils/
    ├── __init__.py
    └── ...
```

**Benefits**:
- ✅ Clear organization
- ✅ Easier to navigate
- ✅ Better for collaboration
- ✅ Faster development

#### **Option 2: Split by Feature**
Organize by feature area instead.

#### **Option 3: Keep Main, Extract Large Functions**
Keep FastAPI app in main.py, extract complex functions to modules.

---

## 🎯 Recommended Next Steps

### **Phase 1: Get Complete Picture** (Do First)
1. Run `find_all_missing_podcasts.py` - see what's missing
2. Run `check_database_status.py` - see canonical filename status
3. Create script A - find ALL podcasts (count discrepancy analysis)

### **Phase 2: Fix Issues** (Then Do)
4. Create script B - diagnose YouTube audio corruption
5. Create script C - fix YouTube audio corruption
6. Run `run_fix_all_issues.py` - fix news podcasts and titles

### **Phase 3: Address File Size** (After Fixes)
7. Refactor `main.py` - split into modules (Option 1 recommended)

---

## 📊 Current File Size Statistics

- `main.py`: **8,166 lines** ⚠️
- Ideal size: **500-1,000 lines per file**
- Current is **8x too large**!

**Breaking it down**:
- ~500 lines: FastAPI app setup
- ~1,500 lines: Admin endpoints
- ~800 lines: Subscriber endpoints
- ~2,000 lines: Podcast generation
- ~1,000 lines: RSS feed management
- ~2,000 lines: Utilities/helpers
- ~366 lines: Other

---

## ✅ What I Recommend

1. **First**: Create scripts A, B, C to get complete picture and fix YouTube issues
2. **Then**: Refactor `main.py` into modules (Option 1)
3. **Timeline**: 
   - Scripts: ~1 hour
   - Refactoring: ~2-3 hours (careful to maintain functionality)

Would you like me to:
- **A**: Create scripts A, B, C first (get complete picture)?
- **B**: Start refactoring `main.py` now?
- **C**: Do both - create scripts, then refactor?

What's your preference?

