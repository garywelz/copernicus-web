#!/usr/bin/env python3
"""
Simple comparison: Get podcasts from gwelz account vs database.
Just comparing two lists of filenames.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

print("Starting comparison...")

db = firestore.Client(database='copernicusai')
print("Connected to Firestore")

# Find gwelz subscriber ID
print("Finding gwelz@jjay.cuny.edu...")
gwelz_id = None
for sub_doc in db.collection('subscribers').stream():
    if sub_doc.to_dict().get('email') == 'gwelz@jjay.cuny.edu':
        gwelz_id = sub_doc.id
        print(f"Found subscriber ID: {gwelz_id}")
        break

if not gwelz_id:
    print("ERROR: Subscriber not found")
    sys.exit(1)

# Get podcasts from podcast_jobs
print("Getting podcasts from podcast_jobs...")
gwelz_jobs = set()
for job_doc in db.collection('podcast_jobs').where('subscriber_id', '==', gwelz_id).stream():
    canonical = job_doc.to_dict().get('result', {}).get('canonical_filename')
    if canonical:
        gwelz_jobs.add(canonical)

print(f"Found {len(gwelz_jobs)} in podcast_jobs")

# Get podcasts from episodes for gwelz
print("Getting podcasts from episodes for gwelz...")
gwelz_episodes = set()
for ep_doc in db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', gwelz_id).stream():
    gwelz_episodes.add(ep_doc.id)

print(f"Found {len(gwelz_episodes)} in episodes")

# Union = all in account
gwelz_all = gwelz_jobs | gwelz_episodes
print(f"Total in gwelz account (union): {len(gwelz_all)}")

# Get ALL episodes in database
print("Getting ALL episodes from database...")
all_episodes = set()
for ep_doc in db.collection(EPISODE_COLLECTION_NAME).stream():
    all_episodes.add(ep_doc.id)

print(f"Total in database: {len(all_episodes)}")

# Compare
print("\n" + "="*70)
print("COMPARISON")
print("="*70)

missing = gwelz_all - all_episodes

if missing:
    print(f"\nMISSING FROM DATABASE ({len(missing)} podcast(s)):")
    for canonical in sorted(missing):
        print(f"  - {canonical}")
else:
    print("\nAll podcasts in account are in database.")

print(f"\nSummary:")
print(f"  In gwelz account: {len(gwelz_all)}")
print(f"  In database: {len(all_episodes)}")
print(f"  Missing: {len(missing)}")




