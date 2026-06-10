#!/usr/bin/env python3
"""Check failed podcast jobs for Topology/TDA topics"""

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

# Search keywords
keywords = ["Topological Data Analysis", "Topology", "TDA"]

print(f"\n🔍 Checking failed podcast jobs for: {', '.join(keywords)}\n")

# Get recent jobs (simplified query to avoid index requirement)
jobs_query = db.collection('podcast_jobs').where('status', '==', 'failed').limit(50)
jobs = jobs_query.stream()

found_jobs = []
for job in jobs:
    job_data = job.to_dict() or {}
    request_data = job_data.get('request', {})
    topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
    
    # Check if topic matches our keywords
    topic_lower = topic.lower()
    if any(kw.lower() in topic_lower for kw in keywords):
        found_jobs.append({
            'job_id': job.id,
            'topic': topic,
            'status': job_data.get('status', 'unknown'),
            'error': job_data.get('error', ''),
            'error_type': job_data.get('error_type', ''),
            'created_at': job_data.get('created_at', ''),
            'updated_at': job_data.get('updated_at', ''),
            'research_sources_count': job_data.get('research_sources_count', 0),
            'research_quality_score': job_data.get('research_quality_score', 0),
        })

# Sort by created_at (most recent first)
found_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

if found_jobs:
    print(f"Found {len(found_jobs)} failed job(s):\n")
    for i, job in enumerate(found_jobs, 1):
        print("=" * 80)
        print(f"Job #{i}")
        print("=" * 80)
        print(f"Job ID:              {job['job_id']}")
        print(f"Topic:               {job['topic']}")
        print(f"Status:               {job['status']}")
        print(f"Created:              {job['created_at']}")
        print(f"Updated:              {job['updated_at']}")
        print(f"Research Sources:     {job.get('research_sources_count', 'N/A')}")
        print(f"Research Quality:     {job.get('research_quality_score', 'N/A')}")
        print(f"\n❌ ERROR:")
        print(f"   Type: {job['error_type']}")
        print(f"   Message:")
        error_msg = str(job['error'])
        for line in error_msg.split('\n'):
            print(f"      {line}")
        print()
else:
    print(f"❌ No failed jobs found matching keywords in the last 30 days.")
    print("\nChecking all recent failed jobs...")
    
    all_failed = db.collection('podcast_jobs').where('status', '==', 'failed').where('created_at', '>=', thirty_days_ago).order_by('created_at', direction=firestore.Query.DESCENDING).limit(10).stream()
    
    print(f"\n📋 Recent failed jobs (last 10):")
    for job in all_failed:
        job_data = job.to_dict() or {}
        request_data = job_data.get('request', {})
        topic = request_data.get('topic', 'Unknown') if isinstance(request_data, dict) else 'Unknown'
        error = job_data.get('error', 'No error message')
        error_type = job_data.get('error_type', '')
        print(f"\n  • {topic[:60]}")
        print(f"    Job ID: {job.id}")
        print(f"    Error Type: {error_type}")
        print(f"    Error: {error[:150]}...")
