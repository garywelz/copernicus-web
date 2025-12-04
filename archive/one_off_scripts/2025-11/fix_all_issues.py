#!/usr/bin/env python3
"""Fix all admin dashboard issues:
1. Revert 5 news podcasts from ever- format back to news- format
2. Fix 2 podcast titles (remove "Copernicus AI: Frontiers of Science - " prefix)
3. Update Firestore and RSS feed accordingly
"""

import os
import sys
import requests
import json
from google.cloud import secretmanager
from datetime import datetime

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def revert_news_podcasts():
    """Revert the 5 news podcasts back to their original news- format"""
    admin_key = get_admin_api_key()
    headers = {"X-Admin-API-Key": admin_key, "Content-Type": "application/json"}
    
    # Mapping of current (wrong) canonical to original (correct) canonical
    reversions = {
        "ever-bio-250041": "news-bio-28032025",
        "ever-chem-250022": "news-chem-28032025",
        "ever-compsci-250031": "news-compsci-28032025",
        "ever-math-250041": "news-math-28032025",
        "ever-phys-250043": "news-phys-28032025",
    }
    
    print("="*80)
    print("REVERTING NEWS PODCASTS")
    print("="*80)
    
    # This will need to be done via direct Firestore/RSS updates
    # For now, let's call an endpoint to do this
    # We'll need to create an endpoint for this
    
    print("\n⚠️  This requires an endpoint to be created.")
    print("Mapping to revert:")
    for current, original in reversions.items():
        print(f"  {current} -> {original}")

def fix_titles():
    """Fix podcast titles to remove 'Copernicus AI: Frontiers of Science - ' prefix"""
    admin_key = get_admin_api_key()
    headers = {"X-Admin-API-Key": admin_key, "Content-Type": "application/json"}
    
    print("\n" + "="*80)
    print("FIXING PODCAST TITLES")
    print("="*80)
    
    # Titles to fix:
    # 1. "Copernicus AI: Frontiers of Science - AI-Designed Materials: A Paradigm Shift"
    # 2. "Copernicus AI: Frontiers of Science - Prime Number Theory: A Paradigm Shift?"
    
    prefix = "Copernicus AI: Frontiers of Science - "
    
    # Get all podcasts from database
    print("\nFetching all podcasts from database...")
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    podcasts = data.get("podcasts", [])
    
    titles_to_fix = []
    for podcast in podcasts:
        title = podcast.get('title', '')
        if title.startswith(prefix):
            new_title = title.replace(prefix, '', 1)
            titles_to_fix.append({
                'canonical': podcast.get('canonical_filename'),
                'job_id': podcast.get('job_id'),
                'old_title': title,
                'new_title': new_title
            })
    
    if not titles_to_fix:
        print("\n✅ No titles need fixing!")
        return
    
    print(f"\nFound {len(titles_to_fix)} titles to fix:")
    for item in titles_to_fix:
        print(f"\n  Canonical: {item['canonical']}")
        print(f"  Old: {item['old_title']}")
        print(f"  New: {item['new_title']}")
    
    print("\n⚠️  This requires an endpoint to update titles in Firestore.")
    print("   Titles are stored in:")
    print("   - podcast_jobs.result.title")
    print("   - episodes.title")

if __name__ == "__main__":
    print("🔧 Fix All Issues Script")
    print("="*80)
    
    fix_titles()
    revert_news_podcasts()
    
    print("\n" + "="*80)
    print("✅ Script complete!")
    print("="*80)
    print("\nNote: Actual fixes require backend endpoints to be created.")

