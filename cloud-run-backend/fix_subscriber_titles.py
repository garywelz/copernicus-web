#!/usr/bin/env python3
"""
Script to fix missing podcast titles for a subscriber
and run other title/deletion fixes via admin API endpoints
"""

import sys
import os
import requests
import json

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import secretmanager
from google.cloud import firestore

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"

def get_admin_api_key():
    """Get admin API key from Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def get_subscriber_id(email):
    """Get subscriber_id from email using subscriber helper"""
    from utils.subscriber_helpers import get_subscriber_by_email
    
    subscriber_doc = get_subscriber_by_email(email)
    if subscriber_doc:
        return subscriber_doc.id
    return None

def call_endpoint(endpoint, method="POST", params=None, data=None):
    """Call an admin API endpoint"""
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    url = f"{API_BASE_URL}{endpoint}"
    
    if params:
        query_string = "&".join([f"{k}={v}" for k, v in params.items() if v])
        if query_string:
            url += f"?{query_string}"
    
    print(f"\n{'='*70}")
    print(f"Calling: {method} {url}")
    print(f"{'='*70}")
    
    try:
        if method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=120)
        elif method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=120)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        return None

def main():
    email = "gwelz@jjay.cuny.edu"
    
    print(f"🔧 Fixing podcast titles for {email}...\n")
    
    # Step 1: Get subscriber_id
    print("Step 1: Getting subscriber_id...")
    subscriber_id = get_subscriber_id(email)
    
    if not subscriber_id:
        print(f"❌ Subscriber not found: {email}")
        return
    
    print(f"✅ Found subscriber_id: {subscriber_id}")
    
    # Step 2: Fix missing titles for this subscriber (using email)
    print("\nStep 2: Fixing missing titles...")
    result1 = call_endpoint(
        "/api/admin/podcasts/fix-missing-titles",
        method="POST",
        params={"subscriber_email": email}
    )
    
    # Step 3: Fix title prefixes and delete podcast
    print("\nStep 3: Fixing title prefixes and deleting podcast without audio...")
    result2 = call_endpoint(
        "/api/admin/podcasts/fix-titles-and-delete",
        method="POST"
    )
    
    print(f"\n{'='*70}")
    print("✅ All operations complete!")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()

