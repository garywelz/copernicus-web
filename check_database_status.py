#!/usr/bin/env python3
"""Check what podcasts are in the database and their canonical filename status"""

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

def check_database_status():
    """Check database status and show canonical filename patterns"""
    api_key = get_admin_key()
    
    headers = {"X-Admin-API-Key": api_key, "Content-Type": "application/json"}
    
    print("Checking podcast database...")
    print("="*80)
    
    # Get all podcasts from database
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    podcasts = data.get("podcasts", [])
    total = data.get("total_count", 0)
    
    print(f"\nTotal podcasts in database: {total}\n")
    
    # Pattern for canonical filenames
    canonical_pattern = re.compile(r'^ever-(bio|chem|compsci|math|phys)-\d{6}$')
    
    # Categorize podcasts
    with_canonical = []
    without_canonical = []
    
    for podcast in podcasts:
        canonical = podcast.get('canonical_filename', '')
        is_canonical = bool(canonical_pattern.match(canonical)) if canonical else False
        
        if is_canonical:
            with_canonical.append(podcast)
        else:
            without_canonical.append(podcast)
    
    print(f"Podcasts WITH canonical filenames (ever-category-25####): {len(with_canonical)}")
    print(f"Podcasts WITHOUT canonical filenames: {len(without_canonical)}")
    print()
    
    if without_canonical:
        print("="*80)
        print("PODCASTS WITHOUT CANONICAL FILENAMES:")
        print("="*80)
        for i, podcast in enumerate(without_canonical[:20], 1):  # Show first 20
            print(f"\n{i}. {podcast.get('title', 'Untitled')}")
            print(f"   Current identifier: {podcast.get('canonical_filename', 'Unknown')}")
            print(f"   Subscriber: {podcast.get('subscriber_email', 'Unknown')}")
            print(f"   Job ID: {podcast.get('job_id', 'N/A')}")
        
        if len(without_canonical) > 20:
            print(f"\n... and {len(without_canonical) - 20} more")
        
        print("\n" + "="*80)
        print("To assign canonical filenames to these podcasts, run:")
        print("  python3 assign_all_canonical.py")
    else:
        print("✅ All podcasts have canonical filenames!")

if __name__ == "__main__":
    check_database_status()

