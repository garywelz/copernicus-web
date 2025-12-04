#!/usr/bin/env python3
"""Find all podcasts that might be missing from the database - those using job IDs or UUIDs"""

import os
import sys
import requests
import json
import re
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def main():
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    print("🔍 Finding All Missing Podcasts")
    print("="*80)
    
    # Get all podcasts from database
    print("\n📊 Fetching all podcasts from database...")
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    db_data = response.json()
    db_podcasts = db_data.get("podcasts", [])
    db_count = db_data.get("total_count", len(db_podcasts))
    
    print(f"✅ Found {db_count} podcasts in database")
    
    # Get podcasts missing canonical filenames
    print("\n🔍 Checking for podcasts with non-canonical filenames...")
    url = f"{API_BASE_URL}/api/admin/podcasts/missing-canonical"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    missing_data = response.json()
    missing_podcasts = missing_data.get("podcasts_missing_canonical", [])
    
    print(f"✅ Found {len(missing_podcasts)} podcasts missing canonical filenames")
    
    if missing_podcasts:
        print("\n📋 Podcasts Missing Canonical Filenames:")
        print("="*80)
        
        # Group by category
        by_category = {}
        for podcast in missing_podcasts:
            category = podcast.get('category', 'Unknown')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(podcast)
        
        for category, podcasts in by_category.items():
            print(f"\n{category} ({len(podcasts)} podcasts):")
            for i, podcast in enumerate(podcasts, 1):
                print(f"  {i}. {podcast.get('title', 'Untitled')}")
                print(f"     Identifier: {podcast.get('identifier')}")
                print(f"     Current Canonical: {podcast.get('current_canonical', 'None')}")
                print(f"     Job ID: {podcast.get('job_id', 'N/A')}")
                print(f"     Subscriber: {podcast.get('subscriber_email', 'Unknown')}")
                print(f"     Created: {podcast.get('created_at', 'Unknown')}")
        
        # Search for "Parkinson" in titles
        print("\n" + "="*80)
        print("🔍 Searching for 'Parkinson' in all podcasts...")
        parkinson_podcasts = []
        for podcast in db_podcasts:
            title = (podcast.get('title') or '').lower()
            if 'parkinson' in title:
                parkinson_podcasts.append(podcast)
        
        for podcast in missing_podcasts:
            title = (podcast.get('title') or '').lower()
            if 'parkinson' in title:
                parkinson_podcasts.append(podcast)
        
        if parkinson_podcasts:
            print(f"\n✅ Found {len(parkinson_podcasts)} podcast(s) with 'Parkinson' in title:")
            for podcast in parkinson_podcasts:
                print(f"  - {podcast.get('title', 'Untitled')}")
                print(f"    Canonical/Filename: {podcast.get('canonical_filename', podcast.get('identifier', 'Unknown'))}")
        else:
            print("\n❌ No podcasts found with 'Parkinson' in title")
    
    print("\n" + "="*80)
    print(f"📊 Summary:")
    print(f"  Total in database: {db_count}")
    print(f"  Missing canonical filenames: {len(missing_podcasts)}")
    print("="*80)

if __name__ == "__main__":
    main()

