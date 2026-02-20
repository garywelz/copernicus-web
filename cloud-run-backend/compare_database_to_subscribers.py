#!/usr/bin/env python3
"""
Compare podcast database (episodes collection) to subscriber lists by filename.
This will show the ground truth counts.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from collections import defaultdict

print("Starting script...")
db = firestore.Client(database='copernicusai')
print("Firestore client created...")

print("="*80)
print("COMPARING PODCAST DATABASE TO SUBSCRIBER LISTS")
print("="*80)

# 1. Get ALL podcasts from episodes collection (the database)
print("\n1. Getting all podcasts from episodes collection (database)...")
all_podcasts_in_db = {}
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    episode_data = episode_doc.to_dict() or {}
    canonical = episode_doc.id
    subscriber_id = episode_data.get('subscriber_id', 'unknown')
    subscriber_email = episode_data.get('subscriber_email', 'unknown')
    title = episode_data.get('title', episode_data.get('topic', 'Untitled'))
    
    all_podcasts_in_db[canonical] = {
        'subscriber_id': subscriber_id,
        'subscriber_email': subscriber_email,
        'title': title
    }

print(f"   Total podcasts in database: {len(all_podcasts_in_db)}")

# 2. Get all subscribers
print("\n2. Getting all subscribers...")
subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

subscriber_info = {}
for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    subscriber_id = subscriber_doc.id
    email = subscriber_data.get('email', 'N/A')
    
    subscriber_info[subscriber_id] = {
        'email': email,
        'podcasts_from_db': set(),  # Filenames from episodes collection
        'podcasts_from_jobs': set()  # Filenames from podcast_jobs collection
    }

# 3. Group database podcasts by subscriber
print("\n3. Grouping database podcasts by subscriber...")
for canonical, podcast_data in all_podcasts_in_db.items():
    subscriber_id = podcast_data['subscriber_id']
    if subscriber_id and subscriber_id != 'unknown':
        if subscriber_id in subscriber_info:
            subscriber_info[subscriber_id]['podcasts_from_db'].add(canonical)
        else:
            print(f"   ⚠️  Podcast {canonical} has subscriber_id {subscriber_id} but subscriber not found in subscribers collection")

# 4. Get podcasts from podcast_jobs collection
print("\n4. Getting podcasts from podcast_jobs collection...")
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    subscriber_id = job_data.get('subscriber_id')
    
    if canonical and subscriber_id:
        if subscriber_id in subscriber_info:
            subscriber_info[subscriber_id]['podcasts_from_jobs'].add(canonical)
        else:
            print(f"   ⚠️  Job has subscriber_id {subscriber_id} but subscriber not found")

# 5. Compare and report
print("\n" + "="*80)
print("COMPARISON RESULTS BY SUBSCRIBER:")
print("="*80)

total_db_count = 0
for subscriber_id, info in sorted(subscriber_info.items(), key=lambda x: len(x[1]['podcasts_from_db']), reverse=True):
    email = info['email']
    db_set = info['podcasts_from_db']
    jobs_set = info['podcasts_from_jobs']
    union_set = db_set | jobs_set  # All podcasts from either source
    
    db_count = len(db_set)
    jobs_count = len(jobs_set)
    union_count = len(union_set)
    
    total_db_count += db_count
    
    if db_count > 0 or union_count > 0:  # Only show subscribers with podcasts
        print(f"\n{email}:")
        print(f"  Database count (episodes only): {db_count}")
        print(f"  Jobs count (podcast_jobs only): {jobs_count}")
        print(f"  Union count (episodes ∪ jobs): {union_count}")
        
        if db_count != union_count:
            print(f"  ⚠️  MISMATCH!")
            missing_in_db = union_set - db_set
            extra_in_db = db_set - union_set
            
            if missing_in_db:
                print(f"     Missing in database ({len(missing_in_db)}):")
                for canonical in sorted(missing_in_db)[:5]:
                    print(f"       - {canonical}")
            if extra_in_db:
                print(f"     Extra in database ({len(extra_in_db)}):")
                for canonical in sorted(extra_in_db)[:5]:
                    title = all_podcasts_in_db.get(canonical, {}).get('title', 'N/A')
                    print(f"       - {canonical}: {title}")

print("\n" + "="*80)
print("TOTALS:")
print("="*80)
print(f"Total podcasts in database: {len(all_podcasts_in_db)}")
print(f"Sum of database counts by subscriber: {total_db_count}")
print(f"Difference: {len(all_podcasts_in_db) - total_db_count}")

# Specific check for gary.welz@me.com
print("\n" + "="*80)
print("SPECIFIC CHECK: gary.welz@me.com")
print("="*80)

gary_subscriber_id = None
for sub_id, info in subscriber_info.items():
    if info['email'] == 'gary.welz@me.com':
        gary_subscriber_id = sub_id
        break

if gary_subscriber_id:
    info = subscriber_info[gary_subscriber_id]
    db_set = info['podcasts_from_db']
    jobs_set = info['podcasts_from_jobs']
    union_set = db_set | jobs_set
    
    print(f"\nSubscriber ID: {gary_subscriber_id}")
    print(f"Database count: {len(db_set)}")
    print(f"Jobs count: {len(jobs_set)}")
    print(f"Union count: {len(union_set)}")
    
    print(f"\nPodcasts in database ({len(db_set)}):")
    for canonical in sorted(db_set):
        title = all_podcasts_in_db.get(canonical, {}).get('title', 'N/A')
        print(f"  ✓ {canonical}: {title}")
    
    print(f"\nPodcasts in jobs ({len(jobs_set)}):")
    for canonical in sorted(jobs_set):
        in_db = "✓" if canonical in db_set else "✗"
        title = all_podcasts_in_db.get(canonical, {}).get('title', 'N/A')
        print(f"  {in_db} {canonical}: {title}")
    
    print(f"\nUnion (all podcasts) ({len(union_set)}):")
    for canonical in sorted(union_set):
        in_db = "✓" if canonical in db_set else "✗"
        title = all_podcasts_in_db.get(canonical, {}).get('title', 'N/A')
        print(f"  {in_db} {canonical}: {title}")
    
    missing_in_db = union_set - db_set
    if missing_in_db:
        print(f"\n⚠️  Missing in database ({len(missing_in_db)}):")
        for canonical in sorted(missing_in_db):
            print(f"  - {canonical}")
else:
    print("Subscriber not found!")

