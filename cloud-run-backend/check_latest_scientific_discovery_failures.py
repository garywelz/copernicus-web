#!/usr/bin/env python3
"""Check the latest failed AI for Scientific Discovery jobs"""

import sys
import os

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
topic_keyword = "AI for Scientific Discovery"

print(f"\n🔍 Searching for recent failed jobs: {topic_keyword}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id

# Search for jobs with this topic, ordered by created_at descending
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).limit(50)
jobs = jobs_query.stream()

found_jobs = []
for job in jobs:
    job_data = job.to_dict() or {}
    request_data = job_data.get('request', {})
    topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
    status = job_data.get('status', 'unknown')
    
    if topic_keyword.lower() in topic.lower() or "Scientific Discovery" in topic:
        found_jobs.append({
            'job_id': job.id,
            'topic': topic,
            'status': status,
            'error': job_data.get('error', ''),
            'error_type': job_data.get('error_type', ''),
            'created_at': job_data.get('created_at', ''),
            'updated_at': job_data.get('updated_at', ''),
        })

# Sort by created_at (most recent first)
found_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

if found_jobs:
    print(f"Found {len(found_jobs)} job(s) matching this topic:\n")
    for i, job in enumerate(found_jobs[:5], 1):  # Show last 5
        print("=" * 80)
        print(f"Job #{i}")
        print("=" * 80)
        print(f"Job ID: {job['job_id']}")
        print(f"Topic: {job['topic']}")
        print(f"Status: {job['status']}")
        print(f"Created: {job['created_at']}")
        print(f"Updated: {job['updated_at']}")
        
        if job['status'] == 'failed':
            print(f"\n❌ FAILED")
            if job['error']:
                print(f"Error Message:")
                error_lines = job['error'].split('\n')
                for line in error_lines[:20]:  # Show first 20 lines
                    print(f"   {line}")
                if len(error_lines) > 20:
                    print(f"   ... ({len(error_lines) - 20} more lines)")
            if job['error_type']:
                print(f"\nError Type: {job['error_type']}")
        print()
else:
    print(f"❌ No jobs found matching '{topic_keyword}'")

