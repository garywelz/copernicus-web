#!/usr/bin/env python3
"""
Check failed podcast jobs, specifically looking for the Metalloenzymes failure.
Automatically retrieves admin API key from Secret Manager.
"""
import sys
import requests
import json
from google.cloud import secretmanager

# Configuration
API_URL = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"
ENDPOINT = "/api/admin/podcasts/failed"
GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    """Get admin API key from Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        return key
    except Exception as e:
        print(f"❌ Failed to retrieve admin API key from Secret Manager: {e}")
        return None

def check_failed_podcasts(topic_keyword="Metalloenzyme"):
    """Check failed podcast jobs and find matching ones"""
    print(f"🔍 Checking failed podcast jobs...")
    print(f"   Looking for: {topic_keyword}")
    print("=" * 70)
    
    # Get admin API key
    admin_api_key = get_admin_api_key()
    if not admin_api_key:
        print("\n❌ Could not retrieve admin API key.")
        print("   Please ensure you have access to Secret Manager.")
        return
    
    headers = {
        "X-Admin-API-Key": admin_api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Query the endpoint
        response = requests.get(
            f"{API_URL}{ENDPOINT}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        data = response.json()
        failed_jobs = data.get('failed_jobs', [])
        total = data.get('total_count', 0)
        
        print(f"\n📊 Found {total} failed podcast job(s)\n")
        
        if total == 0:
            print("✅ No failed jobs found!")
            return
        
        # Search for matching podcast
        matching_found = False
        for job in failed_jobs:
            topic = job.get('topic', '')
            title = job.get('title', '')
            
            if topic_keyword.lower() in topic.lower() or topic_keyword.lower() in str(title).lower():
                matching_found = True
                print("=" * 70)
                print(f"🎯 FOUND MATCHING PODCAST!")
                print("=" * 70)
                print(f"Job ID:       {job.get('job_id')}")
                print(f"Topic:        {job.get('topic')}")
                print(f"Title:        {job.get('title')}")
                print(f"Category:     {job.get('category')}")
                print(f"Duration:     {job.get('duration')}")
                print(f"Expertise:    {job.get('expertise_level')}")
                print(f"Status:       {job.get('status')}")
                print(f"Created:      {job.get('created_at')}")
                print(f"Updated:      {job.get('updated_at')}")
                if job.get('subscriber_id'):
                    print(f"Subscriber:   {job.get('subscriber_id')}")
                
                error = job.get('error', 'No error message')
                error_type = job.get('error_type', '')
                
                print(f"\n❌ ERROR DETAILS:")
                if error_type:
                    print(f"   Type: {error_type}")
                print(f"   Message:")
                # Print error message with proper formatting
                for line in str(error).split('\n'):
                    print(f"      {line}")
                print()
        
        if not matching_found:
            print(f"⚠️  No podcasts found matching '{topic_keyword}' in failed jobs.")
            print("\n📋 Showing all failed jobs:\n")
            
            for i, job in enumerate(failed_jobs, 1):
                print(f"{'='*70}")
                print(f"Failed Job #{i}")
                print(f"{'='*70}")
                print(f"Job ID:       {job.get('job_id')}")
                print(f"Topic:        {job.get('topic')}")
                print(f"Category:     {job.get('category')}")
                print(f"Created:      {job.get('created_at')}")
                error = job.get('error', 'No error message')
                error_preview = error[:150] + '...' if len(error) > 150 else error
                print(f"Error:        {error_preview}")
                print()
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to API: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Metalloenzyme"
    check_failed_podcasts(keyword)

