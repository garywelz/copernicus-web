#!/usr/bin/env python3
"""Check recent failed podcast jobs for gwelz@jjay.cuny.edu"""

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

print(f"\n🔍 Checking recent failed podcasts for: {email}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id
print(f"✅ Found subscriber: {email}")
print(f"   Subscriber ID: {subscriber_id}\n")

# Get all jobs for this subscriber
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).limit(100)
jobs = jobs_query.stream()

all_jobs = []
for job in jobs:
    job_data = job.to_dict() or {}
    request_data = job_data.get('request', {})
    topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
    
    all_jobs.append({
        'job_id': job.id,
        'topic': topic,
        'status': job_data.get('status', 'unknown'),
        'error': job_data.get('error', ''),
        'error_type': job_data.get('error_type', ''),
        'created_at': job_data.get('created_at', ''),
        'updated_at': job_data.get('updated_at', ''),
    })

# Filter failed jobs
failed_jobs = [job for job in all_jobs if job['status'] == 'failed']

# Sort by created_at in Python (most recent first)
failed_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

print(f"📊 Total jobs found: {len(all_jobs)}")
print(f"❌ Failed jobs: {len(failed_jobs)}\n")

if failed_jobs:
    print("=" * 80)
    print("RECENT FAILED PODCASTS (Last 10):")
    print("=" * 80)
    
    for i, job in enumerate(failed_jobs[:10], 1):
        print(f"\n{i}. Job ID: {job['job_id']}")
        print(f"   Topic: {job['topic']}")
        print(f"   Created: {job['created_at']}")
        print(f"   Updated: {job['updated_at']}")
        print(f"   Status: {job['status']}")
        if job['error_type']:
            print(f"   Error Type: {job['error_type']}")
        if job['error']:
            error_msg = job['error']
            # Truncate long errors
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
            print(f"   Error: {error_msg}")
        print("-" * 80)
    
    if len(failed_jobs) >= 2:
        print(f"\n📋 LAST 2 FAILED PODCASTS:")
        print("=" * 80)
        for i, job in enumerate(failed_jobs[:2], 1):
            print(f"\n{i}. {job['topic']}")
            print(f"   Job ID: {job['job_id']}")
            print(f"   Created: {job['created_at']}")
            if job['error']:
                print(f"   Error: {job['error'][:800]}")
            print()
else:
    print("✅ No failed jobs found for this account")

# Also check for any jobs in progress or stuck
in_progress = [job for job in all_jobs if job['status'] in ['processing', 'generating_content', 'generating_research']]
if in_progress:
    print(f"\n⚠️  Found {len(in_progress)} job(s) still in progress:")
    for job in in_progress[:5]:
        print(f"   - {job['topic']} (Status: {job['status']}, Created: {job['created_at']})")

