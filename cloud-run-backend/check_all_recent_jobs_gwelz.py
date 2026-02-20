#!/usr/bin/env python3
"""Check all recent podcast jobs for gwelz@jjay.cuny.edu"""

import sys
import os
from datetime import datetime

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

print(f"\n🔍 Checking ALL recent podcast jobs for: {email}\n")

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
        'result': job_data.get('result', {})
    })

# Sort by created_at in Python (most recent first)
all_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

print(f"📊 Total jobs found: {len(all_jobs)}\n")
print("=" * 80)
print("MOST RECENT JOBS (Last 10):")
print("=" * 80)

for i, job in enumerate(all_jobs[:10], 1):
    print(f"\n{i}. Topic: {job['topic']}")
    print(f"   Job ID: {job['job_id']}")
    print(f"   Status: {job['status']}")
    print(f"   Created: {job['created_at']}")
    print(f"   Updated: {job['updated_at']}")
    
    # Check if result has required fields
    result = job.get('result', {})
    has_audio = bool(result.get('audio_url'))
    has_title = bool(result.get('title'))
    has_description = bool(result.get('description'))
    
    if job['status'] == 'completed':
        print(f"   ✅ Completed")
        if not has_audio:
            print(f"   ⚠️  WARNING: No audio_url in result")
        if not has_title:
            print(f"   ⚠️  WARNING: No title in result")
        if not has_description:
            print(f"   ⚠️  WARNING: No description in result")
    elif job['status'] == 'failed':
        print(f"   ❌ FAILED")
        if job['error']:
            error_msg = job['error'][:300]
            print(f"   Error: {error_msg}")
        if job['error_type']:
            print(f"   Error Type: {job['error_type']}")
    elif job['status'] in ['processing', 'generating_content', 'generating_research']:
        print(f"   ⏳ IN PROGRESS")
    else:
        print(f"   ⚠️  Status: {job['status']}")
    
    print("-" * 80)

# Count by status
status_counts = {}
for job in all_jobs:
    status = job['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print(f"\n📊 STATUS SUMMARY:")
for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"   {status}: {count}")

# Check for jobs with errors but not marked as failed
jobs_with_errors = [job for job in all_jobs if job['error'] and job['status'] != 'failed']
if jobs_with_errors:
    print(f"\n⚠️  Found {len(jobs_with_errors)} job(s) with errors but not marked as failed:")
    for job in jobs_with_errors[:5]:
        print(f"   - {job['topic']} (Status: {job['status']}, Error: {job['error'][:100]})")

