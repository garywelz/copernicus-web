#!/usr/bin/env python3
"""
Find the discrepancy between subscriber podcast counts (65) and total count (64)
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from collections import defaultdict

db = firestore.Client(database='copernicusai')

print("="*70)
print("INVESTIGATING COUNT DISCREPANCY: 65 (subscriber sum) vs 64 (total)")
print("="*70)

# Get all subscribers
print("\n1. Getting all subscribers...")
subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

subscriber_info = {}
for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    subscriber_id = subscriber_doc.id
    email = subscriber_data.get('email', 'N/A')
    
    # Count unique podcasts using union (same logic as endpoint)
    unique_podcasts = set()
    
    # Count from podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            unique_podcasts.add(canonical)
        else:
            unique_podcasts.add(job_doc.id)
    
    # Count from episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    for episode_doc in episodes_query:
        unique_podcasts.add(episode_doc.id)
    
    subscriber_info[subscriber_id] = {
        'email': email,
        'count': len(unique_podcasts),
        'podcasts': unique_podcasts
    }

print(f"\n2. Subscriber counts:")
total_subscriber_count = 0
for sub_id, info in subscriber_info.items():
    print(f"   {info['email']}: {info['count']} podcasts")
    total_subscriber_count += info['count']

print(f"\n   Subscriber sum: {total_subscriber_count}")

# Get global total (union of all podcasts)
print("\n3. Getting global total (unique podcasts across all collections)...")
all_unique_podcasts = set()

# Get all from podcast_jobs
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        all_unique_podcasts.add(canonical)

# Get all from episodes
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    all_unique_podcasts.add(episode_doc.id)

global_total = len(all_unique_podcasts)
print(f"   Global total (union): {global_total}")

# Find podcasts assigned to multiple subscribers
print("\n4. Checking for podcasts assigned to multiple subscribers...")
podcast_to_subscribers = defaultdict(list)

for sub_id, info in subscriber_info.items():
    for podcast_id in info['podcasts']:
        podcast_to_subscribers[podcast_id].append({
            'subscriber_id': sub_id,
            'email': info['email']
        })

multi_assigned = {pod: subs for pod, subs in podcast_to_subscribers.items() if len(subs) > 1}

if multi_assigned:
    print(f"\n   ⚠️  Found {len(multi_assigned)} podcast(s) assigned to multiple subscribers:")
    for podcast_id, subs in multi_assigned.items():
        print(f"\n   Podcast: {podcast_id}")
        for sub in subs:
            print(f"      - {sub['email']} ({sub['subscriber_id']})")
else:
    print("   ✅ No podcasts assigned to multiple subscribers")

# Find podcasts in subscriber counts but not in global
print("\n5. Checking for podcasts in subscriber counts but not in global...")
all_subscriber_podcasts = set()
for info in subscriber_info.values():
    all_subscriber_podcasts.update(info['podcasts'])

in_subscribers_not_global = all_subscriber_podcasts - all_unique_podcasts
in_global_not_subscribers = all_unique_podcasts - all_subscriber_podcasts

if in_subscribers_not_global:
    print(f"\n   ⚠️  Found {len(in_subscribers_not_global)} podcast(s) in subscriber counts but not in global:")
    for podcast_id in in_subscribers_not_global:
        print(f"      - {podcast_id}")
        # Find which subscriber has it
        for sub_id, info in subscriber_info.items():
            if podcast_id in info['podcasts']:
                print(f"        Assigned to: {info['email']}")

if in_global_not_subscribers:
    print(f"\n   ⚠️  Found {len(in_global_not_subscribers)} podcast(s) in global but not in subscriber counts:")
    for podcast_id in in_global_not_subscribers[:10]:  # Show first 10
        print(f"      - {podcast_id}")
        # Check which collections it's in
        episode_doc = db.collection(EPISODE_COLLECTION_NAME).document(podcast_id).get()
        if episode_doc.exists:
            episode_data = episode_doc.to_dict() or {}
            sub_id = episode_data.get('subscriber_id')
            print(f"        In episodes collection, subscriber_id: {sub_id or 'None/Unknown'}")

print("\n" + "="*70)
print("SUMMARY:")
print("="*70)
print(f"Subscriber sum: {total_subscriber_count}")
print(f"Global total: {global_total}")
print(f"Difference: {total_subscriber_count - global_total}")
print(f"\nMulti-assigned podcasts: {len(multi_assigned)}")
print(f"Podcasts in subscribers but not global: {len(in_subscribers_not_global)}")
print(f"Podcasts in global but not subscribers: {len(in_global_not_subscribers)}")

# Calculate expected total if we account for duplicates
if multi_assigned:
    duplicate_count = sum(len(subs) - 1 for subs in multi_assigned.values())
    expected_total = total_subscriber_count - duplicate_count
    print(f"\nExpected total (subscriber sum - duplicates): {expected_total}")
    print(f"  (Each duplicate counts as +1 in subscriber sum)")




