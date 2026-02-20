#!/bin/bash

# Upload All Processes to GCS
# Uploads all refined process files to Google Cloud Storage as primary source
# 
# Usage: ./scripts/upload_all_processes_to_gcs.sh [--dry-run]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUCKET="gs://regal-scholar-453620-r7-podcast-storage"
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No files will be uploaded"
fi

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Upload All Processes to GCS"
echo "=========================================="
echo ""

# Function to upload a process database
upload_process_database() {
    local db_name=$1
    local process_count=$2
    local gcs_path="$BUCKET/$db_name"
    
    echo "📦 Uploading $db_name ($process_count processes)..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "   Would upload to: $gcs_path/processes/"
        find "$db_name/processes" -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l | xargs echo "   Files to upload:"
    else
        # Upload process files, preserving directory structure.
        # This ensures URLs like .../processes/<subcategory>/<process-id>.json keep working.
        if [ -d "$db_name/processes" ]; then
            # Exclude any "*.backup" files while mirroring structure.
            gsutil -m rsync -r -x ".*\\.backup$" "$db_name/processes" "$gcs_path/processes"
        fi
        
        # Upload metadata if exists
        if [ -f "$db_name/metadata.json" ]; then
            gsutil cp "$db_name/metadata.json" "$gcs_path/metadata.json"
        fi
        
        # Upload database table HTML if exists
        if [ -f "$db_name"/*-database-table.html ]; then
            gsutil cp "$db_name"/*-database-table.html "$gcs_path/"
        fi
        
        echo "   ✅ Uploaded to: $gcs_path"
    fi
    echo ""
}

# Count processes in each database
echo "📊 Counting processes..."
BIOLOGY_COUNT=$(find biology-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)
CHEMISTRY_COUNT=$(find chemistry-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)
PHYSICS_COUNT=$(find physics-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)
MATHEMATICS_COUNT=$(find mathematics-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)
GLMP_COUNT=$(find glmp-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)
CS_COUNT=$(find computer-science-processes-database/processes -name "*.json" ! -name "*.backup" 2>/dev/null | wc -l)

TOTAL=$((BIOLOGY_COUNT + CHEMISTRY_COUNT + PHYSICS_COUNT + MATHEMATICS_COUNT + GLMP_COUNT + CS_COUNT))

echo "   Biology: $BIOLOGY_COUNT"
echo "   Chemistry: $CHEMISTRY_COUNT"
echo "   Physics: $PHYSICS_COUNT"
echo "   Mathematics: $MATHEMATICS_COUNT"
echo "   GLMP: $GLMP_COUNT"
echo "   Computer Science: $CS_COUNT"
echo "   Total: $TOTAL processes"
echo ""

# Upload each database
if [ "$DRY_RUN" = false ]; then
    read -p "Continue with upload? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Upload cancelled"
        exit 1
    fi
fi

echo "🚀 Starting upload..."
echo ""

# Upload each database
upload_process_database "biology-processes-database" "$BIOLOGY_COUNT"
upload_process_database "chemistry-processes-database" "$CHEMISTRY_COUNT"
upload_process_database "physics-processes-database" "$PHYSICS_COUNT"
upload_process_database "mathematics-processes-database" "$MATHEMATICS_COUNT"
upload_process_database "glmp-processes-database" "$GLMP_COUNT"
upload_process_database "computer-science-processes-database" "$CS_COUNT"

# Set public read permissions (optional)
if [ "$DRY_RUN" = false ]; then
    echo "🔐 Setting public read permissions..."
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/biology-processes-database/**" 2>/dev/null || true
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/chemistry-processes-database/**" 2>/dev/null || true
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/physics-processes-database/**" 2>/dev/null || true
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/mathematics-processes-database/**" 2>/dev/null || true
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/glmp-processes-database/**" 2>/dev/null || true
    gsutil -m acl ch -r -u AllUsers:R "$BUCKET/computer-science-processes-database/**" 2>/dev/null || true
    echo "   ✅ Permissions set"
fi

echo ""
echo "=========================================="
if [ "$DRY_RUN" = true ]; then
    echo "✅ Dry run complete - No files uploaded"
else
    echo "✅ Upload complete!"
    echo ""
    echo "📋 Summary:"
    echo "   Total processes uploaded: $TOTAL"
    echo "   Location: $BUCKET"
fi
echo "=========================================="
