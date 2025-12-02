#!/usr/bin/env python3
"""Regenerate thumbnails for episodes that now have canonical filenames"""

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

# Episodes that now have canonical filenames (use the canonical filenames, not UUIDs)
canonical_filenames = [
    'ever-phys-250042',  # Quantum Computing Advances
    'ever-chem-250021',  # Silicon compounds
    'ever-phys-250043',  # Quantum Computing chip advances
    'ever-phys-250044',  # Prime Number Theory update
    'ever-phys-250045',  # New materials created using AI
    'ever-phys-250046',  # Matrix Multiplication advances
    'ever-bio-250040'    # Revolutionizing COVID-19 Treatment (fix fallback)
]

payload = {
    'episode_guids': canonical_filenames
}

print("🖼️  Regenerating thumbnails with canonical filenames...")
print(f"Episodes: {len(canonical_filenames)}")
print("⏳ This may take several minutes (DALL-E generation)...\n")

response = requests.post(url, headers=headers, json=payload, timeout=600)

print(f'Status Code: {response.status_code}\n')

if response.status_code == 200:
    result = response.json()
    print("✅ SUCCESS!\n")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Regenerated: {result.get('success_count', 0)} thumbnails")
    print(f"  Failed: {result.get('failure_count', 0)} thumbnails")
    print("="*60)
    
    if result.get('regenerated'):
        print("\n✅ SUCCESSFULLY REGENERATED:")
        for success in result['regenerated']:
            print(f"  - {success.get('title', success.get('guid'))}")
            print(f"    Canonical: {success.get('guid')}")
            thumb_url = success.get('thumbnail_url', '')
            if 'fallback' in thumb_url:
                print(f"    ⚠️  Using fallback: {thumb_url}")
            else:
                print(f"    ✅ Custom thumbnail: {thumb_url}")
            print()
    
    if result.get('failed'):
        print("\n❌ FAILED:")
        for fail in result['failed']:
            print(f"  - {fail.get('guid')}: {fail.get('error', 'Unknown error')}")
else:
    print("❌ ERROR:")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text)

