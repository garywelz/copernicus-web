# Issues Diagnosis and Fixes

**Date:** January 2025  
**Issues Investigated:** 3 critical issues

---

## 🔴 Issue 1: Failed Podcast - "AI Data Center Building Boom"

### Diagnosis
**Error Found:**
```
Both Vertex AI and Google AI API failed. 
Vertex: 404 Not Found
Google: 404 models/gemini-1.5-flash is not found for API version v1beta
```

**Root Cause:**
- The system tried to use `models/gemini-1.5-flash` which doesn't exist in the API
- Fallback chain is incomplete - when Gemini 3.0 fails, it falls back to 2.5, but somewhere in the chain it's trying to use 1.5-flash which is invalid
- The error handling isn't catching all model failures properly

**Job ID:** `dc312c2e-78fe-4c3c-be34-2db700d94534`  
**Status:** `failed`  
**Created:** 2025-11-27  
**Subscriber ID:** `2ba148605cbe5df7ab758646b76393bbeb87aad3adb993fef20ad90fbaf0f4ef`

### Fix Required
1. **Update model fallback chain** to use valid models only:
   - Primary: `models/gemini-3.0-flash`
   - Fallback 1: `models/gemini-2.5-flash`
   - Fallback 2: `models/gemini-2.0-flash-exp`
   - Fallback 3: `models/gemini-1.5-pro` (not flash - that's the issue!)
   
2. **Fix Google AI API model usage** - it's trying to use v1beta API version incorrectly

3. **Improve error handling** to catch model availability issues earlier

---

## 🔴 Issue 2: Incomplete Podcasts Stuck in Collection

### Diagnosis
**Found:** 4 podcasts stuck in `generating_content` status since September 2025

**Stuck Podcasts:**
1. Job ID: `6ae0b6f7-85dd-4bb8-8...` - "New materials created using AI" (Created: 2025-09-06)
2. Job ID: `85b0f041-75be-4e79-9...` - "Quantum Computing chip advances" (Created: 2025-09-10)
3. Job ID: `977d7344-63f2-4aa7-8...` - "Prime Number Theory update" (Created: 2025-09-06)
4. One more (details truncated)

**Root Cause:**
- These podcasts were likely interrupted during generation (timeout, crash, or manual termination)
- They got stuck in `generating_content` status and never completed or failed
- No cleanup mechanism to mark old incomplete jobs as failed

### Fix Required
1. **Cleanup script** to mark old incomplete podcasts as `failed` with reason "stuck_in_generation"
2. **Add timeout mechanism** to automatically fail jobs that have been in non-terminal status for >24 hours
3. **Add watchdog** to detect and clean up stuck jobs periodically

---

## 🔴 Issue 3: Incorrect Podcast Counts and Wrong Assignments

### Diagnosis

#### Count Discrepancy
**Subscriber:** `gwelz@jjay.cuny.edu` (Gary Welz)
- **Stored Count:** 21
- **Actual Count:** 19  
- **Completed Count:** 14
- **Discrepancy:** -2 (stored is higher than actual)

**Root Cause:**
- Some podcasts were deleted from `podcast_jobs` collection but the subscriber's `podcasts_generated` count was never decremented
- Or podcasts were created but failed before being counted, yet the count was incremented

#### Wrong Assignments
**John Covington** (`john.covington@verizon.net`)
- Has 1 podcast assigned
- No suspicious admin reassignments found in diagnostic
- **This seems correct** - only 1 podcast assigned

**However**, the user mentioned seeing podcasts in John's account that shouldn't be there. Need to investigate:
- Check if there are podcasts assigned to John that were created by someone else
- Check creation timestamps vs assignment timestamps

### Fix Required
1. **Recalculate podcast counts** for all subscribers based on actual `podcast_jobs` collection
2. **Audit script** to find podcasts assigned to wrong subscribers:
   - Compare `subscriber_id` with `request.subscriber_id` (if stored)
   - Check for admin reassignments that don't match original creator
3. **Fix count increment/decrement logic** to only count successful completions

---

## ✅ Recommended Actions

### Immediate Fixes (High Priority)

1. **Fix Model Fallback Chain** 
   - Update all model references to use valid Gemini models
   - Remove `models/gemini-1.5-flash` (doesn't exist in API)
   - Add proper fallback to `models/gemini-1.5-pro` or `models/gemini-2.0-flash-exp`

2. **Clean Up Stuck Podcasts**
   - Mark 4 stuck podcasts as `failed` with reason
   - Create cleanup script for future stuck jobs

3. **Fix Podcast Counts**
   - Recalculate `podcasts_generated` for all subscribers
   - Update Firestore with correct counts

### Medium Priority

4. **Add Timeout/Cleanup Mechanism**
   - Automatic job timeout after 24 hours in non-terminal status
   - Periodic cleanup job

5. **Audit Subscriber Assignments**
   - Find all podcasts assigned to wrong subscribers
   - Provide reassignment tool

### Low Priority

6. **Improve Error Messages**
   - Better error messages for model failures
   - Clearer user-facing error messages

---

## Next Steps

1. Fix model fallback chain in `main.py`
2. Create cleanup script for stuck podcasts
3. Create count recalculation script
4. Create assignment audit script

