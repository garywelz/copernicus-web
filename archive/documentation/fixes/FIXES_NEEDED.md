# Critical Fixes Needed

## ✅ Issue 1: Failed Podcast - MODEL ERROR (FIXING NOW)

**Error:** `models/gemini-1.5-flash is not found for API version v1beta`

**Location:** Line 1965 in `main.py`

**Fix:** Replace invalid model name with valid fallback:
- Change `'gemini-1.5-flash'` to `'gemini-1.5-pro'` or `'gemini-2.0-flash-exp'`
- Update Google AI API fallback to use correct model format

---

## ⏳ Issue 2: Stuck Podcasts (4 podcasts)

**Status:** 4 podcasts stuck in `generating_content` since September 2025

**Fix Needed:** 
- Mark them as `failed` with reason "stuck_in_generation"
- Create cleanup script for future stuck jobs

**Action:** Will create cleanup script after fixing model issue

---

## ⏳ Issue 3: Count Discrepancy

**Subscriber:** gwelz@jjay.cuny.edu
- Stored: 21
- Actual: 19
- **Discrepancy: -2**

**Fix Needed:**
- Recalculate and update count

**Action:** Will create count fix script

---

## ⏳ Issue 4: John Covington Assignment

**Status:** Only 1 podcast found (seems correct)
**Action:** Need more info from you about which podcasts shouldn't be there

---

## Priority Order:
1. ✅ **NOW:** Fix model error (blocks new podcasts)
2. ⏳ Clean up stuck podcasts
3. ⏳ Fix count discrepancy  
4. ⏳ Investigate John Covington issue (need more details)

