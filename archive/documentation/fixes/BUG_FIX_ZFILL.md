# Bug Fix: Episode Number Padding (zfill)

## Issue
**Bug Type:** Off-by-one error in episode number formatting

**Location:** `cloud-run-backend/main.py` lines 1557 and 1569

**Description:** 
The code was using `.zfill(5)` to pad episode numbers to 5 digits, but:
1. The inline comment stated "Pad to 5 digits like 250032"
2. **250032 is actually 6 digits, not 5**
3. The `category_episodes` dictionary shows biology starting at `250007` (6 digits)
4. The original naming convention uses 6-digit episode numbers

## Root Cause
Mismatch between:
- **Code:** `.zfill(5)` → produces 5-digit padded strings (e.g., `"00001"`)
- **Convention:** Episode numbers are 6 digits (e.g., `250007`, `250032`)
- **Comment:** Incorrectly claimed 5 digits while showing a 6-digit example

## Impact
- **Low episodes (1-99999):** Would be padded to only 5 digits (e.g., `"00001"` instead of `"000001"`)
- **High episodes (≥100000):** Would work correctly since the number is already ≥5 digits
- **Biology category:** Starting at 250007, this category would not have been affected, but new categories starting from lower numbers would have incorrect filenames

## Fix
Changed both occurrences:

```python
# BEFORE (INCORRECT)
next_episode_str = str(next_episode).zfill(5)  # Pad to 5 digits like 250032

# AFTER (CORRECT)
next_episode_str = str(next_episode).zfill(6)  # Pad to 6 digits like 250032
```

### Files Modified
- `cloud-run-backend/main.py` (line 1557)
- `cloud-run-backend/main.py` (line 1569)

## Verification
Episode number examples:
- `1` → `"000001"` (was `"00001"`) ✅
- `250007` → `"250007"` (unchanged) ✅
- `250032` → `"250032"` (unchanged) ✅
- `999999` → `"999999"` (was `"999999"`) ✅

## Deployment
- **Status:** Fixed and deployed to Cloud Run
- **Date:** November 6, 2025
- **Service:** `copernicus-podcast-api`

## Testing Recommendations
1. Generate a new podcast in a low-episode category (chem, compsci, math, phys)
2. Verify the filename in GCS uses 6-digit padding (e.g., `ever-chem-000001.mp3`)
3. Check that the episode number in the RSS feed matches the filename

---

**Reporter:** User feedback
**Fixed by:** AI Assistant
**Verified:** ✅ Code analysis confirms the bug and fix

