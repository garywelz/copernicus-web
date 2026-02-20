#!/bin/bash
# Upload Chemistry Processes Database to Google Cloud Storage

set -e  # Exit on error

# Configuration
BUCKET="gs://regal-scholar-453620-r7-podcast-storage"
GCS_PATH="${BUCKET}/chemistry-processes-database"
LOCAL_DIR="chemistry-processes-database"

echo "============================================================"
echo "Uploading Chemistry Processes Database to GCS"
echo "============================================================"
echo "Source: ${LOCAL_DIR}/"
echo "Destination: ${GCS_PATH}/"
echo ""

# Check if gsutil is available
if ! command -v gsutil &> /dev/null; then
    echo "ERROR: gsutil not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if local directory exists
if [ ! -d "${LOCAL_DIR}" ]; then
    echo "ERROR: Directory ${LOCAL_DIR} not found"
    exit 1
fi

# Change to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}/.."

echo "Step 1: Uploading JSON files..."
gsutil -m cp -r "${LOCAL_DIR}/processes/**/*.json" "${GCS_PATH}/processes/" 2>&1 | head -20

echo ""
echo "Step 2: Uploading HTML viewer files..."
gsutil -m cp -r "${LOCAL_DIR}/processes/**/*.html" "${GCS_PATH}/processes/" 2>&1 | head -20

echo ""
echo "Step 3: Uploading metadata.json..."
gsutil cp "${LOCAL_DIR}/metadata.json" "${GCS_PATH}/metadata.json"

echo ""
echo "Step 4: Uploading database table HTML..."
gsutil cp "${LOCAL_DIR}/chemistry-database-table.html" "${GCS_PATH}/chemistry-database-table.html"

echo ""
echo "Step 5: Setting public read permissions..."
gsutil -m acl ch -r -u AllUsers:R "${GCS_PATH}/**" 2>&1 | head -10

echo ""
echo "Step 6: Setting content types..."
gsutil -m -h "Content-Type:text/html" cp -r "${LOCAL_DIR}/processes/**/*.html" "${GCS_PATH}/processes/" 2>&1 | head -5
gsutil -h "Content-Type:text/html" cp "${LOCAL_DIR}/chemistry-database-table.html" "${GCS_PATH}/chemistry-database-table.html"
gsutil -h "Content-Type:application/json" cp "${LOCAL_DIR}/metadata.json" "${GCS_PATH}/metadata.json"
gsutil -m -h "Content-Type:application/json" cp -r "${LOCAL_DIR}/processes/**/*.json" "${GCS_PATH}/processes/" 2>&1 | head -5

echo ""
echo "============================================================"
echo "Upload Complete!"
echo "============================================================"
echo ""
echo "Database Table URL:"
echo "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/chemistry-database-table.html"
echo ""
echo "Metadata URL:"
echo "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/metadata.json"
echo ""
