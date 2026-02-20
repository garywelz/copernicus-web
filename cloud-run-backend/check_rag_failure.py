#!/usr/bin/env python3
"""Check the failed RAG podcast job"""

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
topic_keyword = "Retrieval-Augmented Generation"

print(f"\n🔍 Searching for failed job: {topic_keyword}\n")

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id

# Search for jobs with this topic
jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).limit(50)
jobs = jobs_query.stream()

found_jobs = []
for job in jobs:
    job_data = job.to_dict() or {}
    request_data = job_data.get('request', {})
    topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
    status = job_data.get('status', 'unknown')
    
    if "RAG" in topic or "Retrieval-Augmented" in topic or "Knowledge Grounding" in topic:
        found_jobs.append({
            'job_id': job.id,
            'topic': topic,
            'status': status,
            'error': job_data.get('error', ''),
            'error_type': job_data.get('error_type', ''),
            'created_at': job_data.get('created_at', ''),
            'updated_at': job_data.get('updated_at', ''),
            'request': request_data,
        })

# Sort by created_at (most recent first)
found_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

if found_jobs:
    print(f"Found {len(found_jobs)} job(s) matching this topic:\n")
    for i, job in enumerate(found_jobs[:3], 1):  # Show last 3
        print("=" * 80)
        print(f"Job #{i}")
        print("=" * 80)
        print(f"Job ID: {job['job_id']}")
        print(f"Topic: {job['topic']}")
        print(f"Status: {job['status']}")
        print(f"Created: {job['created_at']}")
        print(f"Updated: {job['updated_at']}")
        
        request = job.get('request', {})
        print(f"\nRequest Details:")
        print(f"   Category: {request.get('category', 'N/A')}")
        print(f"   Expertise Level: {request.get('expertise_level', 'N/A')}")
        print(f"   Duration: {request.get('duration', 'N/A')}")
        print(f"   Format: {request.get('format_type', 'N/A')}")
        
        if job['status'] == 'failed':
            print(f"\n❌ FAILED")
            if job['error']:
                print(f"Error Message:")
                error_msg = job['error']
                # Show full error
                if len(error_msg) > 1000:
                    print(f"   {error_msg[:500]}...")
                    print(f"\n   ... ({len(error_msg) - 500} more characters)")
                    print(f"\n   Full error (last 500 chars):")
                    print(f"   ...{error_msg[-500:]}")
                else:
                    print(f"   {error_msg}")
            if job['error_type']:
                print(f"\nError Type: {job['error_type']}")
        elif job['status'] == 'completed':
            result = job.get('result', {})
            print(f"\n✅ Completed")
            print(f"   Title: {result.get('title', 'N/A')}")
        else:
            print(f"\n⏳ Status: {job['status']}")
        print()
else:
    print(f"❌ No jobs found matching '{topic_keyword}'")

