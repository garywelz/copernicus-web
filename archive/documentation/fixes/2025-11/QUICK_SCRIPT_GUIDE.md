# Quick Script Guide - What to Run Now

## 🎯 Scripts You Can Run Right Now

### **1. Find Missing Podcasts** ✅
```bash
python3 find_all_missing_podcasts.py
```
**Shows**: Database count, missing canonical filenames, searches for "Parkinson"

---

### **2. Check Database Status** ✅
```bash
python3 check_database_status.py
```
**Shows**: Total podcasts, which have canonical filenames, which don't

---

### **3. Fix News & Titles** ⚠️ (Requires Confirmation)
```bash
python3 run_fix_all_issues.py
```
**Does**: Reverts 5 news podcasts, fixes titles with prefix

---

## ❌ Scripts Still Needed (I'll Create These)

### **A. Find ALL Podcasts** - To find the 3 missing (64→61)
### **B. Diagnose YouTube Audio** - Check the 6 failed podcasts  
### **C. Fix YouTube Audio** - Regenerate corrupt audio files

---

## ⚠️ File Size Issue

**`main.py`**: **8,166 lines** - TOO LARGE!

**Recommendation**: Split into modules after we fix the current issues.

---

## 📋 What I Recommend

**Run these scripts first to see complete picture**:
1. `python3 find_all_missing_podcasts.py`
2. `python3 check_database_status.py`

**Then I'll create**:
- Script A (find ALL podcasts)
- Script B (diagnose YouTube audio)
- Script C (fix YouTube audio)

**Then we'll address**:
- File size by splitting `main.py` into modules

Would you like to run the scripts first, or should I create scripts A, B, C now?

