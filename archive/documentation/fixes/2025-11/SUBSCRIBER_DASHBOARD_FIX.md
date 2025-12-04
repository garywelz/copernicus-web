# Subscriber Dashboard Count Fix

## 🐛 **Bug Identified**

The subscriber dashboard for `gwelz@jjay.cuny.edu` shows **16 podcasts** in the "Podcasts Generated" stat card, but the actual count is **52-53 podcasts**.

**Root Cause**: The `/api/subscribers/profile/{subscriber_id}` endpoint returns the stored `podcasts_generated` field instead of calculating the count dynamically.

---

## ✅ **Fix Applied**

### **Updated `get_subscriber_profile()` Endpoint**

Modified the endpoint to **calculate podcast counts dynamically** and override the stored value:

```python
# Calculate actual podcast count dynamically
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

# Override stored count with actual calculated count
actual_podcast_count = len(all_canonical_filenames)
subscriber_data['podcasts_generated'] = actual_podcast_count
```

**Location**: `cloud-run-backend/main.py` lines ~3208-3270

---

## 📊 **Current Status**

- **Stored count**: 16 (outdated)
- **Actual count**: 52-53 podcasts
- **Fix**: Code updated to calculate dynamically
- **Status**: Needs deployment

---

## 🎯 **What Will Be Fixed**

After deployment:

1. ✅ Subscriber dashboard will show **correct count** (52-53) in "Podcasts Generated" stat card
2. ✅ Admin dashboard subscriber list will show **correct count** (52-53)
3. ✅ Both will calculate in **real-time** (no stale data)

---

## 📋 **Files Changed**

- `cloud-run-backend/main.py`
  - Updated `get_subscriber_profile()` to calculate counts dynamically (lines ~3208-3270)
  - Updated `list_all_subscribers()` to calculate counts dynamically (lines ~3706-3739)

---

## ✅ **Both Dashboards Fixed!**

- ✅ **Admin Dashboard**: Subscriber list table count
- ✅ **Subscriber Dashboard**: "Podcasts Generated" stat card

Both will show the correct count of 52-53 after deployment!

