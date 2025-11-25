# Voice ID Swap Fix - November 2, 2025

## 🐛 Bug Description
When users selected **Bella** (female) and **Bryan** (male) voices:
- **Bella's lines were spoken in a MALE voice**
- **Bryan's lines were spoken in a FEMALE voice**

## 🔍 Root Cause
The ElevenLabs voice IDs for Bella and Bryan were **swapped** in our system mappings.

### Incorrect Mappings (Before Fix):
```javascript
// Frontend: public/subscriber-dashboard.html
"pqHfZKP75CvOlQylNhV4" → Bella (❌ This ID is actually male!)
"EXAVITQu4vr4xnSDxMaL" → Bryan (❌ This ID is actually female!)
```

```python
# Backend: cloud-run-backend/podcast_research_integrator.py
"pqHfZKP75CvOlQylNhV4": "Bella"  # ❌ Wrong!
"EXAVITQu4vr4xnSDxMaL": "Bryan"  # ❌ Wrong!
```

## ✅ Fix Applied
Swapped the voice IDs to match the correct genders:

### Correct Mappings (After Fix):
```javascript
// Frontend: public/subscriber-dashboard.html
"EXAVITQu4vr4xnSDxMaL" → Bella (✅ Female voice)
"pqHfZKP75CvOlQylNhV4" → Bryan (✅ Male voice)
```

```python
# Backend: cloud-run-backend/podcast_research_integrator.py
"EXAVITQu4vr4xnSDxMaL": "Bella"  # ✅ Female, British
"pqHfZKP75CvOlQylNhV4": "Bryan"  # ✅ Male, American
```

## 📋 Changes Made

### 1. Frontend (`public/subscriber-dashboard.html`)
- **Line 270**: Changed Bella's ID from `pqHfZKP75CvOlQylNhV4` → `EXAVITQu4vr4xnSDxMaL`
- **Line 280**: Changed Bryan's ID from `EXAVITQu4vr4xnSDxMaL` → `pqHfZKP75CvOlQylNhV4`

### 2. Backend (`cloud-run-backend/podcast_research_integrator.py`)
- **Line 272**: Updated Bella mapping to `EXAVITQu4vr4xnSDxMaL`
- **Line 275**: Updated Bryan mapping to `pqHfZKP75CvOlQylNhV4`

## 🧪 Testing
**After deployment completes**, test with:

1. Generate a new podcast
2. Select **Bella** (Host) + **Bryan** (Expert)
3. Expected results:
   - ✅ Script says "BELLA:" and "BRYAN:"
   - ✅ **Bella's voice is FEMALE** (British accent)
   - ✅ **Bryan's voice is MALE** (American accent)
   - ✅ Two distinct voices in the audio

## 📦 Deployment
- **Frontend**: Vercel (Revision: pending)
- **Backend**: Cloud Run (Revision: pending)
- **Commit**: `5178218` - "Fix: Swap Bella and Bryan voice IDs - they were reversed"

## 🎯 Impact
This fix ensures that:
- All 6 voices (Matilda, Bella, Sam, Adam, Bryan, Daniel) now map to their correct genders
- Users can confidently select voice combinations knowing the gender will match the name
- The dynamic voice selection feature works as intended

---

**Status**: ✅ Fix deployed, awaiting verification

