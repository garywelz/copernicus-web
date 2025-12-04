#!/usr/bin/env python3
"""Regenerate thumbnail for the one remaining episode that needs it"""

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
url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/rss/regenerate-thumbnails'
headers = {
    'X-Admin-API-Key': admin_key,
    'Content-Type': 'application/json'
}

payload = {
    'episode_guids': ['ever-bio-250040']
}

print("🖼️  Regenerating thumbnail for 'Revolutionizing COVID-19 Treatment'...")
print("⏳ This may take a minute (DALL-E generation)...\n")

response = requests.post(url, headers=headers, json=payload, timeout=300)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Status: {result.get('message', 'Complete')}")
    if result.get('regenerated'):
        for ep in result['regenerated']:
            print(f"\n✓ {ep.get('title')}")
            print(f"  URL: {ep.get('thumbnail_url')}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

