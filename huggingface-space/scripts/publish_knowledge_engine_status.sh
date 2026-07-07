#!/bin/bash
# Regenerate knowledge-engine-status.json and upload to GCS.
# Extra args are passed to generate_status_page.py, e.g.  -- --videos 800
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

# Jetson: system python3 is 3.6; master-todo-cron venv has py3.13 + google-cloud-storage
PYTHON="${PUBLISH_PYTHON:-/media/sdcard/venvs/master-todo-cron/bin/python}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-/home/gary/.config/copernicus/gcp-sa.json}"

"$PYTHON" scripts/generate_status_page.py --source api "$@"
"$PYTHON" scripts/upload_knowledge_engine_status_gcs.py --local "$BASE/knowledge-engine-status.json"
echo "Published: gs://${GCS_STATUS_BUCKET_NAME:-regal-scholar-453620-r7-podcast-storage}/knowledge-engine-status.json"
