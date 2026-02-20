#!/usr/bin/env python3
"""
Compare gwelz@jjay.cuny.edu podcasts using the API endpoints.
This avoids Firestore authentication issues.
"""

import requests
import json
import os
from google.cloud import secretmanager

# Get admin API key
def get_admin_api_key():
    project_id = "regal-scholar-453620-r7"
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

API_BASE_URL = os.getenv("API_BASE_URL", "https://copernicus-podcast-api-6bxtm6k7qa-uc.a.run.app")

def main():
    api_key = get_admin_api_key()
    headers = {"X-API-Key": api_key}
    
    print("="*70)
    print("COMPARING gwelz@jjay.cuny.edu PODCASTS VIA API")
    print("="*70)
    
    # 1. Get all subscribers to find gwelz's ID
    print("\n1. Getting subscribers list...")
    response = requests.get(f"{API_BASE_URL}/api/admin/subscribers", headers=headers)
    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        return
    
    subscribers = response.json().get('subscribers', [])
    gwelz_subscriber = None
    for sub in subscribers:
        if sub.get('email') == 'gwelz@jjay.cuny.edu':
            gwelz_subscriber = sub
            break
    
    if not gwelz_subscriber:
        print("   ❌ gwelz@jjay.cuny.edu not found")
        return
    
    subscriber_id = gwelz_subscriber.get('subscriber_id')
    print(f"   ✅ Found subscriber ID: {subscriber_id}")
    print(f"   Count shown: {gwelz_subscriber.get('podcasts_generated', 'N/A')}")
    
    # 2. Get all podcasts for gwelz (what "View Podcasts" shows)
    print(f"\n2. Getting all podcasts for gwelz@jjay.cuny.edu...")
    response = requests.get(f"{API_BASE_URL}/api/admin/subscribers/{subscriber_id}/podcasts", headers=headers)
    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")
        return
    
    data = response.json()
    gwelz_podcasts = data.get('podcasts', [])
    gwelz_canonicals = set()
    for podcast in gwelz_podcasts:
        canonical = podcast.get('podcast_id') or podcast.get('id') or podcast.get('canonical_filename')
        if canonical:
            gwelz_canonicals.add(canonical)
    
    print(f"   ✅ Found {len(gwelz_canonicals)} podcasts")
    
    # 3. Get all podcasts from database
    print(f"\n3. Getting all podcasts from database...")
    response = requests.get(f"{API_BASE_URL}/api/admin/podcasts/database", headers=headers)
    if response.status_code != 200:
        print(f"   ❌ Error: {response.status_code}")
        return
    
    data = response.json()
    all_podcasts = data.get('podcasts', [])
    all_canonicals = set()
    for podcast in all_podcasts:
        canonical = podcast.get('canonical_filename') or podcast.get('podcast_id') or podcast.get('id')
        if canonical:
            all_canonicals.add(canonical)
    
    print(f"   ✅ Found {len(all_canonicals)} podcasts in database")
    
    # 4. Compare
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)
    
    missing_in_db = gwelz_canonicals - all_canonicals
    
    if missing_in_db:
        print(f"\n⚠️  Found {len(missing_in_db)} podcast(s) in gwelz account but NOT in database:")
        for canonical in sorted(missing_in_db):
            # Find podcast info
            podcast_info = next((p for p in gwelz_podcasts if (p.get('podcast_id') or p.get('id') or p.get('canonical_filename')) == canonical), None)
            title = podcast_info.get('title', 'N/A') if podcast_info else 'N/A'
            print(f"\n   {canonical}:")
            print(f"      Title: {title}")
            print(f"      ⚠️  In account but NOT in database")
    else:
        print(f"\n✅ All podcasts in account are in database")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Podcasts in gwelz account: {len(gwelz_canonicals)}")
    print(f"Podcasts in database: {len(all_canonicals)}")
    print(f"Missing from database: {len(missing_in_db)}")
    
    if missing_in_db:
        print(f"\nLIST OF MISSING PODCASTS:")
        for canonical in sorted(missing_in_db):
            podcast_info = next((p for p in gwelz_podcasts if (p.get('podcast_id') or p.get('id') or p.get('canonical_filename')) == canonical), None)
            title = podcast_info.get('title', 'N/A') if podcast_info else 'N/A'
            print(f"   - {canonical}: {title}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()




