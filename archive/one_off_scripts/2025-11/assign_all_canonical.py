#!/usr/bin/env python3
"""Script to assign canonical filenames to all podcasts missing them"""

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

def assign_canonical_to_all():
    """Assign canonical filenames to all podcasts missing them"""
    api_key = get_admin_key()
    
    url = f"{API_BASE_URL}/api/admin/podcasts/assign-canonical-filenames"
    headers = {"X-Admin-API-Key": api_key, "Content-Type": "application/json"}
    
    payload = {
        "fix_all_missing": True
    }
    
    print("Assigning canonical filenames to all podcasts missing them...")
    print("This may take a few minutes...")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    
    print(f"\n{'='*80}")
    print("Assignment Results:")
    print(f"{'='*80}\n")
    
    print(f"Total processed: {data.get('total', 0)}")
    print(f"Successfully assigned: {data.get('success_count', 0)}")
    print(f"Failed: {data.get('failure_count', 0)}")
    
    assigned = data.get('assigned', [])
    failed = data.get('failed', [])
    
    if assigned:
        print(f"\n✅ Successfully assigned canonical filenames ({len(assigned)}):")
        for item in assigned[:10]:  # Show first 10
            print(f"  - {item.get('guid', 'Unknown')} -> {item.get('canonical_filename', 'Unknown')}")
        if len(assigned) > 10:
            print(f"  ... and {len(assigned) - 10} more")
    
    if failed:
        print(f"\n❌ Failed to assign ({len(failed)}):")
        for item in failed[:10]:  # Show first 10
            print(f"  - {item.get('guid', 'Unknown')}: {item.get('error', 'Unknown error')}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    confirm = input("This will assign canonical filenames to ALL podcasts missing them. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        assign_canonical_to_all()
    else:
        print("Cancelled.")

