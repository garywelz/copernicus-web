# Admin Dashboard - Subscriber Management

## Overview
Added a complete admin dashboard for managing CopernicusAI subscribers with viewing and deletion capabilities.

## Features Implemented

### 1. **Subscriber List Endpoint** (`GET /api/admin/subscribers`)
- **Location:** `cloud-run-backend/main.py` (lines 2883-2929)
- **Returns:** JSON array with all subscriber data
- **Fields:**
  - `email` - Actual email address (not hashed)
  - `subscriber_id` - SHA-256 hash (document ID)
  - `display_name` - User's display name
  - `initials` - User's initials
  - `show_attribution` - Whether to show attribution in RSS
  - `created_at` - Account creation timestamp
  - `last_login` - Last login timestamp
  - `podcast_count` - Number of podcasts generated

### 2. **Delete Subscriber Endpoint** (`DELETE /api/admin/subscribers/{subscriber_id}`)
- **Location:** `cloud-run-backend/main.py` (lines 2931-2961)
- **Functionality:**
  - Validates subscriber exists
  - Deletes subscriber document from Firestore
  - Returns confirmation with email and ID
- **Security:** No authentication yet (recommend adding later)

### 3. **Admin Web Dashboard**
- **URL:** `https://copernicus-web-public-79jr9698z-gary-welzs-projects.vercel.app/admin-subscribers.html`
- **File:** `public/admin-subscribers.html`

#### Dashboard Features:
- ✅ **Summary Stats Cards**
  - Total Subscribers
  - Subscribers with Attribution
  - Total Podcasts Generated

- ✅ **Subscriber Table**
  - Email addresses (real, not hashed)
  - Display names and initials
  - Attribution status
  - Podcast count
  - Created and last login dates
  - Delete button for each subscriber

- ✅ **Delete Functionality**
  - Click "🗑️ Delete" button
  - Confirmation dialog
  - Deletes from Firestore
  - Auto-refreshes list

- ✅ **Export to CSV**
  - Downloads all subscriber data
  - Filename: `copernicus-subscribers-YYYY-MM-DD.csv`

## Bug Fixes

### Bug #1: Email Addresses Showing as Hashes
**Problem:** Document IDs (SHA-256 hashes) were displayed instead of actual emails

**Cause:** Code was using `sub.id` (document ID) instead of `data.get('email')`

**Fix:**
```python
# Before (line 2908)
'email': sub.id,  # ❌ This was the hash

# After
'email': data.get('email', 'N/A'),  # ✅ Actual email from document
```

### Bug #2: Podcast Count Always 0
**Problem:** Podcast counts showed 0 even for users who generated podcasts

**Cause:** Wrong field name - using `podcast_count` instead of `podcasts_generated`

**Fix:**
```python
# Before (line 2915)
'podcast_count': data.get('podcast_count', 0)  # ❌ Wrong field

# After
'podcast_count': data.get('podcasts_generated', 0)  # ✅ Correct field
```

## Current Subscriber Analysis (from your data)

Based on the 7 accounts shown:

1. **rossscott1@me.com** - Testing account
2. **gwelz@jjay.cuny.edu** - Your account (duplicate #1)
3. **gwelz@jjay.cuny.edu** - Your account (duplicate #2, has profile data)
4. **edshelp247@gmail.com** - Incomplete registration (null display name)
5. **gary.welz@me.com** - Leo Welz account (has attribution enabled)
6. **scimedtv@gmail.com** - Your account (duplicate #1)
7. **scimedtv@gmail.com** - Your account (duplicate #2)

### Recommendations:
- **Keep:** `gwelz@jjay.cuny.edu` (#3 - has profile), `gary.welz@me.com` (#5 - Leo's account)
- **Consider deleting:** Duplicates (#2, #6, #7), test accounts (#1), incomplete (#4)

## Security Considerations

⚠️ **No Authentication:** The admin endpoints are currently PUBLIC

**Recommended Next Steps:**
1. Add API key authentication
2. Or restrict to specific Google accounts
3. Or add IP whitelist
4. Or move to Firebase Admin SDK with proper auth

## Deployment

- **Backend:** Cloud Run (revision 00099+)
- **Frontend:** Vercel (`admin-subscribers.html`)

## Usage

1. Visit: `https://copernicus-web-public-79jr9698z-gary-welzs-projects.vercel.app/admin-subscribers.html`
2. View all subscribers in the table
3. Click "🗑️ Delete" next to any subscriber to remove them
4. Click "📊 Export to CSV" to download the data

---

**Date:** November 6, 2025  
**Status:** ✅ Deployed and functional

