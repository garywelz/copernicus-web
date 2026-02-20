# GCS Upload Instructions - Chemistry Processes Database

## Overview
Upload the Chemistry Processes Database to Google Cloud Storage for public access.

## Target Location
- **Bucket:** `regal-scholar-453620-r7-podcast-storage`
- **Path:** `chemistry-processes-database/`
- **Public URL:** `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/`

---

## Quick Upload (Automated Script)

### Option 1: Run the Upload Script
```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
chmod +x scripts/upload_chemistry_to_gcs.sh
./scripts/upload_chemistry_to_gcs.sh
```

---

## Manual Upload Commands

### Step 1: Upload JSON Files
```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
gsutil -m cp -r chemistry-processes-database/processes/**/*.json \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/processes/
```

### Step 2: Upload HTML Viewer Files
```bash
gsutil -m cp -r chemistry-processes-database/processes/**/*.html \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/processes/
```

### Step 3: Upload Metadata and Database Table
```bash
gsutil cp chemistry-processes-database/metadata.json \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/metadata.json

gsutil cp chemistry-processes-database/chemistry-database-table.html \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html
```

### Step 4: Set Public Read Permissions
```bash
gsutil -m acl ch -r -u AllUsers:R \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/**
```

### Step 5: Set Correct Content Types
```bash
# Set HTML content type for all HTML files
gsutil -m -h "Content-Type:text/html" cp -r \
  chemistry-processes-database/processes/**/*.html \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/processes/

gsutil -h "Content-Type:text/html" cp \
  chemistry-processes-database/chemistry-database-table.html \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html

# Set JSON content type for all JSON files
gsutil -h "Content-Type:application/json" cp \
  chemistry-processes-database/metadata.json \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/metadata.json

gsutil -m -h "Content-Type:application/json" cp -r \
  chemistry-processes-database/processes/**/*.json \
  gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/processes/
```

---

## Verification

After upload, verify the files are accessible:

```bash
# Check database table
curl -I https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html

# Check metadata
curl -I https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/metadata.json

# List uploaded files
gsutil ls -r gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/ | head -20
```

---

## Expected File Structure in GCS

```
gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/
├── metadata.json
├── chemistry-database-table.html
└── processes/
    ├── organic_chemistry/
    │   ├── organic_chemistry-organic-reaction-mechanisms.json
    │   ├── organic_chemistry-organic-reaction-mechanisms.html
    │   └── ... (3 processes)
    ├── physical_chemistry/
    │   └── ... (3 processes)
    ├── analytical_chemistry/
    │   └── ... (3 processes)
    └── ... (11 more subcategories)
```

---

## Public Access URLs

Once uploaded, these URLs will be accessible:

- **Database Table:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html
- **Metadata:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/metadata.json

---

## Notes

- The `-m` flag enables parallel uploads for faster transfer
- The `-r` flag enables recursive directory copying
- Content-Type headers ensure browsers interpret files correctly
- Public read permissions allow access without authentication
