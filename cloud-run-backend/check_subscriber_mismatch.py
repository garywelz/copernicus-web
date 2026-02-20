#!/usr/bin/env python3
"""
Check if gwelz@jjay.cuny.edu or gary.welz@me.com have podcasts in their lists
that are not in the episodes collection (database).
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

db = firestore.Client(database='copernicusai')

print("Checking for podcasts in subscriber lists but not in database...\n")

# Get all episodes (database)
print("1. Loading all episodes from database...")
all_episodes = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    all_episodes.add(episode_doc.id)
print(f"   Found {len(all_episodes)} episodes in database")

# Check gwelz@jjay.cuny.edu
print("\n2. Checking gwelz@jjay.cuny.edu...")
subscribers_ref = db.collection('subscribers')
subscriber_doc = None
for sub_doc in subscribers_ref.stream():
    if sub_doc.to_dict().get('email') == 'gwelz@jjay.cuny.edu':
        subscriber_doc = sub_doc
        break

if subscriber_doc:
    subscriber_id = subscriber_doc.id
    print(f"   Subscriber ID: {subscriber_id}")
    
    # Get from podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    jobs_canonicals = []
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            jobs_canonicals.append(canonical)
    
    print(f"   Podcasts in podcast_jobs: {len(jobs_canonicals)}")
    
    # Get from episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    episodes_canonicals = [doc.id for doc in episodes_query]
    print(f"   Podcasts in episodes: {len(episodes_canonicals)}")
    
    # Find missing
    jobs_set = set(jobs_canonicals)
    episodes_set = set(episodes_canonicals)
    missing_from_db = jobs_set - episodes_set
    
    if missing_from_db:
        print(f"\n   ⚠️  Found {len(missing_from_db)} podcast(s) in jobs but NOT in episodes:")
        for canonical in sorted(missing_from_db):
            print(f"      - {canonical}")
            # Check if it exists in database at all
            if canonical in all_episodes:
                # Check who it belongs to
                ep_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
                if ep_doc.exists:
                    ep_data = ep_doc.to_dict() or {}
                    other_sub_id = ep_data.get('subscriber_id')
                    print(f"        → Exists in DB but assigned to subscriber_id: {other_sub_id}")
            else:
                print(f"        → NOT in database at all (deleted?)")
    else:
        print(f"\n   ✅ All podcasts in jobs are also in episodes")

# Check gary.welz@me.com
print("\n3. Checking gary.welz@me.com...")
subscriber_doc = None
for sub_doc in subscribers_ref.stream():
    if sub_doc.to_dict().get('email') == 'gary.welz@me.com':
        subscriber_doc = sub_doc
        break

if subscriber_doc:
    subscriber_id = subscriber_doc.id
    print(f"   Subscriber ID: {subscriber_id}")
    
    # Get from podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    jobs_canonicals = []
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            jobs_canonicals.append(canonical)
    
    print(f"   Podcasts in podcast_jobs: {len(jobs_canonicals)}")
    
    # Get from episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    episodes_canonicals = [doc.id for doc in episodes_query]
    print(f"   Podcasts in episodes: {len(episodes_canonicals)}")
    
    # Find missing
    jobs_set = set(jobs_canonicals)
    episodes_set = set(episodes_canonicals)
    missing_from_db = jobs_set - episodes_set
    
    if missing_from_db:
        print(f"\n   ⚠️  Found {len(missing_from_db)} podcast(s) in jobs but NOT in episodes:")
        for canonical in sorted(missing_from_db):
            print(f"      - {canonical}")
            # Check if it exists in database at all
            if canonical in all_episodes:
                # Check who it belongs to
                ep_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
                if ep_doc.exists:
                    ep_data = ep_doc.to_dict() or {}
                    other_sub_id = ep_data.get('subscriber_id')
                    print(f"        → Exists in DB but assigned to subscriber_id: {other_sub_id}")
            else:
                print(f"        → NOT in database at all (deleted?)")
    else:
        print(f"\n   ✅ All podcasts in jobs are also in episodes")

print("\nDone!")




