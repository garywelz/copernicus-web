#!/usr/bin/env python3
"""Script to recalculate subscriber podcast count"""

import requests
import json
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Error: {e}")
        return None

admin_key = get_admin_api_key()
if not admin_key:
    exit(1)

subscriber_id = "2ba148605cbe5df7ab758646b76393bbeb87aad3adb993fef20ad90fbaf0f4ef"
url = f'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/subscribers/{subscriber_id}/recalculate-count'
headers = {'X-Admin-API-Key': admin_key}

response = requests.post(url, headers=headers, timeout=60)
print(f'Status: {response.status_code}')
print(json.dumps(response.json(), indent=2))

