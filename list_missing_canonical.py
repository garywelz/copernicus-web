#!/usr/bin/env python3
"""Script to list all podcasts missing canonical filenames"""

import os
import sys
import requests
import json

API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_key():
    """Get admin API key from environment or user input"""
    api_key = os.getenv("ADMIN_API_KEY")
    if not api_key:
        print("Please set ADMIN_API_KEY environment variable or enter it:")
        api_key = input("Admin API Key: ").strip()
    return api_key

def list_missing_canonical():
    """List all podcasts missing canonical filenames"""
    api_key = get_admin_key()
    
    url = f"{API_BASE_URL}/api/admin/podcasts/missing-canonical"
    headers = {"X-Admin-API-Key": api_key}
    
    print("Fetching podcasts missing canonical filenames...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    
    podcasts = data.get("podcasts_missing_canonical", [])
    total = data.get("total_count", 0)
    
    print(f"\n{'='*80}")
    print(f"Found {total} podcasts missing canonical filenames")
    print(f"{'='*80}\n")
    
    if total == 0:
        print("✅ All podcasts have canonical filenames!")
        return
    
    # Group by category
    by_category = {}
    for podcast in podcasts:
        category = podcast.get('category', 'Unknown')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(podcast)
    
    # Print summary
    print("Summary by category:")
    for category, items in sorted(by_category.items()):
        print(f"  {category}: {len(items)}")
    print()
    
    # Print detailed list
    print("Detailed List:")
    print(f"{'='*80}")
    for i, podcast in enumerate(podcasts, 1):
        print(f"\n{i}. {podcast.get('title', 'Untitled')}")
        print(f"   Identifier: {podcast.get('identifier')}")
        print(f"   Job ID: {podcast.get('job_id', 'N/A')}")
        print(f"   Current Canonical: {podcast.get('current_canonical', 'None')}")
        print(f"   Category: {podcast.get('category', 'Unknown')}")
        print(f"   Subscriber: {podcast.get('subscriber_email', 'Unknown')}")
        print(f"   Source: {podcast.get('source', 'Unknown')}")
        print(f"   Created: {podcast.get('created_at', 'Unknown')}")
    
    print(f"\n{'='*80}")
    print(f"\nTo assign canonical filenames to all, use:")
    print(f"  python3 assign_canonical_to_all.py")

if __name__ == "__main__":
    list_missing_canonical()

