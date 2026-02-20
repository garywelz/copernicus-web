#!/usr/bin/env python3
"""Check all podcast jobs from past 4 hours for gwelz@jjay.cuny.edu"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    from utils.subscriber_helpers import get_subscriber_by_email
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

email = "gwelz@jjay.cuny.edu"

print(f"\n🔍 Checking ALL podcast jobs from past 4 hours for: {email}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id
print(f"✅ Found subscriber: {email}")
print(f"   Subscriber ID: {subscriber_id}\n")

# Calculate 4 hours ago
four_hours_ago = (datetime.utcnow() - timedelta(hours=4)).isoformat()

# Get all jobs for this subscriber from past 4 hours
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).limit(100)
jobs = jobs_query.stream()

all_jobs = []
for job in jobs:
    job_data = job.to_dict() or {}
    created_at = job_data.get('created_at', '')
    
    # Filter to last 4 hours
    if created_at >= four_hours_ago:
        request_data = job_data.get('request', {})
        topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
        
        all_jobs.append({
            'job_id': job.id,
            'topic': topic,
            'status': job_data.get('status', 'unknown'),
            'error': job_data.get('error', ''),
            'error_type': job_data.get('error_type', ''),
            'created_at': created_at,
            'updated_at': job_data.get('updated_at', ''),
            'result': job_data.get('result', {})
        })

# Sort by created_at (most recent first)
all_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

print(f"📊 Found {len(all_jobs)} jobs in the past 4 hours\n")
print("=" * 80)
print("ALL JOBS FROM PAST 4 HOURS:")
print("=" * 80)

failed_jobs = []
completed_jobs = []
other_jobs = []

for i, job in enumerate(all_jobs, 1):
    status = job['status']
    if status == 'failed':
        failed_jobs.append(job)
    elif status == 'completed':
        completed_jobs.append(job)
    else:
        other_jobs.append(job)
    
    print(f"\n{i}. Topic: {job['topic']}")
    print(f"   Job ID: {job['job_id']}")
    print(f"   Status: {status}")
    print(f"   Created: {job['created_at']}")
    
    if status == 'failed':
        print(f"   ❌ FAILED")
        if job['error']:
            error_msg = job['error']
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            print(f"   Error: {error_msg}")
        if job['error_type']:
            print(f"   Error Type: {job['error_type']}")
    elif status == 'completed':
        result = job.get('result', {})
        has_audio = bool(result.get('audio_url'))
        print(f"   ✅ Completed")
        print(f"   Has audio: {has_audio}")
        if not has_audio:
            print(f"   ⚠️  WARNING: No audio_url")
    else:
        print(f"   ⏳ Status: {status}")
    print("-" * 80)

print(f"\n📊 SUMMARY:")
print(f"   ✅ Completed: {len(completed_jobs)}")
print(f"   ❌ Failed: {len(failed_jobs)}")
print(f"   ⏳ Other: {len(other_jobs)}")

if failed_jobs:
    print(f"\n❌ FAILED JOBS DETAILS:")
    for i, job in enumerate(failed_jobs, 1):
        print(f"\n   {i}. {job['topic']}")
        print(f"      Job ID: {job['job_id']}")
        print(f"      Created: {job['created_at']}")
        if job['error']:
            print(f"      Error: {job['error']}")

