#!/bin/bash

# Deploy HTML files to Google Cloud Storage for public serving
# This script uploads all updated HTML files to GCS and makes them publicly readable

set -e

echo "🚀 Deploying HTML files to Google Cloud Storage..."

# Configuration
BUCKET_NAME="regal-scholar-453620-r7-podcast-storage"
PROJECT_ID="regal-scholar-453620-r7"

# Set the project
gcloud config set project $PROJECT_ID

# Files to upload
FILES=(
    "public/admin-dashboard.html"
    "public/podcast-database.html"
    "public/subscriber-dashboard.html"
    "public/subscriber-login.html"
    "public/subscriber-create-account.html"
    "public/index.html"
    "public/search.html"
    "public/podcast-database-table.html"
)

# Upload files
echo "📤 Uploading HTML files..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "  → Uploading $filename..."
        gsutil cp "$file" "gs://$BUCKET_NAME/$filename"
    else
        echo "  ⚠️  File not found: $file"
    fi
done

# Make all HTML files publicly readable
echo "🔓 Making HTML files publicly readable..."
gsutil -m acl ch -u AllUsers:R "gs://$BUCKET_NAME/*.html"

# Set content type for HTML files
echo "📝 Setting content-type headers..."
gsutil -m setmeta -h "Content-Type:text/html" "gs://$BUCKET_NAME/*.html"

echo ""
echo "✅ HTML files deployed successfully!"
echo ""
echo "🌐 Files are accessible at:"
echo "   https://storage.googleapis.com/$BUCKET_NAME/"
echo ""
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "   - https://storage.googleapis.com/$BUCKET_NAME/$filename"
    fi
done



