#!/usr/bin/env python3
"""
Compare podcasts in gwelz@jjay.cuny.edu account with podcast database.
Find which podcast is in the account but NOT in the database.
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
    
    print("="*70)
    print("COMPARING gwelz@jjay.cuny.edu PODCASTS WITH DATABASE")
    print("="*70)
    
    email = "gwelz@jjay.cuny.edu"
    
    # Get subscriber ID
    print(f"\n1. Finding subscriber: {email}...")
    subscriber_id = None
    subscribers = {}
    for sub_doc in db.collection('subscribers').stream():
        sub_data = sub_doc.to_dict() or {}
        subscribers[sub_doc.id] = sub_data.get('email', 'N/A')
        if sub_data.get('email') == email:
            subscriber_id = sub_doc.id
            break
    
    if not subscriber_id:
        print(f"   ❌ Subscriber not found: {email}")
        sys.exit(1)
    
    print(f"   ✅ Subscriber ID: {subscriber_id}")
    
    # Get podcasts from podcast_jobs
    print(f"\n2. Getting podcasts from podcast_jobs...")
    gwelz_from_jobs = set()
    jobs_info = {}
    jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        if canonical:
            gwelz_from_jobs.add(canonical)
            jobs_info[canonical] = {
                'title': result.get('title') or job_data.get('request', {}).get('topic', 'Untitled'),
                'status': job_data.get('status', 'unknown')
            }
    
    print(f"   Found {len(gwelz_from_jobs)} podcasts in podcast_jobs")
    
    # Get podcasts from episodes
    print(f"\n3. Getting podcasts from episodes collection...")
    gwelz_from_episodes = set()
    episodes_info = {}
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    for episode_doc in episodes_query:
        canonical = episode_doc.id
        gwelz_from_episodes.add(canonical)
        episode_data = episode_doc.to_dict() or {}
        episodes_info[canonical] = {
            'title': episode_data.get('title', episode_data.get('topic', 'Untitled'))
        }
    
    print(f"   Found {len(gwelz_from_episodes)} podcasts in episodes")
    
    # Union (all podcasts in account)
    gwelz_all = gwelz_from_jobs | gwelz_from_episodes
    print(f"\n   Union (all in account): {len(gwelz_all)}")
    
    # Get ALL episodes from database
    print(f"\n4. Getting ALL podcasts from database (episodes collection)...")
    all_database = set()
    all_episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
    for episode_doc in all_episodes_query:
        all_database.add(episode_doc.id)
    
    print(f"   Total in database: {len(all_database)}")
    
    # Find missing
    missing_in_db = gwelz_all - all_database
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    if missing_in_db:
        print(f"\n⚠️  Found {len(missing_in_db)} podcast(s) in gwelz account but NOT in database:")
        for canonical in sorted(missing_in_db):
            info = jobs_info.get(canonical, {})
            print(f"\n   {canonical}:")
            print(f"      Title: {info.get('title', 'N/A')}")
            print(f"      Status: {info.get('status', 'N/A')}")
            print(f"      ⚠️  In podcast_jobs but NOT in episodes collection")
    else:
        print(f"\n✅ All podcasts in account are in database")
    
    # Also check if any are in episodes but not in jobs
    missing_in_jobs = gwelz_from_episodes - gwelz_from_jobs
    if missing_in_jobs:
        print(f"\n📝 {len(missing_in_jobs)} podcast(s) in episodes but not in jobs (this is OK)")
    
    # Summary counts
    print("\n" + "="*70)
    print("SUMMARY COUNTS")
    print("="*70)
    print(f"Podcasts in podcast_jobs: {len(gwelz_from_jobs)}")
    print(f"Podcasts in episodes: {len(gwelz_from_episodes)}")
    print(f"Total unique in account (union): {len(gwelz_all)}")
    print(f"Total in database: {len(all_database)}")
    
    if missing_in_db:
        print(f"\n⚠️  Missing from database: {len(missing_in_db)}")
        print(f"\nLIST OF MISSING PODCASTS:")
        for canonical in sorted(missing_in_db):
            info = jobs_info.get(canonical, {})
            print(f"   - {canonical}: {info.get('title', 'N/A')}")
    
    # List all for reference
    print("\n" + "="*70)
    print("ALL PODCASTS IN gwelz@jjay.cuny.edu ACCOUNT:")
    print("="*70)
    for canonical in sorted(gwelz_all):
        in_db = "✓" if canonical in all_database else "✗"
        info = jobs_info.get(canonical) or episodes_info.get(canonical, {})
        print(f"   {in_db} {canonical}: {info.get('title', 'N/A')}")

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()




