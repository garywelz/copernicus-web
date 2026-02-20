#!/usr/bin/env python3
"""
Count podcasts by subscriber by comparing podcast database to subscriber lists.
This script queries the episodes collection and matches podcasts to subscribers by filename.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

# Initialize Firestore
db = firestore.Client(database='copernicusai')

def get_all_podcasts_from_database():
    """Get all podcasts from the episodes collection with their canonical filenames and subscriber info."""
    print("\n=== Fetching all podcasts from database (episodes collection) ===\n")
    
    podcasts = {}
    episodes_ref = db.collection(EPISODE_COLLECTION_NAME).stream()
    
    for episode_doc in episodes_ref:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id
        subscriber_id = episode_data.get('subscriber_id', 'unknown')
        subscriber_email = episode_data.get('subscriber_email', 'unknown')
        title = episode_data.get('title', episode_data.get('topic', 'Untitled'))
        
        podcasts[canonical] = {
            'canonical': canonical,
            'subscriber_id': subscriber_id,
            'subscriber_email': subscriber_email,
            'title': title,
            'submitted_to_rss': episode_data.get('submitted_to_rss', False)
        }
    
    print(f"Total podcasts in database: {len(podcasts)}")
    return podcasts

def get_subscriber_lists():
    """Get all subscribers and their associated podcasts from both podcast_jobs and episodes."""
    print("\n=== Fetching subscriber lists ===\n")
    
    subscribers = {}
    
    # First, get all unique subscriber_ids and emails from episodes
    episodes_ref = db.collection(EPISODE_COLLECTION_NAME).stream()
    for episode_doc in episodes_ref:
        episode_data = episode_doc.to_dict() or {}
        subscriber_id = episode_data.get('subscriber_id')
        subscriber_email = episode_data.get('subscriber_email')
        
        if subscriber_id and subscriber_id not in subscribers:
            subscribers[subscriber_id] = {
                'subscriber_id': subscriber_id,
                'email': subscriber_email or 'unknown',
                'podcasts_from_episodes': set(),
                'podcasts_from_jobs': set()
            }
        
        if subscriber_id:
            canonical = episode_doc.id
            subscribers[subscriber_id]['podcasts_from_episodes'].add(canonical)
    
    # Also check podcast_jobs
    jobs_ref = db.collection('podcast_jobs').stream()
    for job_doc in jobs_ref:
        job_data = job_doc.to_dict() or {}
        subscriber_id = job_data.get('subscriber_id')
        
        if subscriber_id:
            if subscriber_id not in subscribers:
                subscribers[subscriber_id] = {
                    'subscriber_id': subscriber_id,
                    'email': job_data.get('subscriber_email', 'unknown'),
                    'podcasts_from_episodes': set(),
                    'podcasts_from_jobs': set()
                }
            
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename')
            if canonical:
                subscribers[subscriber_id]['podcasts_from_jobs'].add(canonical)
    
    return subscribers

def compare_and_report():
    """Compare database podcasts to subscriber lists and report counts."""
    
    # Get all podcasts from database
    all_podcasts = get_all_podcasts_from_database()
    
    # Get subscriber lists
    subscribers = get_subscriber_lists()
    
    print("\n" + "="*80)
    print("COMPARISON REPORT")
    print("="*80 + "\n")
    
    # Group podcasts by subscriber
    podcasts_by_subscriber = {}
    unassigned_podcasts = []
    
    for canonical, podcast_info in all_podcasts.items():
        subscriber_id = podcast_info['subscriber_id']
        if subscriber_id and subscriber_id != 'unknown':
            if subscriber_id not in podcasts_by_subscriber:
                podcasts_by_subscriber[subscriber_id] = {
                    'email': podcast_info['subscriber_email'],
                    'podcasts': []
                }
            podcasts_by_subscriber[subscriber_id]['podcasts'].append(podcast_info)
        else:
            unassigned_podcasts.append(podcast_info)
    
    # Report counts by subscriber
    print("PODCASTS BY SUBSCRIBER (from database):")
    print("-" * 80)
    
    total_assigned = 0
    for subscriber_id, data in sorted(podcasts_by_subscriber.items(), key=lambda x: len(x[1]['podcasts']), reverse=True):
        email = data['email'] or 'unknown'
        count = len(data['podcasts'])
        total_assigned += count
        
        # Get union count from subscriber lists
        union_count = 0
        if subscriber_id in subscribers:
            union_set = subscribers[subscriber_id]['podcasts_from_episodes'] | subscribers[subscriber_id]['podcasts_from_jobs']
            union_count = len(union_set)
        
        print(f"\n{subscriber_id} ({email})")
        print(f"  Database count: {count}")
        print(f"  Union count (episodes ∪ jobs): {union_count}")
        print(f"  Difference: {union_count - count}")
        
        if union_count != count:
            print(f"  ⚠️  MISMATCH DETECTED!")
            
            # Find the difference
            db_canonicals = {p['canonical'] for p in data['podcasts']}
            if subscriber_id in subscribers:
                union_set = subscribers[subscriber_id]['podcasts_from_episodes'] | subscribers[subscriber_id]['podcasts_from_jobs']
                missing_in_db = union_set - db_canonicals
                extra_in_db = db_canonicals - union_set
                
                if missing_in_db:
                    print(f"  Missing in database: {missing_in_db}")
                if extra_in_db:
                    print(f"  Extra in database: {extra_in_db}")
    
    print(f"\nTotal assigned: {total_assigned}")
    print(f"Unassigned: {len(unassigned_podcasts)}")
    print(f"Total in database: {len(all_podcasts)}")
    print(f"Expected total: {total_assigned + len(unassigned_podcasts)}")
    
    if unassigned_podcasts:
        print("\n" + "-" * 80)
        print("UNASSIGNED PODCASTS (subscriber_id is 'unknown' or missing):")
        for p in unassigned_podcasts[:10]:  # Show first 10
            print(f"  {p['canonical']}: {p['title']}")
        if len(unassigned_podcasts) > 10:
            print(f"  ... and {len(unassigned_podcasts) - 10} more")
    
    # Show the specific case: gary.welz@me.com
    print("\n" + "="*80)
    print("SPECIFIC CHECK: gary.welz@me.com")
    print("="*80)
    
    gary_subscriber_id = None
    for sub_id, data in subscribers.items():
        if data['email'] == 'gary.welz@me.com':
            gary_subscriber_id = sub_id
            break
    
    if gary_subscriber_id:
        print(f"\nSubscriber ID: {gary_subscriber_id}")
        
        # Count from database
        db_count = len([p for p in all_podcasts.values() if p['subscriber_id'] == gary_subscriber_id])
        print(f"Database count: {db_count}")
        
        # Count from union
        union_set = subscribers[gary_subscriber_id]['podcasts_from_episodes'] | subscribers[gary_subscriber_id]['podcasts_from_jobs']
        union_count = len(union_set)
        print(f"Union count (episodes ∪ jobs): {union_count}")
        
        # List all podcasts
        db_canonicals = {p['canonical'] for p in all_podcasts.values() if p['subscriber_id'] == gary_subscriber_id}
        print(f"\nPodcasts in database:")
        for canonical in sorted(db_canonicals):
            podcast = all_podcasts[canonical]
            print(f"  {canonical}: {podcast['title']}")
        
        print(f"\nPodcasts in union (episodes ∪ jobs):")
        for canonical in sorted(union_set):
            in_db = "✓" if canonical in db_canonicals else "✗"
            print(f"  {in_db} {canonical}")
            if canonical in all_podcasts:
                print(f"      Title: {all_podcasts[canonical]['title']}")
            else:
                print(f"      Title: (not in database)")
        
        # Find the discrepancy
        missing_in_db = union_set - db_canonicals
        extra_in_db = db_canonicals - union_set
        
        if missing_in_db:
            print(f"\n⚠️  Missing in database ({len(missing_in_db)}):")
            for canonical in sorted(missing_in_db):
                print(f"  {canonical}")
        if extra_in_db:
            print(f"\n⚠️  Extra in database ({len(extra_in_db)}):")
            for canonical in sorted(extra_in_db):
                print(f"  {canonical}: {all_podcasts[canonical]['title']}")
    else:
        print("Subscriber not found!")

if __name__ == '__main__':
    try:
        compare_and_report()
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()

