#!/usr/bin/env python3
"""
Find why subscriber sum (65) doesn't match total (64)
Most likely: one podcast is assigned to two subscribers
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
print("FINDING COUNT DISCREPANCY: 65 vs 64")
print("="*70)

# Map: podcast_id -> list of subscriber_ids that claim it
podcast_to_subscribers = defaultdict(set)

# Check all episodes
print("\n1. Checking episodes collection...")
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    episode_data = episode_doc.to_dict() or {}
    canonical = episode_doc.id
    sub_id = episode_data.get('subscriber_id')
    if sub_id:
        podcast_to_subscribers[canonical].add(('episodes', sub_id))

# Check all podcast_jobs
print("2. Checking podcast_jobs collection...")
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        sub_id = job_data.get('subscriber_id')
        if sub_id:
            podcast_to_subscribers[canonical].add(('podcast_jobs', sub_id))

# Find podcasts with multiple subscribers
print("\n3. Finding podcasts assigned to multiple subscribers...")
multi_sub_podcasts = {}
for podcast_id, subscribers in podcast_to_subscribers.items():
    # Get unique subscriber IDs
    unique_subs = set(sub[1] for sub in subscribers)
    if len(unique_subs) > 1:
        multi_sub_podcasts[podcast_id] = {
            'subscribers': list(unique_subs),
            'sources': list(subscribers)
        }

if multi_sub_podcasts:
    print(f"\n   ⚠️  Found {len(multi_sub_podcasts)} podcast(s) assigned to multiple subscribers:")
    for podcast_id, info in multi_sub_podcasts.items():
        print(f"\n   {podcast_id}:")
        # Get subscriber emails
        for sub_id in info['subscribers']:
            sub_doc = db.collection('subscribers').document(sub_id).get()
            if sub_doc.exists:
                email = sub_doc.to_dict().get('email', 'N/A')
                print(f"      - {email} ({sub_id[:16]}...)")
            else:
                print(f"      - Unknown subscriber ({sub_id[:16]}...)")
        
        # Check which collections
        sources = info['sources']
        has_episode = any(s[0] == 'episodes' for s in sources)
        has_job = any(s[0] == 'podcast_jobs' for s in sources)
        print(f"      Sources: episodes={has_episode}, podcast_jobs={has_job}")
else:
    print("   ✅ No podcasts assigned to multiple subscribers")

# Now calculate actual counts
print("\n4. Calculating subscriber counts (union method)...")
subscribers_ref = db.collection('subscribers')
subscribers = subscribers_ref.stream()

subscriber_podcasts = defaultdict(set)
for subscriber_doc in subscribers:
    subscriber_data = subscriber_doc.to_dict() or {}
    subscriber_id = subscriber_doc.id
    email = subscriber_data.get('email', 'N/A')
    
    # From podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            subscriber_podcasts[email].add(canonical)
    
    # From episodes
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    for episode_doc in episodes_query:
        subscriber_podcasts[email].add(episode_doc.id)

print("\n   Subscriber counts:")
total = 0
for email, podcasts in subscriber_podcasts.items():
    count = len(podcasts)
    print(f"      {email}: {count}")
    total += count

print(f"\n   Subscriber sum: {total}")

# Global total (episodes only - what the database endpoint shows)
all_episodes_set = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    all_episodes_set.add(episode_doc.id)

global_total = len(all_episodes_set)
print(f"\n5. Global total (episodes collection only): {global_total}")

print(f"\n" + "="*70)
print(f"RESULT:")
print(f"   Subscriber sum: {total}")
print(f"   Global total: {global_total}")
print(f"   Difference: {total - global_total}")
print("="*70)

if total > global_total:
    print(f"\n   The discrepancy is {total - global_total} podcast(s).")
    print(f"   This means {total - global_total} podcast(s) are counted in subscriber sums")
    print(f"   but don't exist in the episodes collection (which is used for the global total).")
    print(f"\n   These podcasts are likely only in podcast_jobs but not in episodes yet.")




