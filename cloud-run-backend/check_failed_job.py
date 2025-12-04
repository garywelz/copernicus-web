#!/usr/bin/env python3
"""Check a failed podcast job to see what went wrong"""
import sys
from datetime import datetime, timedelta
from google.cloud import firestore

def find_failed_job(topic_keyword: str = "Metalloenzyme"):
    """Find failed podcast jobs matching the topic keyword"""
    db = firestore.Client(project='copernicus-mvp')
    
    print(f"🔍 Searching for failed podcast job...")
    print(f"Keyword: {topic_keyword}")
    print("=" * 70)
    
    # Search in podcast_jobs collection
    jobs_ref = db.collection('podcast_jobs')
    
    # Get recent jobs from last 3 days
    three_days_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()
    recent_jobs = jobs_ref.where('created_at', '>=', three_days_ago).order_by('created_at', direction=firestore.Query.DESCENDING).limit(50).stream()
    
    found_jobs = []
    for job in recent_jobs:
        job_data = job.to_dict()
        request_data = job_data.get('request', {})
        topic = request_data.get('topic', '')
        
        if topic_keyword.lower() in topic.lower():
            status = job_data.get('status', 'unknown')
            error = job_data.get('error', '')
            error_type = job_data.get('error_type', '')
            
            found_jobs.append({
                'job_id': job.id,
                'topic': topic,
                'status': status,
                'created_at': job_data.get('created_at', ''),
                'updated_at': job_data.get('updated_at', ''),
                'error': error,
                'error_type': error_type,
                'subscriber_id': job_data.get('subscriber_id'),
                'result': job_data.get('result')
            })
    
    if found_jobs:
        print(f"\n✅ Found {len(found_jobs)} matching job(s):\n")
        for i, job in enumerate(found_jobs, 1):
            print(f"{'='*70}")
            print(f"Job #{i}")
            print(f"{'='*70}")
            print(f"Job ID:      {job['job_id']}")
            print(f"Topic:       {job['topic']}")
            print(f"Status:      {job['status']}")
            print(f"Created:     {job['created_at']}")
            print(f"Updated:     {job['updated_at']}")
            if job['subscriber_id']:
                print(f"Subscriber:  {job['subscriber_id']}")
            if job['error']:
                print(f"\n❌ ERROR:")
                print(f"   Type: {job['error_type']}")
                print(f"   Message: {job['error']}")
            if job['result']:
                print(f"\n📊 Result keys: {list(job['result'].keys())}")
            print()
    else:
        print(f"\n❌ No jobs found matching '{topic_keyword}' in the last 3 days.")
        print("\nChecking all failed jobs from last 3 days...")
        
        failed_jobs = jobs_ref.where('status', '==', 'failed').where('created_at', '>=', three_days_ago).order_by('created_at', direction=firestore.Query.DESCENDING).limit(10).stream()
        
        print(f"\n📋 Recent failed jobs:")
        for job in failed_jobs:
            job_data = job.to_dict()
            request_data = job_data.get('request', {})
            topic = request_data.get('topic', 'Unknown')
            error = job_data.get('error', 'No error message')
            print(f"\n  • {topic[:60]}")
            print(f"    Job ID: {job.id}")
            print(f"    Error: {error[:100]}")

if __name__ == '__main__':
    keyword = sys.argv[1] if len(sys.argv) > 1 else "Metalloenzyme"
    find_failed_job(keyword)

