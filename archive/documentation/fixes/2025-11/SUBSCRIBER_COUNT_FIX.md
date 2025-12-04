# Subscriber Podcast Count Fix

## 🐛 **Bug Identified**

The admin dashboard shows **16 podcasts** for `gwelz@jjay.cuny.edu`, but the actual count is **52-53 podcasts**.

**Root Cause**: The `list_all_subscribers()` endpoint uses the stored `podcasts_generated` field instead of calculating counts dynamically.

---

## ✅ **Fix Applied**

### **1. Updated `list_all_subscribers()` Endpoint**

Modified the endpoint to **calculate podcast counts dynamically** instead of using stored values:

```python
# Calculate actual podcast count dynamically
subscriber_id = sub.id
all_canonical_filenames = set()

# Count from podcast_jobs
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        all_canonical_filenames.add(canonical)
    else:
        all_canonical_filenames.add(job_doc.id)

# Count from episodes
episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
for episode_doc in episodes_query:
    canonical = episode_doc.id
    all_canonical_filenames.add(canonical)

# Use actual count
actual_podcast_count = len(all_canonical_filenames)
```

**Location**: `cloud-run-backend/main.py` lines ~3706-3739

---

## 📊 **Current Status**

- **Stored count**: 16 (outdated)
- **Actual count**: 52-53 podcasts
- **Fix**: Code updated to calculate dynamically
- **Status**: Needs deployment

---

## 🎯 **What Will Be Fixed**

After deployment:

1. ✅ Subscriber list will show **correct counts** for all subscribers
2. ✅ Counts will be **calculated in real-time** (no stale data)
3. ✅ "View Podcasts" page already uses the correct endpoint (should show all 52-53)

---

## 📋 **Files Changed**

- `cloud-run-backend/main.py`
  - Updated `list_all_subscribers()` to calculate counts dynamically

---

## 🔍 **Verification**

The "View Podcasts" button calls `/api/admin/subscribers/{subscriber_id}/podcasts` which already returns all podcasts correctly (52-53). The issue is only in the subscriber list table showing the count.

After deployment, the count in the table will match the actual number of podcasts.

