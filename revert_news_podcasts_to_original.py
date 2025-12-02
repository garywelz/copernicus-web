#!/usr/bin/env python3
"""Find and revert news podcasts that were incorrectly changed from news-category-DDMMYYYY to ever-category-25#### format"""

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

def find_and_revert_news_podcasts():
    """Find news podcasts that were incorrectly changed and revert them"""
    admin_key = get_admin_api_key()
    headers = {"X-Admin-API-Key": admin_key, "Content-Type": "application/json"}
    
    print("🔍 Finding news podcasts that were incorrectly changed...")
    print("="*80)
    
    # Get all podcasts from database
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    podcasts = data.get("podcasts", [])
    
    # Pattern for news podcasts (DDMMYYYY format like news-bio-28032025)
    news_pattern = re.compile(r'^news-(bio|chem|compsci|math|phys)-\d{8}$')
    ever_pattern = re.compile(r'^ever-(bio|chem|compsci|math|phys)-\d{6}$')
    
    # Find podcasts that:
    # 1. Have "news" in the title/topic (case-insensitive)
    # 2. Currently have ever- format canonical filename
    # 3. Should have news- format
    
    incorrectly_changed = []
    
    for podcast in podcasts:
        title = (podcast.get('title') or '').lower()
        canonical = podcast.get('canonical_filename', '')
        job_id = podcast.get('job_id')
        
        # Check if it's a news podcast
        is_news = 'news' in title or 'News' in podcast.get('title', '')
        
        # Check if it currently has ever- format
        has_ever_format = bool(ever_pattern.match(canonical))
        
        if is_news and has_ever_format:
            incorrectly_changed.append({
                'title': podcast.get('title'),
                'current_canonical': canonical,
                'job_id': job_id,
                'subscriber': podcast.get('subscriber_email'),
                'created_at': podcast.get('created_at')
            })
    
    if not incorrectly_changed:
        print("\n✅ No incorrectly changed news podcasts found!")
        return
    
    print(f"\nFound {len(incorrectly_changed)} news podcasts that were incorrectly changed:")
    print("="*80)
    for i, podcast in enumerate(incorrectly_changed, 1):
        print(f"\n{i}. {podcast['title']}")
        print(f"   Current (wrong): {podcast['current_canonical']}")
        print(f"   Job ID: {podcast['job_id']}")
        print(f"   Subscriber: {podcast['subscriber_email']}")
    
    print("\n" + "="*80)
    print("\n⚠️  To revert these, we need to:")
    print("1. Check the RSS feed for original news-category-DDMMYYYY filenames")
    print("2. Check GCS bucket for audio files with news- prefix")
    print("3. Extract the date from the creation date or file metadata")
    print("\nThis script will help identify which podcasts need to be reverted.")
    print("The actual revert will need to be done manually or via an admin endpoint.")

if __name__ == "__main__":
    find_and_revert_news_podcasts()

