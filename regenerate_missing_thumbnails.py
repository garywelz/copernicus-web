#!/usr/bin/env python3
"""Regenerate thumbnails for the 8 missing episodes"""

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
        print(f"Error getting admin API key: {e}")
        return None

admin_key = get_admin_api_key()
if not admin_key:
    print("Failed to retrieve admin API key")
    exit(1)

# The 8 episodes that need thumbnails
episode_guids = [
    'ever-bio-250040',
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    'ever-math-250036',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/rss/regenerate-thumbnails'
headers = {
    'X-Admin-API-Key': admin_key,
    'Content-Type': 'application/json'
}

payload = {
    'episode_guids': episode_guids
}

print("🖼️  Regenerating thumbnails for 8 episodes...")
print(f"📡 Calling: {url}\n")
print("Episodes:")
for i, guid in enumerate(episode_guids, 1):
    print(f"  {i}. {guid}")

print("\n⏳ This may take a few minutes (DALL-E thumbnail generation)...\n")

response = requests.post(url, headers=headers, json=payload, timeout=600)  # 10 minute timeout

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
    
    if result.get('failed'):
        print("\n❌ FAILED EPISODES:")
        for fail in result['failed']:
            print(f"  - {fail.get('guid')}: {fail.get('error', 'Unknown error')}")
    
    if result.get('regenerated'):
        print("\n✅ SUCCESSFULLY REGENERATED:")
        for success in result['regenerated']:
            print(f"  - {success.get('title', success.get('guid'))}")
            print(f"    URL: {success.get('thumbnail_url', 'N/A')}")
else:
    print("❌ ERROR:")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text)

