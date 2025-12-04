# Available Scripts and File Size Constraints

## 📋 Scripts You Can Run

### **1. Find Missing Podcasts** ✅ Ready to Run
**Script**: `find_all_missing_podcasts.py`

**What it does**:
- Fetches all podcasts from the database endpoint
- Checks for podcasts missing canonical filenames
- Searches for specific podcasts (like "Parkinson's Disease")
- Shows summary counts

**Run it**:
```bash
cd /home/gdubs/copernicus-web-public
python3 find_all_missing_podcasts.py
```

**Output**: Shows database count, missing canonical filenames, and searches for specific podcasts.

---

### **2. Fix All Issues (News + Titles)** ⚠️ Requires Confirmation
**Script**: `run_fix_all_issues.py`

**What it does**:
- Reverts 5 news podcasts from `ever-` format back to `news-` format
- Fixes podcast titles to remove "Copernicus AI: Frontiers of Science - " prefix
- Updates Firestore and RSS feed

**Run it**:
```bash
cd /home/gdubs/copernicus-web-public
python3 run_fix_all_issues.py
```

**Note**: This will ask for confirmation before making changes.

---

### **3. Check Database Status**
**Script**: `check_database_status.py`

**What it does**: (Need to check what this does)

**Run it**:
```bash
python3 check_database_status.py
```

---

### **4. List Missing Canonical Filenames**
**Script**: `list_missing_canonical.py`

**What it does**: Lists all podcasts without canonical filenames

**Run it**:
```bash
python3 list_missing_canonical.py
```

---

### **5. Assign Canonical Filenames**
**Script**: `assign_all_canonical.py` or `assign_canonical_filenames.py`

**What it does**: Assigns canonical filenames to podcasts missing them

**Run it**:
```bash
python3 assign_all_canonical.py
```

---

## 🔍 Scripts to Create (Still Needed)

### **A. Find ALL Podcasts (Complete Count)**
**Purpose**: Find the 3 missing podcasts (64 → 61 discrepancy)

**What it should do**:
- Count ALL podcast_jobs entries directly from Firestore
- Count ALL episodes entries
- Compare with database count
- List any podcasts not in the database
- Show podcasts using job IDs instead of canonical filenames

### **B. Diagnose YouTube Audio Corruption**
**Purpose**: Check the 6 failed podcasts

**What it should do**:
- Find podcasts by title:
  - "Quantum Computing Advances"
  - "Silicon compounds"
  - "Quantum Computing chip advances"
  - "Prime Number Theory update"
  - "New materials created using AI"
  - "Matrix Multiplication advances"
- Check if audio files exist in GCS
- Verify audio file integrity (download and check)
- Report which files are corrupt or missing

### **C. Fix YouTube Audio Corruption**
**Purpose**: Regenerate corrupt audio files

**What it should do**:
- Regenerate audio for the 6 failed podcasts
- Update RSS feed with new audio URLs
- Verify fixes

---

## 📊 File Size Constraints

### **Current Status**
- `cloud-run-backend/main.py`: **8,166 lines** ⚠️ Very Large

### **Issues with Large Files**
1. **Performance**: Slower to load/edit
2. **Maintenance**: Harder to navigate and understand
3. **Deployment**: Slower deployments
4. **Merge Conflicts**: More likely to have conflicts

### **Recommended Solutions**

#### **Option 1: Split by Domain** (Recommended)
Break `main.py` into logical modules:

```
cloud-run-backend/
├── main.py (core FastAPI app setup, ~500 lines)
├── endpoints/
│   ├── __init__.py
│   ├── admin.py (admin endpoints)
│   ├── subscriber.py (subscriber endpoints)
│   ├── podcast.py (podcast generation)
│   ├── rss.py (RSS feed management)
│   └── health.py (health checks)
├── services/
│   ├── __init__.py
│   ├── audio_service.py
│   ├── thumbnail_service.py
│   └── ...
└── utils/
    ├── __init__.py
    └── ...
```

#### **Option 2: Split by Feature**
```
cloud-run-backend/
├── main.py
├── admin/
│   ├── __init__.py
│   └── routes.py
├── podcast/
│   ├── __init__.py
│   ├── generation.py
│   └── management.py
└── ...
```

#### **Option 3: Keep Main, Extract Large Functions**
Move large functions to separate modules:
- Keep FastAPI app in `main.py`
- Move complex endpoints to `endpoints/` modules
- Move utility functions to `utils/` modules

### **Recommended Approach**

I recommend **Option 1 (Split by Domain)** because:
- ✅ Clear organization
- ✅ Easier to maintain
- ✅ Better for team collaboration
- ✅ Faster development
- ✅ Easier to test

Would you like me to:
1. Create the missing scripts first (A, B, C above)?
2. Then refactor `main.py` to split into modules?
3. Or do both in parallel?

---

## 🎯 Next Steps

1. **Run `find_all_missing_podcasts.py`** to see current state
2. **Create scripts A, B, C** to find missing podcasts and diagnose YouTube issues
3. **Address file size** by splitting `main.py` into modules

What would you like to do first?

