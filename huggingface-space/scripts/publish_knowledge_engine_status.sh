#!/bin/bash
# Regenerate knowledge-engine-status.json and upload to GCS.
# Extra args are passed to generate_status_page.py, e.g.  -- --videos 800
set -e
cd "$(dirname "$0")/.."
python3 scripts/generate_status_page.py --source api "$@"
BUCKET="${GCS_STATUS_BUCKET:-gs://regal-scholar-453620-r7-podcast-storage}"
gsutil cp knowledge-engine-status.json "${BUCKET}/knowledge-engine-status.json"
echo "Uploaded: ${BUCKET}/knowledge-engine-status.json"
