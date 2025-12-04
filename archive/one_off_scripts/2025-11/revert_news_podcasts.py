#!/usr/bin/env python3
"""Revert news podcasts that were incorrectly changed from news-category-DDMMYYYY to ever-category-25#### format"""

import os
import sys
import requests
import json
import re

API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_key():
    """Get admin API key from environment or user input"""
    api_key = os.getenv("ADMIN_API_KEY")
    if not api_key:
        print("Please set ADMIN_API_KEY environment variable or enter it:")
        api_key = input("Admin API Key: ").strip()
    return api_key

def find_incorrectly_changed_news_podcasts():
    """Find news podcasts that were incorrectly changed to ever- format"""
    api_key = get_admin_key()
    headers = {"X-Admin-API-Key": api_key}
    
    # Get all podcasts from database
    print("Fetching all podcasts from database...")
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    podcasts = data.get("podcasts", [])
    
    # Pattern for news podcasts (DDMMYYYY format like news-bio-28032025)
    news_pattern = re.compile(r'^news-(bio|chem|compsci|math|phys)-\d{8}$')
    ever_pattern = re.compile(r'^ever-(bio|chem|compsci|math|phys)-\d{6}$')
    
    # Find podcasts that:
    # 1. Have "news" in the title/topic
    # 2. Currently have ever- format canonical filename
    # 3. Should have news- format
    
    incorrectly_changed = []
    
    for podcast in podcasts:
        title = (podcast.get('title') or '').lower()
        canonical = podcast.get('canonical_filename', '')
        
        # Check if it's a news podcast (has "news" in title)
        is_news = 'news' in title
        
        # Check if it currently has ever- format
        has_ever_format = bool(ever_pattern.match(canonical))
        
        if is_news and has_ever_format:
            incorrectly_changed.append({
                'title': podcast.get('title'),
                'current_canonical': canonical,
                'job_id': podcast.get('job_id'),
                'subscriber': podcast.get('subscriber_email'),
                'created_at': podcast.get('created_at')
            })
    
    return incorrectly_changed

def revert_news_podcast():
    """Find and list news podcasts that need to be reverted"""
    incorrectly_changed = find_incorrectly_changed_news_podcasts()
    
    if not incorrectly_changed:
        print("\n✅ No incorrectly changed news podcasts found!")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(incorrectly_changed)} news podcasts incorrectly changed:")
    print(f"{'='*80}\n")
    
    for i, podcast in enumerate(incorrectly_changed, 1):
        print(f"{i}. {podcast['title']}")
        print(f"   Current: {podcast['current_canonical']}")
        print(f"   Job ID: {podcast['job_id']}")
        print(f"   Subscriber: {podcast['subscriber_email']}")
        print()
    
    print("="*80)
    print("\n⚠️  To revert these, we need to:")
    print("1. Find the original news-category-DDMMYYYY filename from the RSS feed or file system")
    print("2. Update Firestore records")
    print("3. Update RSS feed if needed")
    print("\nPlease check the RSS feed or GCS bucket for the original news filenames.")

if __name__ == "__main__":
    revert_news_podcast()

