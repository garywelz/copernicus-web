#!/usr/bin/env python3
import requests
import json
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

admin_key = get_admin_api_key()
url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/rss/diagnose-thumbnails'
headers = {'X-Admin-API-Key': admin_key}

response = requests.get(url, headers=headers, timeout=300)
if response.status_code == 200:
    result = response.json()
    missing = result.get('missing_thumbnails_in_rss', [])
    if missing:
        print(f"\n❌ Still missing ({len(missing)}):")
        for ep in missing:
            print(f"  - {ep.get('title', ep.get('guid'))}")
    else:
        print("\n✅ All thumbnails found!")

