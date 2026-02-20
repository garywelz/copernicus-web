#!/usr/bin/env python3
"""Check detailed job information for recent jobs"""

import sys
import os
import json

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
job_ids = [
    "6f2505a2-0af4-40c5-b1b4-6706452eb4e9",  # Efficient AI
    "e22cec20-f6cf-4189-867d-273e0ae11440",  # Multimodal AI
]

print(f"\n🔍 Checking job details for: {email}\n")

for job_id in job_ids:
    print("=" * 80)
    job_doc = db.collection('podcast_jobs').document(job_id).get()
    
    if not job_doc.exists:
        print(f"❌ Job {job_id} not found")
        continue
    
    job_data = job_doc.to_dict()
    request = job_data.get('request', {})
    topic = request.get('topic', 'Unknown') if isinstance(request, dict) else 'Unknown'
    status = job_data.get('status', 'unknown')
    result = job_data.get('result', {})
    error = job_data.get('error', '')
    
    print(f"Job ID: {job_id}")
    print(f"Topic: {topic}")
    print(f"Status: {status}")
    print(f"Created: {job_data.get('created_at', 'N/A')}")
    print(f"Updated: {job_data.get('updated_at', 'N/A')}")
    
    if error:
        print(f"\n❌ ERROR:")
        print(f"   {error}")
    
    if result:
        print(f"\n📊 RESULT CONTENTS:")
        print(f"   Has audio_url: {bool(result.get('audio_url'))}")
        print(f"   Has title: {bool(result.get('title'))}")
        print(f"   Has description: {bool(result.get('description'))}")
        print(f"   Has script: {bool(result.get('script'))}")
        print(f"   Has canonical_filename: {bool(result.get('canonical_filename'))}")
        
        if result.get('audio_url'):
            print(f"   audio_url: {result.get('audio_url')[:100]}...")
        else:
            print(f"   ⚠️  MISSING audio_url")
        
        if result.get('title'):
            print(f"   title: {result.get('title')}")
        else:
            print(f"   ⚠️  MISSING title")
        
        # Check if description exists and is valid
        description = result.get('description', '')
        if description:
            print(f"   description length: {len(description)} chars")
            print(f"   description preview: {description[:200]}...")
        else:
            print(f"   ⚠️  MISSING description")
        
        # Check for any error messages in result
        if 'error' in result:
            print(f"   ⚠️  ERROR in result: {result.get('error')}")
    else:
        print(f"\n⚠️  NO RESULT DATA")
    
    print()

