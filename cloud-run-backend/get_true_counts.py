#!/usr/bin/env python3
"""
Get true counts for each subscriber
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from collections import defaultdict

try:
    db = firestore.Client(database='copernicusai')
    
    print("="*70)
    print("TRUE SUBSCRIBER COUNTS FROM EPISODES COLLECTION")
    print("="*70)
    
    # Get all subscribers
    subscribers = {}
    for sub_doc in db.collection('subscribers').stream():
        sub_data = sub_doc.to_dict() or {}
        subscribers[sub_doc.id] = sub_data.get('email', 'N/A')
    
    # Count episodes per subscriber
    counts = defaultdict(int)
    no_subscriber = []
    
    for ep_doc in db.collection(EPISODE_COLLECTION_NAME).stream():
        ep_data = ep_doc.to_dict() or {}
        sub_id = ep_data.get('subscriber_id')
        
        if sub_id and sub_id in subscribers:
            counts[subscribers[sub_id]] += 1
        else:
            no_subscriber.append({
                'id': ep_doc.id,
                'subscriber_id': sub_id,
                'title': ep_data.get('title', 'Untitled')
            })
    
    print("\nSubscriber counts (from episodes collection):")
    print("-" * 70)
    total = 0
    for email in sorted(counts.keys()):
        count = counts[email]
        print(f"  {email}: {count}")
        total += count
    
    print(f"\n{'='*70}")
    print(f"Sum of subscriber counts: {total}")
    
    # Get total episodes
    all_episodes = list(db.collection(EPISODE_COLLECTION_NAME).stream())
    print(f"Total episodes in collection: {len(all_episodes)}")
    print(f"Episodes without valid subscriber: {len(no_subscriber)}")
    print(f"Difference: {len(all_episodes) - total}")
    
    if no_subscriber:
        print(f"\n⚠️  Episodes without valid subscriber:")
        for ep in no_subscriber[:10]:
            print(f"  - {ep['id']}: {ep['title']}")
            print(f"    subscriber_id: {ep['subscriber_id'] or 'None'}")
    
    # Check gwelz specifically
    print(f"\n{'='*70}")
    print("DETAILED CHECK FOR gwelz@jjay.cuny.edu:")
    print("="*70)
    
    gwelz_email = "gwelz@jjay.cuny.edu"
    gwelz_id = None
    for sub_id, email in subscribers.items():
        if email == gwelz_email:
            gwelz_id = sub_id
            break
    
    if gwelz_id:
        gwelz_episodes = []
        for ep_doc in db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', gwelz_id).stream():
            ep_data = ep_doc.to_dict() or {}
            gwelz_episodes.append({
                'id': ep_doc.id,
                'title': ep_data.get('title', 'Untitled'),
                'has_audio': bool(ep_data.get('audio_url'))
            })
        
        print(f"\n{gwelz_email} has {len(gwelz_episodes)} episodes in episodes collection")
        
        # Check for missing audio
        incomplete = [e for e in gwelz_episodes if not e['has_audio']]
        if incomplete:
            print(f"\n⚠️  {len(incomplete)} episode(s) without audio:")
            for ep in incomplete:
                print(f"  - {ep['id']}: {ep['title']}")
        else:
            print(f"\n✅ All episodes have audio")
    else:
        print(f"\n❌ Subscriber not found: {gwelz_email}")

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()




