#!/usr/bin/env python3
"""Check recent podcast jobs for supramolecular chemistry and metalloenzymes"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

# Topics to search for
topics_to_find = [
    "supramolecular",
    "metalloenzyme",
    "self-assembly",
    "bioinspired"
]

print(f"\n🔍 Searching for recent podcast jobs with chemistry topics...")
print(f"   Looking for: {', '.join(topics_to_find)}")
print("=" * 80)

# Get recent jobs from last 24 hours
one_day_ago = datetime.utcnow() - timedelta(days=1)
recent_jobs = db.collection('podcast_jobs').where(
    'created_at', '>=', one_day_ago.isoformat()
).order_by('created_at', direction=firestore.Query.DESCENDING).limit(100).stream()

found_jobs = []
for job in recent_jobs:
    job_data = job.to_dict()
    request = job_data.get('request', {})
    topic = request.get('topic', '') if isinstance(request, dict) else ''
    
    # Check if topic matches any of our search terms
    topic_lower = topic.lower()
    if any(search_term.lower() in topic_lower for search_term in topics_to_find):
        status = job_data.get('status', 'unknown')
        created_at = job_data.get('created_at', 'Unknown')
        updated_at = job_data.get('updated_at', 'Unknown')
        error = job_data.get('error', '')
        error_type = job_data.get('error_type', '')
        result = job_data.get('result', {})
        
        found_jobs.append({
            'job_id': job.id,
            'topic': topic,
            'status': status,
            'created_at': created_at,
            'updated_at': updated_at,
            'error': error,
            'error_type': error_type,
            'has_audio': bool(result.get('audio_url')) if result else False,
            'canonical_filename': result.get('canonical_filename') if result else None
        })

if found_jobs:
    print(f"\n✅ Found {len(found_jobs)} matching job(s):\n")
    for i, job in enumerate(found_jobs, 1):
        print(f"{'='*80}")
        print(f"Job #{i}")
        print(f"{'='*80}")
        print(f"Job ID:      {job['job_id']}")
        print(f"Topic:       {job['topic']}")
        print(f"Status:      {job['status']}")
        print(f"Created:     {job['created_at']}")
        print(f"Updated:     {job['updated_at']}")
        if job['canonical_filename']:
            print(f"Canonical:   {job['canonical_filename']}")
        if job['has_audio']:
            print(f"✅ Has audio file")
        else:
            print(f"❌ No audio file")
        
        if job['error']:
            print(f"\n❌ ERROR:")
            if job['error_type']:
                print(f"   Type: {job['error_type']}")
            print(f"   Message: {job['error']}")
        
        # Check status details
        if job['status'] == 'failed':
            print(f"\n⚠️  Job failed")
        elif job['status'] == 'completed':
            print(f"\n✅ Job completed")
        elif job['status'] in ['pending', 'researching', 'generating', 'generating_content', 'producing']:
            print(f"\n⏳ Job still in progress (status: {job['status']})")
        
        print()
else:
    print(f"\n❌ No jobs found matching those topics in the last 24 hours.")
    print("\nChecking all recent jobs from last 24 hours...")
    
    # Show all recent jobs
    recent_all = db.collection('podcast_jobs').where(
        'created_at', '>=', one_day_ago.isoformat()
    ).order_by('created_at', direction=firestore.Query.DESCENDING).limit(10).stream()
    
    print(f"\n📋 Recent jobs (last 10):")
    for job in recent_all:
        job_data = job.to_dict()
        request = job_data.get('request', {})
        topic = request.get('topic', 'Unknown') if isinstance(request, dict) else 'Unknown'
        status = job_data.get('status', 'Unknown')
        created_at = job_data.get('created_at', 'Unknown')
        print(f"\n  • {topic[:70]}")
        print(f"    Status: {status}")
        print(f"    Created: {created_at}")
        print(f"    Job ID: {job.id}")

