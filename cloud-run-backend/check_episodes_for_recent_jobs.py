#!/usr/bin/env python3
"""Check if recent jobs made it to episodes collection"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    from config.constants import EPISODE_COLLECTION_NAME
    db = firestore.Client(project="regal-scholar-453620-r7", database="copernicusai")
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

# These are the canonical filenames from the jobs we checked
canonicals_to_check = [
    "ever-compsci-250037",  # Efficient AI
    "ever-compsci-250036",  # Multimodal AI
    "ever-compsci-250035",  # AI Agents (estimated)
]

print(f"\n🔍 Checking if these podcasts exist in episodes collection...\n")

for canonical in canonicals_to_check:
    print("=" * 80)
    print(f"Checking: {canonical}")
    print("-" * 80)
    
    # Check in episodes
    ep_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
    
    if ep_doc.exists:
        ep_data = ep_doc.to_dict()
        print(f"✅ Found in episodes collection")
        print(f"   Title: {ep_data.get('title', 'N/A')}")
        print(f"   Status: {ep_data.get('status', 'N/A')}")
        print(f"   Has audio_url: {bool(ep_data.get('audio_url'))}")
        print(f"   Subscriber ID: {ep_data.get('subscriber_id', 'N/A')}")
    else:
        print(f"❌ NOT found in episodes collection")
        
        # Check if it exists in podcast_jobs
        jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
        found_in_jobs = False
        for job_doc in jobs_query:
            found_in_jobs = True
            job_data = job_doc.to_dict()
            print(f"   ✅ Found in podcast_jobs:")
            print(f"      Job ID: {job_doc.id}")
            print(f"      Status: {job_data.get('status', 'N/A')}")
            result = job_data.get('result', {})
            print(f"      Title: {result.get('title', 'N/A')}")
            print(f"      Has audio_url: {bool(result.get('audio_url'))}")
            promoted = job_data.get('promoted_to_episodes', False)
            print(f"      promoted_to_episodes: {promoted}")
            if not promoted:
                print(f"      ⚠️  This job was never promoted to episodes!")
        if not found_in_jobs:
            print(f"   ❌ Also NOT found in podcast_jobs")
    print()

