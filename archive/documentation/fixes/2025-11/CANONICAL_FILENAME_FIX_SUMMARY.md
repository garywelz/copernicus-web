# Canonical Filename Fix Summary - December 1, 2025

## ✅ Answers to Your Questions

### 1. **Is it true that some podcasts don't have canonical filenames?**

**YES!** Some podcasts are missing canonical filenames in the format `ever-category-25####` (like `ever-bio-250040`). Instead, they're using:
- Job IDs (UUIDs like `a1b2c3d4-e5f6-...`)
- Other non-standard identifiers

The database endpoint I created was already using `job_id` as a fallback when canonical filenames are missing (which is why I mentioned this).

### 2. **Can you list them?**

**YES!** I've created:

**Endpoint**: `GET /api/admin/podcasts/missing-canonical`
- Lists all podcasts without canonical filenames
- Shows title, current identifier, category, subscriber, etc.

**Script**: `list_missing_canonical.py`
- Calls the endpoint and displays results in a readable format
- Groups by category
- Shows detailed information for each podcast

### 3. **Can you change the filenames to canonical form?**

**YES!** I've enhanced the existing endpoint:

**Endpoint**: `POST /api/admin/podcasts/assign-canonical-filenames`
- Now finds ALL podcasts missing canonical filenames (not just UUIDs in RSS feed)
- Generates proper canonical filenames like `ever-bio-250041`
- Updates Firestore records
- Assigns sequential numbers per category

**Script**: `assign_all_canonical.py` (or use existing `assign_canonical_filenames.py`)
- Calls the endpoint with `fix_all_missing: true`
- Assigns canonical filenames to all podcasts missing them

## 📋 What Was Created

### New Endpoint

**`GET /api/admin/podcasts/missing-canonical`**
- Finds all podcasts without canonical filenames
- Checks both `podcast_jobs` and `episodes` collections
- Uses regex pattern: `^ever-(bio|chem|compsci|math|phys)-\d{6}$`
- Returns detailed list with titles, identifiers, categories, etc.

### Enhanced Endpoint

**`POST /api/admin/podcasts/assign-canonical-filenames`** (updated)
- Enhanced `fix_all_missing` mode to find ALL podcasts missing canonical filenames
- Not just UUIDs in RSS feed - finds podcasts using job_ids or any non-canonical identifiers
- Generates canonical filenames based on category and next available number

### Scripts Created

1. **`list_missing_canonical.py`**
   ```bash
   python3 list_missing_canonical.py
   ```
   - Lists all podcasts missing canonical filenames
   - Shows summary by category
   - Displays detailed information

2. **`assign_all_canonical.py`**
   ```bash
   python3 assign_all_canonical.py
   ```
   - Assigns canonical filenames to all podcasts missing them
   - Requires confirmation before running
   - Shows results summary

## 🚀 How to Use

### Step 1: List Missing Canonical Filenames

```bash
cd /home/gdubs/copernicus-web-public
export ADMIN_API_KEY="your-key-here"
python3 list_missing_canonical.py
```

This will show:
- Total count of podcasts missing canonical filenames
- Grouped by category
- Detailed list with titles, identifiers, etc.

### Step 2: Assign Canonical Filenames

```bash
python3 assign_all_canonical.py
```

Or use the existing script:
```bash
python3 assign_canonical_filenames.py
```

This will:
- Find all podcasts missing canonical filenames
- Generate proper canonical filenames (e.g., `ever-bio-250041`)
- Update Firestore records
- Show success/failure summary

## 📊 Canonical Filename Format

The canonical format is: **`ever-{category}-{episode_number}`**

Where:
- **category** is one of: `bio`, `chem`, `compsci`, `math`, `phys`
- **episode_number** is 6 digits like `250040`

Examples:
- `ever-bio-250040` ✅
- `ever-phys-250041` ✅
- `a1b2c3d4-e5f6-...` ❌ (UUID/job_id)
- `podcast-123` ❌ (non-canonical)

## 🔍 What Gets Fixed

The system will find and fix podcasts that:
- Have no `canonical_filename` field
- Have a `canonical_filename` that doesn't match the pattern `ever-category-25####`
- Are using job_id as the identifier
- Are using UUID GUIDs

## 📝 Notes

- The assignment process maintains sequential numbering per category
- Existing canonical filenames won't be changed
- Only podcasts missing or with invalid canonical filenames will be updated
- The process updates both `podcast_jobs` and `episodes` collections

## 🎯 Next Steps

1. **Run the list script** to see what needs fixing
2. **Review the results** to verify the list looks correct
3. **Run the assign script** to fix them all
4. **Verify** by checking the podcast database page

## ✅ Deployment Status

- ✅ Endpoint deployed to Cloud Run
- ✅ Scripts created and ready to use
- ⏳ Ready to list and assign canonical filenames

