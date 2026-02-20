#!/usr/bin/env python3
"""
Check for count discrepancy: 65 (subscriber sum) vs 64 (total)
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
print("FINDING COUNT DISCREPANCY")
print("="*70)

# Check for podcasts with different subscriber_ids in podcast_jobs vs episodes
print("\n1. Checking for podcasts with mismatched subscriber_ids...")
mismatches = []

all_episodes = {}
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    episode_data = episode_doc.to_dict() or {}
    canonical = episode_doc.id
    ep_subscriber_id = episode_data.get('subscriber_id')
    all_episodes[canonical] = ep_subscriber_id

all_jobs = {}
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        job_subscriber_id = job_data.get('subscriber_id')
        if canonical in all_jobs:
            # Multiple jobs with same canonical - this could be the issue
            mismatches.append({
                'canonical': canonical,
                'type': 'multiple_jobs',
                'job_ids': all_jobs[canonical].get('job_ids', []) + [job_doc.id],
                'subscriber_ids': list(set(all_jobs[canonical].get('subscriber_ids', []) + [job_subscriber_id]))
            })
        else:
            all_jobs[canonical] = {
                'subscriber_id': job_subscriber_id,
                'job_ids': [job_doc.id],
                'subscriber_ids': [job_subscriber_id] if job_subscriber_id else []
            }
        
        # Check if subscriber_id differs between jobs and episodes
        if canonical in all_episodes:
            ep_sub_id = all_episodes[canonical]
            if ep_sub_id and job_subscriber_id and ep_sub_id != job_subscriber_id:
                mismatches.append({
                    'canonical': canonical,
                    'type': 'subscriber_mismatch',
                    'episode_subscriber': ep_sub_id,
                    'job_subscriber': job_subscriber_id
                })

if mismatches:
    print(f"\n   ⚠️  Found {len(mismatches)} issue(s):")
    for mismatch in mismatches:
        print(f"\n   Podcast: {mismatch['canonical']}")
        if mismatch['type'] == 'multiple_jobs':
            print(f"      Type: Multiple jobs with same canonical")
            print(f"      Job IDs: {mismatch['job_ids']}")
            print(f"      Subscriber IDs: {mismatch['subscriber_ids']}")
        elif mismatch['type'] == 'subscriber_mismatch':
            print(f"      Type: Different subscriber_ids")
            print(f"      Episode subscriber: {mismatch['episode_subscriber']}")
            print(f"      Job subscriber: {mismatch['job_subscriber']}")
else:
    print("   ✅ No subscriber_id mismatches found")

# Check for podcasts assigned to multiple subscribers in episodes
print("\n2. Checking for podcasts with multiple subscriber assignments in episodes...")
episode_subscribers = defaultdict(list)
for canonical, sub_id in all_episodes.items():
    if sub_id:
        episode_subscribers[canonical].append(sub_id)

multi_sub_episodes = {k: v for k, v in episode_subscribers.items() if len(set(v)) > 1}
if multi_sub_episodes:
    print(f"\n   ⚠️  Found {len(multi_sub_episodes)} podcast(s) with multiple subscriber assignments")
    for canonical, sub_ids in multi_sub_episodes.items():
        print(f"      {canonical}: {sub_ids}")
else:
    print("   ✅ No podcasts with multiple subscriber assignments in episodes")

# Get subscriber counts
print("\n3. Getting subscriber counts...")
subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

subscriber_counts = {}
for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    subscriber_id = subscriber_doc.id
    email = subscriber_data.get('email', 'N/A')
    
    unique_podcasts = set()
    
    # From podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            unique_podcasts.add(canonical)
    
    # From episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    for episode_doc in episodes_query:
        unique_podcasts.add(episode_doc.id)
    
    subscriber_counts[email] = {
        'count': len(unique_podcasts),
        'subscriber_id': subscriber_id,
        'podcasts': unique_podcasts
    }

print("\n   Subscriber counts:")
total_subscriber_sum = 0
for email, info in subscriber_counts.items():
    print(f"      {email}: {info['count']}")
    total_subscriber_sum += info['count']

print(f"\n   Subscriber sum: {total_subscriber_sum}")

# Get global total
all_unique = set()
all_unique.update(all_episodes.keys())
all_unique.update(all_jobs.keys())
global_total = len(all_unique)
print(f"\n4. Global total (union of all podcasts): {global_total}")

print(f"\n" + "="*70)
print(f"SUMMARY:")
print(f"   Subscriber sum: {total_subscriber_sum}")
print(f"   Global total: {global_total}")
print(f"   Difference: {total_subscriber_sum - global_total}")
print("="*70)

# Find podcasts that appear in multiple subscriber counts
print("\n5. Checking for podcasts counted in multiple subscribers...")
podcast_owners = defaultdict(set)
for email, info in subscriber_counts.items():
    for podcast_id in info['podcasts']:
        podcast_owners[podcast_id].add(email)

duplicated_podcasts = {k: list(v) for k, v in podcast_owners.items() if len(v) > 1}

if duplicated_podcasts:
    print(f"\n   ⚠️  Found {len(duplicated_podcasts)} podcast(s) counted in multiple subscribers:")
    for podcast_id, owners in duplicated_podcasts.items():
        print(f"\n      {podcast_id}:")
        for owner in owners:
            print(f"         - {owner}")
    
    duplicate_count = sum(len(owners) - 1 for owners in duplicated_podcasts.values())
    expected_total = total_subscriber_sum - duplicate_count
    print(f"\n   Expected total (subscriber sum - {duplicate_count} duplicates): {expected_total}")
else:
    print("\n   ✅ No podcasts counted in multiple subscribers")




