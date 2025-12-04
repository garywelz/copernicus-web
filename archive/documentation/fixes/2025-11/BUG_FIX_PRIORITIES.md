# Bug Fix Priorities

## 🔍 **Issues Identified**

### **1. Missing Podcasts (High Priority)**
- **Expected**: 64 podcasts
- **Found**: 61 podcasts
- **Missing**: **3 podcasts**

**Action**: Find where these 3 podcasts went

---

### **2. Missing Audio File (High Priority)**
- **Podcast**: "Quantum Computing Advances" (`ever-phys-250042`)
- **Issue**: No audio URL in database
- **Impact**: YouTube ingestion failure

**Action**: Regenerate or locate audio file

---

### **3. Podcasts Not Found in Database (High Priority)**
YouTube reported these as failing, but they're not in our database:
1. "Quantum Computing chip advances"
2. "Prime Number Theory update"
3. "New materials created using AI"
4. "Matrix Multiplication advances"

**Action**: Search for these by partial title or check if they exist with different names

---

### **4. Parkinson's Disease Podcast (Resolved ✅)**
- **Status**: Found! (`ever-bio-250039`)
- **Title**: "Beyond Dopamine: Exploring New Frontiers in Parkinson's Disease Research"

**Action**: None needed

---

## 🎯 **Fix Plan**

### **Step 1: Find Missing Podcasts**
- Search podcast_jobs for failed/deleted entries
- Check episodes collection for orphans
- Compare with RSS feed

### **Step 2: Fix Missing Audio**
- Check if audio exists in GCS but URL is missing
- If missing, regenerate audio for `ever-phys-250042`

### **Step 3: Find Missing YouTube Podcasts**
- Search database by partial titles
- Check RSS feed for these titles
- Verify if they were renamed

---

## 📋 **Execution Order**

1. ✅ Search for 3 missing podcasts
2. ✅ Fix missing audio for "Quantum Computing Advances"
3. ✅ Find the 4 YouTube-reported podcasts
4. ✅ Create fixes/endpoints as needed

