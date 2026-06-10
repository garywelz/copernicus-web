#!/bin/bash
# Rebuild graph-data.json from metadata.json
# Run this whenever metadata.json changes (e.g. after adding processes or subcategories).
# The upload script also runs this automatically before uploading to GCS.
#
# Usage: ./rebuild-graph.sh   (from this directory)
#        or: cd mathematics-processes-database && node build-graph-data.js

set -e
cd "$(dirname "$0")"
node build-graph-data.js
echo "✅ Graph data rebuilt. Refresh whole-of-mathematics.html to see changes."
