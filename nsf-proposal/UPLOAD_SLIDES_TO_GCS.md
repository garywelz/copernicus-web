# Upload TDA_Seminar_Slides.html to Google Cloud Storage

## File Location
- **Source file**: `/home/gdubs/copernicus-web-public/nsf-proposal/TDA_Seminar_Slides.html`
- **Target GCS bucket**: `regal-scholar-453620-r7-podcast-storage`
- **Target path**: `TDA_Seminar_Slides.html` (root of bucket)

## Upload Methods

### Option 1: Using Google Cloud Console (Web UI)

1. Go to: https://console.cloud.google.com/storage/browser/regal-scholar-453620-r7-podcast-storage
2. Click "Upload Files"
3. Select `TDA_Seminar_Slides.html` from your local machine
4. Upload to the root of the bucket (same level as `glmp-database-table.html`)
5. Ensure the file is publicly accessible (check permissions)

### Option 2: Using gsutil Command Line

```bash
gsutil cp /home/gdubs/copernicus-web-public/nsf-proposal/TDA_Seminar_Slides.html \
  gs://regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides.html

# Make it publicly readable
gsutil acl ch -u AllUsers:R gs://regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides.html
```

### Option 3: Using Python (if you have gcloud SDK)

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('regal-scholar-453620-r7-podcast-storage')
blob = bucket.blob('TDA_Seminar_Slides.html')
blob.upload_from_filename('/home/gdubs/copernicus-web-public/nsf-proposal/TDA_Seminar_Slides.html')
blob.make_public()  # Make it publicly accessible
```

## Verify Upload

After uploading, verify the file is accessible at:
```
https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/TDA_Seminar_Slides.html
```

The slides should render properly in a browser (not show raw HTML).

## Files Updated

Both `index.html` and `README.md` have been updated with the new Google Cloud Storage URL:
- `index.html`: Link updated in the Publications & Presentations section
- `README.md`: Link updated in the Publications & Presentations section

After uploading the HTML file to GCS, the links will work correctly.
