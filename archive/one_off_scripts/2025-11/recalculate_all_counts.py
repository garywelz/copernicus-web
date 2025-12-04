#!/usr/bin/env python3
"""Script to recalculate all subscriber podcast counts"""

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

url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/subscribers/recalculate-all-counts'
headers = {'X-Admin-API-Key': admin_key}

print("Recalculating all subscriber counts...")
response = requests.post(url, headers=headers, timeout=120)
print(f'\nStatus: {response.status_code}')
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2))
else:
    print(f'Error: {response.text}')

