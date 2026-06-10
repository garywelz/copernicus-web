#!/usr/bin/env bash
# Ingest paper JSON under metadata-database/papers/ into Firestore (research_papers).
# Prereq: gcloud application-default credentials (or a service account) for project regal-scholar-453620-r7.
# Manual:  bash scripts/ingest_metadata_to_firestore.sh
#          bash scripts/ingest_metadata_to_firestore.sh --dry-run
#          (optional "--" before flags is ignored:  ... sh -- --dry-run)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HFS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$(cd "$HFS_DIR/../cloud-run-backend" && pwd)"
ROOT_PAPERS="${HFS_DIR}/metadata-database/papers"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-regal-scholar-453620-r7}"
export FIRESTORE_DATABASE="${FIRESTORE_DATABASE:-copernicusai}"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "❌ cloud-run-backend not found at: $BACKEND_DIR"
  exit 2
fi
if [ ! -d "$ROOT_PAPERS" ]; then
  echo "❌ Paper metadata root not found: $ROOT_PAPERS"
  exit 2
fi

cd "$BACKEND_DIR"
if [ -f "venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "venv/bin/activate"
fi

echo "==> Ingest to Firestore"
echo "    project=$GOOGLE_CLOUD_PROJECT  database=$FIRESTORE_DATABASE"
echo "    root=$ROOT_PAPERS"
echo ""

EXTRA=()
for a in "$@"; do
  [ "$a" = "--" ] && continue
  EXTRA+=("$a")
done

python3 scripts/ingest_papers_from_metadata_json.py --root "$ROOT_PAPERS" --skip-existing "${EXTRA[@]}"
