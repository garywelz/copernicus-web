#!/usr/bin/env python3
"""
Investigate count discrepancy between total podcasts and subscriber sums
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

db = firestore.Client(database='copernicusai')

print("="*70)
print("INVESTIGATING COUNT DISCREPANCY")
print("="*70)

# Get all episodes
all_episodes = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    all_episodes.add(episode_doc.id)

print(f"\nTotal episodes: {len(all_episodes)}")

# Get all podcast_jobs with canonical filenames
all_jobs = set()
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        all_jobs.add(canonical)

print(f"Total podcast_jobs with canonical: {len(all_jobs)}")

# Get union (unique podcasts)
all_unique = all_episodes.union(all_jobs)
print(f"Total unique podcasts (union): {len(all_unique)}")

# Now check subscriber counts
print("\n" + "="*70)
print("SUBSCRIBER COUNTS (using MAX method - current):")
print("="*70)

subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

total_max_count = 0
total_union_count = 0

for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    subscriber_id = subscriber_doc.id
    email = subscriber_data.get('email', 'N/A')
    
    # Count from podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    jobs_canonicals = set()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            jobs_canonicals.add(canonical)
    
    # Count from episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    episodes_canonicals = set()
    for episode_doc in episodes_query:
        episodes_canonicals.add(episode_doc.id)
    
    # MAX method (current - WRONG)
    max_count = max(len(jobs_canonicals), len(episodes_canonicals))
    
    # UNION method (correct)
    union_canonicals = jobs_canonicals.union(episodes_canonicals)
    union_count = len(union_canonicals)
    
    total_max_count += max_count
    total_union_count += union_count
    
    if max_count != union_count:
        print(f"  {email}: MAX={max_count}, UNION={union_count} (DIFFERENCE: {max_count - union_count})")
    else:
        print(f"  {email}: {max_count}")

print(f"\nTotal using MAX method: {total_max_count}")
print(f"Total using UNION method: {total_union_count}")
print(f"Difference: {total_max_count - total_union_count}")

print("\n" + "="*70)
print("SUMMARY:")
print("="*70)
print(f"Episodes collection: {len(all_episodes)}")
print(f"Podcast_jobs with canonical: {len(all_jobs)}")
print(f"Unique podcasts (union): {len(all_unique)}")
print(f"\nSubscriber sum (MAX method - WRONG): {total_max_count}")
print(f"Subscriber sum (UNION method - CORRECT): {total_union_count}")




