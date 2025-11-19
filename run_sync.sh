#!/bin/bash
# Run RSS sync via API endpoint

curl -X POST https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/episodes/sync-rss-status
