#!/usr/bin/env python3
"""Call the comprehensive fix endpoint to fix all podcast issues"""

import os
import sys
import requests
import json
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def main():
    print("🔧 Fixing All Podcast Issues")
    print("="*80)
    print("\nThis will:")
    print("1. Revert 5 news podcasts from ever- format back to news- format")
    print("2. Fix podcast titles to remove 'Copernicus AI: Frontiers of Science - ' prefix")
    print("3. Update Firestore and RSS feed accordingly")
    print("\n" + "="*80)
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    print("\n📡 Calling fix endpoint...")
    url = f"{API_BASE_URL}/api/admin/podcasts/fix-all-issues"
    response = requests.post(url, headers=headers)
    
    if response.status_code != 200:
        print(f"\n❌ Error: HTTP {response.status_code}")
        try:
            error_data = response.json()
            print(f"Detail: {error_data.get('detail', 'Unknown error')}")
        except:
            print(response.text)
        return
    
    result = response.json()
    
    print("\n" + "="*80)
    print("✅ FIX COMPLETE")
    print("="*80)
    
    print(f"\n📊 Summary:")
    print(f"  News podcasts reverted: {result.get('total_news_reverted', 0)}")
    print(f"  Titles fixed: {result.get('total_titles_fixed', 0)}")
    print(f"  Errors: {result.get('total_errors', 0)}")
    
    if result.get('news_reverted'):
        print(f"\n📰 News Podcasts Reverted:")
        for item in result['news_reverted']:
            print(f"  {item['old_canonical']} → {item['new_canonical']}")
    
    if result.get('titles_fixed'):
        print(f"\n📝 Titles Fixed:")
        for item in result['titles_fixed']:
            print(f"  {item['canonical']}:")
            print(f"    Old: {item['old_title']}")
            print(f"    New: {item['new_title']}")
    
    if result.get('errors'):
        print(f"\n⚠️  Errors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print("\n" + "="*80)
    print("✅ All fixes applied!")
    print("="*80)

if __name__ == "__main__":
    main()

