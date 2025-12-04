#!/usr/bin/env python3
"""Assign canonical filenames to episodes with UUID GUIDs"""

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
url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/podcasts/assign-canonical-filenames'
headers = {
    'X-Admin-API-Key': admin_key,
    'Content-Type': 'application/json'
}

payload = {
    'fix_all_missing': True
}

print("🏷️  Assigning canonical filenames to episodes with UUID GUIDs...")
print(f"📡 Calling: {url}\n")

response = requests.post(url, headers=headers, json=payload, timeout=300)

print(f'Status Code: {response.status_code}\n')

if response.status_code == 200:
    result = response.json()
    print("✅ SUCCESS!\n")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Assigned: {result.get('success_count', 0)} canonical filenames")
    print(f"  Failed: {result.get('failure_count', 0)}")
    print("="*60)
    
    if result.get('assigned'):
        print("\n✅ ASSIGNED CANONICAL FILENAMES:")
        for item in result['assigned']:
            print(f"  - {item.get('title', item.get('guid'))[:60]}")
            print(f"    GUID: {item.get('guid')}")
            print(f"    Canonical: {item.get('canonical_filename')}")
            print(f"    Category: {item.get('category')}")
            print()
else:
    print("❌ ERROR:")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text)

