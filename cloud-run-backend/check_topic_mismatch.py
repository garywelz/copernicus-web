#!/usr/bin/env python3
"""Check the latest podcast to see topic mismatch"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

# Get the most recently created podcast
print("\n🔍 Finding most recent podcast...\n")

# Get all jobs, sorted by created_at
all_jobs = db.collection('podcast_jobs').order_by('created_at', direction=firestore.Query.DESCENDING).limit(5).stream()

print("Latest 5 podcasts:\n")
for i, job in enumerate(all_jobs, 1):
    job_data = job.to_dict()
    request = job_data.get('request', {})
    
    topic = request.get('topic', 'Unknown') if isinstance(request, dict) else 'Unknown'
    category = request.get('category', 'Unknown') if isinstance(request, dict) else 'Unknown'
    status = job_data.get('status', 'Unknown')
    created_at = job_data.get('created_at', 'Unknown')
    
    print(f"{i}. Job ID: {job.id}")
    print(f"   Topic Requested: {topic}")
    print(f"   Category: {category}")
    print(f"   Status: {status}")
    print(f"   Created: {created_at}")
    
    # Check research context
    research_context = job_data.get('research_context', {})
    if research_context:
        sources = research_context.get('research_sources', [])
        print(f"   Research Sources: {len(sources)} sources")
        if sources:
            print(f"   First source title: {sources[0].get('title', 'N/A')[:80]}")
    
    # Check if there's a description
    description = job_data.get('description', '')
    if description:
        # Extract first sentence
        first_sent = description.split('.')[0] if description else ''
        print(f"   Description preview: {first_sent[:100]}")
    
    print("-" * 80)

# Get the absolute latest one
latest_query = db.collection('podcast_jobs').order_by('created_at', direction=firestore.Query.DESCENDING).limit(1)
latest_jobs = list(latest_query.stream())

if latest_jobs:
    latest = latest_jobs[0]
    latest_data = latest.to_dict()
    latest_request = latest_data.get('request', {})
    
    print(f"\n📋 DETAILED ANALYSIS OF LATEST PODCAST:")
    print(f"Topic Requested: {latest_request.get('topic', 'N/A')}")
    print(f"Category: {latest_request.get('category', 'N/A')}")
    
    research_context = latest_data.get('research_context', {})
    if research_context:
        print(f"\nResearch Context:")
        print(f"  Quality Score: {research_context.get('research_quality_score', 'N/A')}")
        sources = research_context.get('research_sources', [])
        print(f"  Number of Sources: {len(sources)}")
        
        print(f"\n  Research Sources:")
        for i, source in enumerate(sources[:3], 1):  # Show first 3
            print(f"    {i}. {source.get('title', 'No title')[:80]}")
            print(f"       Abstract: {source.get('abstract', 'No abstract')[:100]}")
    
    # Check the actual content generated
    script = latest_data.get('script', '')
    if script:
        print(f"\nGenerated Script Preview (first 200 chars):")
        print(f"  {script[:200]}...")



