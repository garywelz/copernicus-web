#!/usr/bin/env python3
"""Fix the stored podcast count for gwelz@jjay.cuny.edu"""

import sys
import requests
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def get_subscriber_id(email):
    """Get subscriber ID for email"""
    import hashlib
    return hashlib.sha256(email.encode()).hexdigest()

def main():
    print("🔧 Fixing Podcast Count for gwelz@jjay.cuny.edu")
    print("="*80)
    
    email = "gwelz@jjay.cuny.edu"
    subscriber_id = get_subscriber_id(email)
    
    print(f"\n📧 Subscriber: {email}")
    print(f"   Subscriber ID: {subscriber_id}")
    
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    # Check current count
    print(f"\n📊 Checking current count...")
    url = f"{API_BASE_URL}/api/admin/subscribers/{subscriber_id}/podcasts"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error fetching podcasts: HTTP {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    actual_count = data.get("total_count", 0)
    
    print(f"   Actual podcast count: {actual_count}")
    
    # Check if there's a recalculate endpoint
    print(f"\n🔧 Attempting to recalculate count...")
    recalculate_url = f"{API_BASE_URL}/api/admin/subscribers/{subscriber_id}/recalculate-count"
    recalculate_response = requests.post(recalculate_url, headers=headers)
    
    if recalculate_response.status_code == 200:
        recalc_data = recalculate_response.json()
        print(f"✅ Recalculated count successfully!")
        print(f"   New count: {recalc_data.get('podcast_count', 'Unknown')}")
    elif recalculate_response.status_code == 404:
        print(f"⚠️  Recalculate endpoint not found - count will be fixed when endpoint is updated")
        print(f"   The list_all_subscribers endpoint should now calculate dynamically")
    else:
        print(f"⚠️  Recalculate failed: HTTP {recalculate_response.status_code}")
        print(f"   {recalculate_response.text}")
    
    # Verify by checking the subscriber list
    print(f"\n📊 Verifying in subscriber list...")
    list_url = f"{API_BASE_URL}/api/admin/subscribers"
    list_response = requests.get(list_url, headers=headers)
    
    if list_response.status_code == 200:
        list_data = list_response.json()
        subscribers = list_data.get("subscribers", [])
        for sub in subscribers:
            if sub.get("email") == email:
                displayed_count = sub.get("podcast_count", 0)
                print(f"   Count shown in list: {displayed_count}")
                if displayed_count == actual_count:
                    print(f"   ✅ Match! Count is correct")
                else:
                    print(f"   ⚠️  Mismatch! Should show {actual_count}")
                break
    
    print("\n" + "="*80)
    print("✅ Done!")
    print("="*80)

if __name__ == "__main__":
    main()

