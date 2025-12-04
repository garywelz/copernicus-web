#!/usr/bin/env python3
"""Find canonical filenames for episodes and check if thumbnails exist"""

import requests
import json
from google.cloud import secretmanager
from google.cloud import storage

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

admin_key = get_admin_api_key()
url = 'https://copernicus-podcast-api-204731194849.us-central1.run.app/api/admin/podcasts'
headers = {'X-Admin-API-Key': admin_key}

print("🔍 Finding canonical filenames for episodes with UUID GUIDs...\n")
print("="*80)

response = requests.get(url, headers=headers, timeout=300)
if response.status_code == 200:
    data = response.json()
    podcasts = data.get('podcasts', [])
    
    # The UUID GUIDs we're looking for
    uuid_guids = [
        '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
        '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
        '85b0f041-75be-4e79-9175-f46498ba9d39',
        '977d7344-63f2-4aa7-80fc-9ea260b22806',
        '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
        'c28ba67b-5fc2-4f87-a53b-748430a57c86'
    ]
    
    storage_client = storage.Client()
    bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
    
    for uuid_guid in uuid_guids:
        print(f"\n📋 UUID GUID: {uuid_guid}")
        
        # Find this podcast in the list
        found_podcast = None
        for podcast in podcasts:
            podcast_id = podcast.get('podcast_id') or podcast.get('id')
            result = podcast.get('result', {})
            canonical = result.get('canonical_filename')
            
            if podcast_id == uuid_guid or canonical == uuid_guid:
                found_podcast = podcast
                break
        
        if found_podcast:
            result = found_podcast.get('result', {})
            canonical = result.get('canonical_filename')
            title = found_podcast.get('title') or result.get('title') or found_podcast.get('request', {}).get('topic', 'Unknown')
            
            print(f"  Title: {title[:60]}")
            print(f"  Canonical filename: {canonical}")
            
            # Check if thumbnail exists with canonical naming
            if canonical and canonical != uuid_guid:
                canonical_thumb = f"thumbnails/{canonical}-thumb.jpg"
                blob = bucket.blob(canonical_thumb)
                exists = blob.exists()
                print(f"  ✅ Canonical thumbnail exists: {exists} ({canonical_thumb})")
                
                if exists:
                    print(f"  ⚠️  ISSUE: Thumbnail exists with canonical name, but RSS might be using UUID GUID!")
            else:
                print(f"  ⚠️  No canonical filename found (or same as GUID)")
        else:
            print(f"  ❌ Podcast not found in admin list")

print("\n" + "="*80)

