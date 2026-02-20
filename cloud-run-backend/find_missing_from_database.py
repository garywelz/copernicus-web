#!/usr/bin/env python3
"""
Find podcasts that exist in podcast_jobs for a subscriber but are NOT in the episodes collection.
These are podcasts that might have been deleted from the database but still exist in the subscriber's job list.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

db = firestore.Client(database='copernicusai')

print("="*80)
print("FINDING PODCASTS IN SUBSCRIBER LISTS BUT NOT IN DATABASE")
print("="*80)

# Get subscriber emails to check
subscribers_to_check = [
    'gwelz@jjay.cuny.edu',
    'gary.welz@me.com'
]

# First, get all canonical filenames from episodes collection (the database)
print("\n1. Getting all podcasts from episodes collection (database)...")
episodes_canonicals = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    episodes_canonicals.add(episode_doc.id)

print(f"   Total podcasts in database: {len(episodes_canonicals)}")

# Get all subscribers
print("\n2. Getting all subscribers...")
subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

subscriber_map = {}  # email -> subscriber_id
subscriber_reverse_map = {}  # subscriber_id -> email
for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    email = subscriber_data.get('email', '')
    subscriber_id = subscriber_doc.id
    subscriber_map[email] = subscriber_id
    subscriber_reverse_map[subscriber_id] = email

print(f"   Found {len(subscriber_map)} subscribers")

# Check each subscriber
print("\n3. Checking each subscriber for podcasts not in database...")

for email in subscribers_to_check:
    print("\n" + "="*80)
    print(f"CHECKING: {email}")
    print("="*80)
    
    subscriber_id = subscriber_map.get(email)
    if not subscriber_id:
        print(f"   ❌ Subscriber not found: {email}")
        continue
    
    print(f"   Subscriber ID: {subscriber_id}")
    
    # Get podcasts from podcast_jobs for this subscriber
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    
    jobs_canonicals = set()
    jobs_data = {}
    
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        
        if canonical:
            jobs_canonicals.add(canonical)
            jobs_data[canonical] = {
                'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
                'status': job_data.get('status', 'unknown'),
                'created_at': job_data.get('created_at'),
                'has_audio': bool(result.get('audio_url'))
            }
    
    print(f"\n   Podcasts in podcast_jobs: {len(jobs_canonicals)}")
    
    # Get podcasts from episodes for this subscriber
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    
    episodes_canonicals_for_sub = set()
    episodes_data = {}
    
    for episode_doc in episodes_query:
        canonical = episode_doc.id
        episodes_canonicals_for_sub.add(canonical)
        episode_data = episode_doc.to_dict() or {}
        episodes_data[canonical] = {
            'title': episode_data.get('title', episode_data.get('topic', 'Untitled')),
            'has_audio': bool(episode_data.get('audio_url'))
        }
    
    print(f"   Podcasts in episodes: {len(episodes_canonicals_for_sub)}")
    
    # Find podcasts in jobs but NOT in episodes
    missing_from_episodes = jobs_canonicals - episodes_canonicals_for_sub
    
    if missing_from_episodes:
        print(f"\n   ⚠️  Found {len(missing_from_episodes)} podcast(s) in podcast_jobs but NOT in episodes collection:")
        for canonical in sorted(missing_from_episodes):
            job_info = jobs_data.get(canonical, {})
            print(f"\n      {canonical}:")
            print(f"        Title: {job_info.get('title', 'N/A')}")
            print(f"        Status: {job_info.get('status', 'N/A')}")
            print(f"        Has audio: {job_info.get('has_audio', False)}")
            print(f"        Created: {job_info.get('created_at', 'N/A')}")
            
            # Check if it exists in database at all (might be deleted)
            if canonical not in episodes_canonicals:
                print(f"        ❌ NOT in database at all (was deleted?)")
            else:
                print(f"        ⚠️  In database but assigned to different subscriber!")
                
                # Find which subscriber has it
                episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
                if episode_doc.exists:
                    episode_data = episode_doc.to_dict() or {}
                    other_sub_id = episode_data.get('subscriber_id')
                    other_email = subscriber_reverse_map.get(other_sub_id, 'unknown')
                    print(f"        Assigned to: {other_email} ({other_sub_id})")
    else:
        print(f"\n   ✅ All podcasts in podcast_jobs are also in episodes collection")
    
    # Find podcasts in episodes but NOT in jobs
    missing_from_jobs = episodes_canonicals_for_sub - jobs_canonicals
    
    if missing_from_jobs:
        print(f"\n   ⚠️  Found {len(missing_from_jobs)} podcast(s) in episodes but NOT in podcast_jobs:")
        for canonical in sorted(missing_from_jobs)[:5]:  # Show first 5
            episode_info = episodes_data.get(canonical, {})
            print(f"      - {canonical}: {episode_info.get('title', 'N/A')}")
        if len(missing_from_jobs) > 5:
            print(f"      ... and {len(missing_from_jobs) - 5} more")
    
    # Union count (what "View Podcasts" shows)
    union_set = jobs_canonicals | episodes_canonicals_for_sub
    print(f"\n   Union count (episodes ∪ jobs): {len(union_set)}")
    print(f"   This is what 'View Podcasts' modal shows")

# Also check for any podcasts that exist in episodes but have different subscriber_id than expected
print("\n" + "="*80)
print("CHECKING FOR PODCASTS ASSIGNED TO WRONG SUBSCRIBER")
print("="*80)

for email in subscribers_to_check:
    subscriber_id = subscriber_map.get(email)
    if not subscriber_id:
        continue
    
    # Get all episodes that should belong to this subscriber based on jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        
        if canonical and canonical in episodes_canonicals:
            # Check if episode has the same subscriber_id
            episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
            if episode_doc.exists:
                episode_data = episode_doc.to_dict() or {}
                episode_sub_id = episode_data.get('subscriber_id')
                
                if episode_sub_id != subscriber_id:
                    print(f"\n⚠️  Mismatch for {canonical}:")
                    print(f"   Job says: {subscriber_id} ({email})")
                    print(f"   Episode says: {episode_sub_id} ({subscriber_reverse_map.get(episode_sub_id, 'unknown')})")




