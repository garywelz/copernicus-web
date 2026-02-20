#!/usr/bin/env python3
"""Check if completed podcasts are visible in episodes collection"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import firestore
    from config.constants import EPISODE_COLLECTION_NAME
    from config.database import db
    
    print("✅ Connected to Firestore")
except Exception as e:
    print(f"❌ Error connecting to Firestore: {e}")
    sys.exit(1)

# Check these canonical filenames
canonicals_to_check = [
    "ever-bio-250043",  # Metalloenzymes
    "ever-chem-250022"  # Supramolecular
]

print(f"\n🔍 Checking episodes collection for these podcasts...")
print("=" * 80)

for canonical in canonicals_to_check:
    print(f"\n📋 Checking: {canonical}")
    print("-" * 80)
    
    # Check in podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
    job_found = False
    for job_doc in jobs_query:
        job_data = job_doc.to_dict()
        job_found = True
        print(f"✅ Found in podcast_jobs:")
        print(f"   Job ID: {job_doc.id}")
        print(f"   Status: {job_data.get('status', 'unknown')}")
        print(f"   Subscriber ID: {job_data.get('subscriber_id', 'N/A')}")
        print(f"   Title: {job_data.get('result', {}).get('title', 'N/A')}")
        print(f"   Audio URL: {'✅ Yes' if job_data.get('result', {}).get('audio_url') else '❌ No'}")
        subscriber_id = job_data.get('subscriber_id')
        break
    
    if not job_found:
        print(f"❌ NOT found in podcast_jobs")
        continue
    
    # Check in episodes collection
    episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
    if episode_doc.exists:
        episode_data = episode_doc.to_dict()
        print(f"\n✅ Found in episodes collection:")
        print(f"   Title: {episode_data.get('title', 'N/A')}")
        print(f"   Subscriber ID: {episode_data.get('subscriber_id', 'N/A')}")
        print(f"   Audio URL: {'✅ Yes' if episode_data.get('audio_url') else '❌ No'}")
        print(f"   Submitted to RSS: {episode_data.get('submitted_to_rss', False)}")
    else:
        print(f"\n❌ NOT found in episodes collection")
        print(f"   ⚠️  This podcast exists in podcast_jobs but not in episodes!")
        print(f"   This means it may not be visible in the subscriber dashboard.")
        
        if subscriber_id:
            print(f"\n   Checking subscriber's podcast list...")
            subscriber_jobs = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
            count = 0
            for sj in subscriber_jobs:
                sj_data = sj.to_dict()
                if sj_data.get('result', {}).get('canonical_filename'):
                    count += 1
            print(f"   Subscriber has {count} podcasts in podcast_jobs")
            
            subscriber_episodes = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
            episode_count = sum(1 for _ in subscriber_episodes)
            print(f"   Subscriber has {episode_count} podcasts in episodes collection")

