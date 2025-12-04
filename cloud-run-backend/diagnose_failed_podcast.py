#!/usr/bin/env python3
"""
Diagnose a failed podcast by querying the admin API endpoint.
This script uses the admin endpoint to find failed jobs.
"""
import sys
import requests
import json
from datetime import datetime

def find_failed_podcast(topic_keyword="Metalloenzyme", admin_api_key=None):
    """
    Find failed podcast jobs by querying the admin API
    """
    base_url = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"
    
    if not admin_api_key:
        print("❌ Admin API key is required")
        print("\nUsage:")
        print("  python3 diagnose_failed_podcast.py [topic_keyword] [admin_api_key]")
        print("\nExample:")
        print("  python3 diagnose_failed_podcast.py 'Metalloenzyme' YOUR_ADMIN_API_KEY")
        return
    
    headers = {
        "X-Admin-API-Key": admin_api_key,
        "Content-Type": "application/json"
    }
    
    print(f"🔍 Searching for failed podcast...")
    print(f"Keyword: {topic_keyword}")
    print("=" * 70)
    
    try:
        # Get all podcasts from admin endpoint
        response = requests.get(
            f"{base_url}/api/admin/podcasts",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch podcasts: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        data = response.json()
        podcasts = data.get('podcasts', [])
        
        print(f"✅ Found {len(podcasts)} total podcasts")
        print(f"\nSearching for jobs matching '{topic_keyword}'...\n")
        
        # Search for matching podcasts
        matching = []
        for podcast in podcasts:
            title = podcast.get('title', '')
            topic = podcast.get('topic', '')
            status = podcast.get('status', '')
            
            if topic_keyword.lower() in title.lower() or topic_keyword.lower() in topic.lower():
                matching.append(podcast)
        
        if matching:
            print(f"✅ Found {len(matching)} matching podcast(s):\n")
            for i, podcast in enumerate(matching, 1):
                print(f"{'='*70}")
                print(f"Podcast #{i}")
                print(f"{'='*70}")
                print(f"Job ID:      {podcast.get('job_id', 'N/A')}")
                print(f"Title:       {podcast.get('title', 'N/A')}")
                print(f"Topic:       {podcast.get('topic', 'N/A')}")
                print(f"Status:      {podcast.get('status', 'N/A')}")
                print(f"Created:     {podcast.get('created_at', 'N/A')}")
                
                if podcast.get('error'):
                    print(f"\n❌ ERROR:")
                    print(f"   {podcast.get('error', 'N/A')}")
                    if podcast.get('error_type'):
                        print(f"   Type: {podcast.get('error_type')}")
                
                if podcast.get('result'):
                    result = podcast.get('result', {})
                    print(f"\n📊 Result:")
                    print(f"   Keys: {list(result.keys())}")
                    if result.get('canonical_filename'):
                        print(f"   Canonical: {result.get('canonical_filename')}")
                
                print()
        else:
            print(f"❌ No podcasts found matching '{topic_keyword}'")
            print("\n📋 Checking all failed podcasts...\n")
            
            failed = [p for p in podcasts if p.get('status') == 'failed']
            if failed:
                print(f"Found {len(failed)} failed podcast(s):\n")
                for podcast in failed[:5]:  # Show first 5
                    print(f"  • {podcast.get('title', 'Unknown')}")
                    print(f"    Job ID: {podcast.get('job_id', 'N/A')}")
                    print(f"    Error: {podcast.get('error', 'No error message')[:100]}")
                    print()
            else:
                print("No failed podcasts found")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to API: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Metalloenzyme"
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not api_key:
        print("Enter admin API key:")
        api_key = input().strip()
    
    find_failed_podcast(keyword, api_key)

