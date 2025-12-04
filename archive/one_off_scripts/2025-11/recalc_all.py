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
url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/subscribers/recalculate-all-counts'
headers = {'X-Admin-API-Key': admin_key}

response = requests.post(url, headers=headers, timeout=120)
print(f'Status: {response.status_code}')
print(json.dumps(response.json(), indent=2))

