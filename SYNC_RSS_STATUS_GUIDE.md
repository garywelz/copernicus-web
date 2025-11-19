# How to Run sync_rss_status.py

This guide provides step-by-step instructions for running the RSS sync script to update Firestore with episodes from your RSS feed.

## Prerequisites

1. **Google Cloud SDK (gcloud)** installed
2. **Python 3.8+** installed
3. **Access to your GCP project** with Firestore and GCS permissions

## Step-by-Step Instructions

### Option 1: Run on Your Local Machine

#### Step 1: Install Google Cloud SDK (if not already installed)

```bash
# On macOS
brew install google-cloud-sdk

# On Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# On Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

#### Step 2: Authenticate with Google Cloud

```bash
# Login to your Google account
gcloud auth login

# Set your default project
gcloud config set project regal-scholar-453620-r7

# Set up Application Default Credentials (required for the script)
gcloud auth application-default login
```

This will open a browser window for authentication. After completing, your credentials will be stored locally.

#### Step 3: Install Python Dependencies

```bash
cd /workspace  # or wherever your project is located

# Install required packages
pip3 install google-cloud-firestore google-cloud-storage

# Or if using a virtual environment (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install google-cloud-firestore google-cloud-storage
```

#### Step 4: Set Environment Variables (Optional)

The script has defaults, but you can override them:

```bash
export GOOGLE_CLOUD_PROJECT="regal-scholar-453620-r7"
export GCP_AUDIO_BUCKET="regal-scholar-453620-r7-podcast-storage"
```

#### Step 5: Test with Dry Run

```bash
cd /workspace
python3 sync_rss_status.py --dry-run
```

This will show you what changes would be made without actually updating Firestore.

#### Step 6: Run the Actual Sync

```bash
python3 sync_rss_status.py
```

You should see output like:
```
======================================================================
🔄 RSS Feed to Firestore Sync Script
======================================================================
Project: regal-scholar-453620-r7
Database: copernicusai
RSS Feed: https://storage.googleapis.com/...
======================================================================

📡 Fetching RSS feed from: https://storage.googleapis.com/...
✅ Successfully fetched RSS feed (123456 bytes)
🔍 Parsing RSS feed to extract episode GUIDs...
📋 Found 39 items in RSS feed
  ✓ Found GUID: news-bio-28032025
  ...
✅ Extracted 39 unique GUIDs from RSS feed

🔄 Syncing Firestore with RSS feed...
🔌 Connecting to Firestore (project: regal-scholar-453620-r7, database: copernicusai)...
✅ Firestore client initialized
📚 Fetching all podcast_jobs from Firestore...
📊 Found 50 total podcast jobs in Firestore

📝 Updating documents that appear in RSS feed (39 episodes)...
  ✅ news-bio-28032025: Updated submitted_to_rss=true
  ✅ news-chem-28032025: Updated submitted_to_rss=true
  ...

📊 SYNC SUMMARY
======================================================================
Total episodes in RSS feed: 39
Total podcast jobs in Firestore: 50
Episodes updated to submitted_to_rss=true: 37
Episodes already marked as submitted_to_rss=true: 2
Episodes in Firestore but NOT in RSS (marked true): 0
======================================================================

✅ Sync completed successfully!
```

---

### Option 2: Run on Google Cloud Shell

Google Cloud Shell already has gcloud and Python pre-installed.

#### Step 1: Open Cloud Shell

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the Cloud Shell icon (top right)
3. Wait for the shell to initialize

#### Step 2: Clone or Upload Your Project

```bash
# If your code is in a git repo:
git clone <your-repo-url>
cd <your-project-directory>

# Or upload sync_rss_status.py via the Cloud Shell editor
```

#### Step 3: Install Dependencies

```bash
pip3 install --user google-cloud-firestore google-cloud-storage
```

#### Step 4: Authenticate (usually automatic in Cloud Shell)

```bash
# Verify authentication
gcloud auth list

# If needed, set project
gcloud config set project regal-scholar-453620-r7
```

#### Step 5: Run the Script

```bash
# Dry run first
python3 sync_rss_status.py --dry-run

# Then actual sync
python3 sync_rss_status.py
```

---

### Option 3: Run via Cloud Run API Endpoint

If you've deployed the updated `main.py` with the endpoint, you can trigger the sync via HTTP:

#### Step 1: Get Your Cloud Run URL

Your Cloud Run service URL should be something like:
```
https://copernicus-podcast-api-204731194849.us-central1.run.app
```

#### Step 2: Call the Endpoint

```bash
# Using curl
curl -X POST https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/episodes/sync-rss-status

# Or using a tool like Postman or httpie
http POST https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/episodes/sync-rss-status
```

The endpoint will return JSON with statistics:
```json
{
  "status": "success",
  "message": "RSS status synced successfully",
  "stats": {
    "total_in_rss": 39,
    "total_in_firestore": 50,
    "updated": 37,
    "already_marked": 2,
    "not_in_rss_but_marked_true": 0,
    "missing_in_firestore": []
  }
}
```

---

## Troubleshooting

### Error: "No module named 'google'"

**Solution:** Install the required packages:
```bash
pip3 install google-cloud-firestore google-cloud-storage
```

### Error: "Could not automatically determine credentials"

**Solution:** Set up Application Default Credentials:
```bash
gcloud auth application-default login
```

### Error: "Permission denied" or "403 Forbidden"

**Solution:** Ensure your account has the necessary IAM roles:
- `roles/datastore.user` (for Firestore)
- `roles/storage.objectViewer` (for reading GCS)

You can check your roles:
```bash
gcloud projects get-iam-policy regal-scholar-453620-r7 --flatten="bindings[].members" --filter="bindings.members:user:YOUR_EMAIL"
```

### Error: "Database not found" or "Database copernicusai not found"

**Solution:** Verify the database name. You can list databases:
```bash
gcloud firestore databases list --project=regal-scholar-453620-r7
```

If your database has a different name, set it:
```bash
export FIRESTORE_DATABASE="your-database-name"
```

Or modify the script's `FIRESTORE_DATABASE` constant.

### Script Hangs or Times Out

**Possible causes:**
1. **Network issues** - Check your internet connection
2. **Firestore connection** - Verify you can access Firestore from your location
3. **Large dataset** - If you have thousands of documents, the script may take longer

**Solution:** Add timeout handling or run in smaller batches. You can also check Firestore quotas:
```bash
gcloud firestore operations list --project=regal-scholar-453620-r7
```

### RSS Feed Not Found

**Solution:** Verify the RSS feed URL is accessible:
```bash
curl https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml
```

If it's not public, the script will try to read it directly from GCS (requires authentication).

---

## What the Script Does

1. **Fetches RSS Feed**: Downloads the RSS XML from GCS (either via public URL or direct GCS access)
2. **Extracts GUIDs**: Parses all `<guid>` elements from RSS `<item>` entries
3. **Queries Firestore**: Gets all documents from the `podcast_jobs` collection
4. **Matches & Updates**: For each Firestore document:
   - If the document ID matches an RSS GUID → sets `submitted_to_rss: true`
   - If already `true` → skips (logs it)
   - If marked `true` but not in RSS → logs a warning
5. **Reports Statistics**: Shows summary of what was updated

---

## Expected Results

After running successfully, you should see:
- **39 episodes** marked as `submitted_to_rss: true` in Firestore (matching your RSS feed)
- Statistics showing how many were updated vs. already marked
- Any episodes in RSS that don't exist in Firestore (logged as warnings)

You can verify in the Firestore console:
1. Go to [Firestore Console](https://console.cloud.google.com/firestore)
2. Select your project and database
3. Navigate to `podcast_jobs` collection
4. Filter or check documents - you should see `submitted_to_rss: true` for episodes in the RSS feed

---

## Next Steps

After syncing:
1. **Verify in Firestore Console** - Check that episodes show `submitted_to_rss: true`
2. **Check Your Frontend** - The `podcast-database-table.html` should now show more episodes as "Published to RSS"
3. **Set Up Automation** (Optional) - Consider running this script periodically via Cloud Scheduler or as a Cloud Function

---

## Need Help?

If you encounter issues:
1. Check the error message carefully
2. Verify your GCP authentication: `gcloud auth list`
3. Test Firestore access: Try querying Firestore via the console
4. Test RSS feed access: Try accessing the RSS URL in a browser
5. Run with `--dry-run` first to see what would happen without making changes
