#!/usr/bin/env python3
"""
Find the TRUE counts for each subscriber by comparing episodes collection
with what's actually assigned to each subscriber.
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
print("FINDING TRUE SUBSCRIBER COUNTS")
print("="*70)

# Get all episodes with their subscriber_ids
print("\n1. Getting all episodes from episodes collection...")
all_episodes = {}
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    episode_data = episode_doc.to_dict() or {}
    canonical = episode_doc.id
    subscriber_id = episode_data.get('subscriber_id')
    title = episode_data.get('title', 'Untitled')
    has_audio = bool(episode_data.get('audio_url'))
    
    all_episodes[canonical] = {
        'subscriber_id': subscriber_id,
        'title': title,
        'has_audio': has_audio,
        'audio_url': episode_data.get('audio_url')
    }

print(f"   Total episodes in collection: {len(all_episodes)}")

# Get all subscribers
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
        'episodes': [],
        'jobs': []
    }

# Count episodes per subscriber
print("\n3. Counting episodes per subscriber...")
episodes_per_subscriber = defaultdict(list)
episodes_without_subscriber = []

for canonical, episode_data in all_episodes.items():
    sub_id = episode_data.get('subscriber_id')
    if sub_id:
        if sub_id in subscriber_info:
            episodes_per_subscriber[sub_id].append(canonical)
        else:
            episodes_without_subscriber.append({
                'canonical': canonical,
                'subscriber_id': sub_id,
                'title': episode_data.get('title')
            })
    else:
        episodes_without_subscriber.append({
            'canonical': canonical,
            'subscriber_id': None,
            'title': episode_data.get('title')
        })

# Count podcast_jobs per subscriber
print("\n4. Counting podcast_jobs per subscriber...")
jobs_per_subscriber = defaultdict(list)

jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    subscriber_id = job_data.get('subscriber_id')
    
    if canonical and subscriber_id:
        jobs_per_subscriber[subscriber_id].append(canonical)

# Now print detailed breakdown
print("\n" + "="*70)
print("SUBSCRIBER COUNTS (from episodes collection):")
print("="*70)

total_episodes_count = 0
for subscriber_id, info in subscriber_info.items():
    email = info['email']
    episodes_list = episodes_per_subscriber.get(subscriber_id, [])
    jobs_list = jobs_per_subscriber.get(subscriber_id, [])
    
    # Count unique from episodes
    episodes_count = len(episodes_list)
    
    # Count unique from jobs
    jobs_count = len(set(jobs_list))
    
    # Check for podcasts in jobs but not in episodes for this subscriber
    episodes_set = set(episodes_list)
    jobs_set = set(jobs_list)
    only_in_jobs = jobs_set - episodes_set
    only_in_episodes = episodes_set - jobs_set
    
    total_episodes_count += episodes_count
    
    print(f"\n{email}:")
    print(f"  Episodes collection: {episodes_count} podcasts")
    print(f"  Podcast_jobs collection: {jobs_count} podcasts")
    
    if only_in_jobs:
        print(f"  ⚠️  {len(only_in_jobs)} podcast(s) in jobs but NOT in episodes for this subscriber:")
        for pid in list(only_in_jobs)[:5]:  # Show first 5
            print(f"      - {pid}")
    
    if only_in_episodes:
        print(f"  ⚠️  {len(only_in_episodes)} podcast(s) in episodes but NOT in jobs for this subscriber")
    
    if episodes_count != jobs_count:
        print(f"  ⚠️  MISMATCH: episodes={episodes_count}, jobs={jobs_count}, difference={abs(episodes_count - jobs_count)}")

print(f"\n" + "="*70)
print(f"TOTALS:")
print(f"  Sum of subscriber episode counts: {total_episodes_count}")
print(f"  Total episodes in collection: {len(all_episodes)}")
print(f"  Episodes without valid subscriber: {len(episodes_without_subscriber)}")
print("="*70)

if episodes_without_subscriber:
    print(f"\n⚠️  Found {len(episodes_without_subscriber)} episode(s) without valid subscriber assignment:")
    for ep in episodes_without_subscriber[:10]:  # Show first 10
        print(f"  - {ep['canonical']}: {ep['title']}")
        print(f"    subscriber_id: {ep['subscriber_id'] or 'None'}")

# Check for incomplete podcasts (missing audio)
print("\n" + "="*70)
print("CHECKING FOR INCOMPLETE PODCASTS (missing audio):")
print("="*70)

incomplete = []
for canonical, episode_data in all_episodes.items():
    if not episode_data.get('has_audio'):
        incomplete.append({
            'canonical': canonical,
            'title': episode_data.get('title'),
            'subscriber_id': episode_data.get('subscriber_id')
        })

if incomplete:
    print(f"\n⚠️  Found {len(incomplete)} podcast(s) without audio:")
    for ep in incomplete[:10]:
        print(f"  - {ep['canonical']}: {ep['title']}")
else:
    print("\n✅ All podcasts have audio")

# Summary
print("\n" + "="*70)
print("SUMMARY:")
print("="*70)
print(f"Total episodes: {len(all_episodes)}")
print(f"Sum of subscriber counts: {total_episodes_count}")
print(f"Difference: {len(all_episodes) - total_episodes_count}")
if len(all_episodes) != total_episodes_count:
    print(f"\n⚠️  The difference ({len(all_episodes) - total_episodes_count}) is due to:")
    print(f"   - Episodes without valid subscriber: {len(episodes_without_subscriber)}")




