#!/usr/bin/env python3
"""
Compare podcasts in gwelz@jjay.cuny.edu account with podcast database and "all podcasts" list.
Find which podcast is in the account but NOT in the database/all podcasts lists.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

try:
    db = firestore.Client(database='copernicusai')
except Exception as e:
    print(f"Error connecting to Firestore: {e}")
    sys.exit(1)

print("="*80)
print("FINDING MISSING PODCAST IN gwelz@jjay.cuny.edu ACCOUNT")
print("="*80)

email = "gwelz@jjay.cuny.edu"

# 1. Get subscriber ID
print(f"\n1. Finding subscriber: {email}...")
subscriber_doc = None
subscriber_id = None
for sub_doc in db.collection('subscribers').stream():
    if sub_doc.to_dict().get('email') == email:
        subscriber_doc = sub_doc
        subscriber_id = sub_doc.id
        break

if not subscriber_id:
    print(f"   ❌ Subscriber not found: {email}")
    sys.exit(1)

print(f"   ✅ Found subscriber ID: {subscriber_id}")

# 2. Get all podcasts from gwelz@jjay.cuny.edu account (from podcast_jobs)
print(f"\n2. Getting podcasts from podcast_jobs for {email}...")
gwelz_podcasts_from_jobs = set()
gwelz_podcasts_info = {}

jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    
    if canonical:
        gwelz_podcasts_from_jobs.add(canonical)
        gwelz_podcasts_info[canonical] = {
            'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
            'status': job_data.get('status', 'unknown'),
            'source': 'podcast_jobs'
        }

print(f"   Found {len(gwelz_podcasts_from_jobs)} podcasts in podcast_jobs")

# 3. Get all podcasts from episodes for gwelz@jjay.cuny.edu
print(f"\n3. Getting podcasts from episodes collection for {email}...")
gwelz_podcasts_from_episodes = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
for episode_doc in episodes_query:
    canonical = episode_doc.id
    gwelz_podcasts_from_episodes.add(canonical)
    episode_data = episode_doc.to_dict() or {}
    
    if canonical not in gwelz_podcasts_info:
        gwelz_podcasts_info[canonical] = {
            'title': episode_data.get('title', episode_data.get('topic', 'Untitled')),
            'status': 'completed',
            'source': 'episodes'
        }
    else:
        # Update with episode data
        gwelz_podcasts_info[canonical]['title'] = episode_data.get('title') or gwelz_podcasts_info[canonical].get('title', 'Untitled')
        gwelz_podcasts_info[canonical]['source'] = 'both'

print(f"   Found {len(gwelz_podcasts_from_episodes)} podcasts in episodes")

# 4. Union of all podcasts in gwelz account (what "View Podcasts" would show)
gwelz_all_podcasts = gwelz_podcasts_from_jobs | gwelz_podcasts_from_episodes
print(f"\n   Union count (what 'View Podcasts' shows): {len(gwelz_all_podcasts)}")

# 5. Get ALL podcasts from episodes collection (the database)
print(f"\n4. Getting ALL podcasts from episodes collection (podcast database)...")
all_database_podcasts = set()
all_episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in all_episodes_query:
    all_database_podcasts.add(episode_doc.id)

print(f"   Total podcasts in database: {len(all_database_podcasts)}")

# 6. Compare: Find podcasts in gwelz account but NOT in database
print(f"\n5. Comparing gwelz account with database...")
missing_in_database = gwelz_all_podcasts - all_database_podcasts

if missing_in_database:
    print(f"\n   ⚠️  Found {len(missing_in_database)} podcast(s) in gwelz account but NOT in database:")
    for canonical in sorted(missing_in_database):
        info = gwelz_podcasts_info.get(canonical, {})
        print(f"\n      {canonical}:")
        print(f"        Title: {info.get('title', 'N/A')}")
        print(f"        Source: {info.get('source', 'N/A')}")
        print(f"        Status: {info.get('status', 'N/A')}")
        print(f"        ⚠️  This podcast is in podcast_jobs but was deleted from episodes collection")
else:
    print(f"\n   ✅ All podcasts in gwelz account are also in the database")

# 7. Check for podcasts in database but not assigned to gwelz
extra_in_database = all_database_podcasts - gwelz_all_podcasts
# This is expected - other subscribers have podcasts

# 8. Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Podcasts in gwelz@jjay.cuny.edu account (from podcast_jobs): {len(gwelz_podcasts_from_jobs)}")
print(f"Podcasts in gwelz@jjay.cuny.edu account (from episodes): {len(gwelz_podcasts_from_episodes)}")
print(f"Total unique podcasts in gwelz account (union): {len(gwelz_all_podcasts)}")
print(f"Total podcasts in database: {len(all_database_podcasts)}")

if missing_in_database:
    print(f"\n⚠️  DISCREPANCY FOUND:")
    print(f"   {len(missing_in_database)} podcast(s) in gwelz account but NOT in database")
    print(f"\n   These are likely:")
    print(f"   - Podcasts that were deleted from episodes collection")
    print(f"   - Podcasts that exist in podcast_jobs but were never promoted to episodes")
    print(f"   - Or podcasts assigned to wrong subscriber in episodes")
    
    print(f"\n   LIST OF MISSING PODCASTS:")
    for canonical in sorted(missing_in_database):
        info = gwelz_podcasts_info.get(canonical, {})
        print(f"   - {canonical}: {info.get('title', 'N/A')}")
else:
    print(f"\n✅ No discrepancy - all podcasts in account are in database")

# 9. List all podcasts for reference
print("\n" + "="*80)
print("ALL PODCASTS IN gwelz@jjay.cuny.edu ACCOUNT (sorted by filename):")
print("="*80)
for canonical in sorted(gwelz_all_podcasts):
    info = gwelz_podcasts_info.get(canonical, {})
    in_db = "✓" if canonical in all_database_podcasts else "✗"
    print(f"   {in_db} {canonical}: {info.get('title', 'N/A')}")

print("\nDone!")

except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()

