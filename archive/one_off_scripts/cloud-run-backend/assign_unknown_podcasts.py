#!/usr/bin/env python3
"""
Script to assign podcasts with "Unknown" subscriber to gwelz@jjay.cuny.edu
"""

import hashlib
from google.cloud import firestore
from datetime import datetime

def generate_subscriber_id(email: str) -> str:
    """Generate subscriber ID from email (same as backend)"""
    return hashlib.sha256(email.encode()).hexdigest()

def find_podcasts_by_titles(db, titles):
    """Find podcast IDs by their titles (flexible matching)"""
    all_podcasts = db.collection('podcast_jobs').stream()
    found_podcasts = []
    
    # Normalize search titles (lowercase, strip whitespace)
    search_titles = [t.lower().strip() for t in titles]
    
    for podcast in all_podcasts:
        data = podcast.to_dict()
        title = data.get('result', {}).get('title') or data.get('request', {}).get('topic', '')
        title_normalized = title.lower().strip()
        
        # Check if this title matches any in our list (case-insensitive, flexible)
        for search_title in search_titles:
            if title_normalized == search_title or search_title in title_normalized or title_normalized in search_title:
                found_podcasts.append({
                    'podcast_id': podcast.id,
                    'title': title,
                    'current_subscriber': data.get('subscriber_id', None)
                })
                break
    
    return found_podcasts

def find_unknown_podcasts(db):
    """Find all podcasts with Unknown subscriber (missing subscriber_id OR subscriber not found)"""
    all_podcasts = db.collection('podcast_jobs').stream()
    unknown_podcasts = []
    
    for podcast in all_podcasts:
        data = podcast.to_dict()
        subscriber_id = data.get('subscriber_id')
        title = data.get('result', {}).get('title') or data.get('request', {}).get('topic', 'Unknown')
        
        # Check if subscriber_id is missing OR subscriber document doesn't exist
        if not subscriber_id:
            unknown_podcasts.append({
                'podcast_id': podcast.id,
                'title': title,
                'created_at': data.get('created_at', 'Unknown'),
                'reason': 'missing_subscriber_id'
            })
        else:
            # Check if subscriber document exists
            try:
                subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
                if not subscriber_doc.exists:
                    unknown_podcasts.append({
                        'podcast_id': podcast.id,
                        'title': title,
                        'created_at': data.get('created_at', 'Unknown'),
                        'reason': 'subscriber_not_found',
                        'subscriber_id': subscriber_id
                    })
            except:
                # If we can't check, assume it's unknown
                unknown_podcasts.append({
                    'podcast_id': podcast.id,
                    'title': title,
                    'created_at': data.get('created_at', 'Unknown'),
                    'reason': 'lookup_error',
                    'subscriber_id': subscriber_id
                })
    
    return unknown_podcasts

def assign_podcasts_to_subscriber(db, podcast_ids, subscriber_id, subscriber_email):
    """Assign podcasts to a subscriber"""
    updated_count = 0
    failed_count = 0
    
    for podcast_id in podcast_ids:
        try:
            podcast_doc = db.collection('podcast_jobs').document(podcast_id).get()
            if not podcast_doc.exists:
                print(f"❌ Podcast {podcast_id} not found")
                failed_count += 1
                continue
            
            # Update the podcast
            db.collection('podcast_jobs').document(podcast_id).update({
                'subscriber_id': subscriber_id,
                'assigned_by_script': True,
                'assigned_at': datetime.utcnow().isoformat()
            })
            
            data = podcast_doc.to_dict()
            title = data.get('result', {}).get('title') or data.get('request', {}).get('topic', 'Unknown')
            print(f"✅ Assigned: {title}")
            updated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to assign podcast {podcast_id}: {e}")
            failed_count += 1
    
    # Update subscriber's podcast count
    if updated_count > 0:
        subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
        if subscriber_doc.exists:
            subscriber_data = subscriber_doc.to_dict()
            current_count = subscriber_data.get('podcasts_generated', 0)
            db.collection('subscribers').document(subscriber_id).update({
                'podcasts_generated': current_count + updated_count
            })
    
    return updated_count, failed_count

def main():
    # Initialize Firestore
    db = firestore.Client(database='copernicusai')
    
    # Find subscriber
    target_email = 'gwelz@jjay.cuny.edu'
    subscriber_id = generate_subscriber_id(target_email)
    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
    
    if not subscriber_doc.exists:
        print(f"❌ Subscriber not found: {target_email}")
        return
    
    print(f"✅ Found subscriber: {target_email} (ID: {subscriber_id[:32]}...)")
    
    print(f"\n🔍 Finding all podcasts with 'Unknown' or missing subscriber...")
    
    # Find all unknown podcasts
    unknown_podcasts = find_unknown_podcasts(db)
    
    if not unknown_podcasts:
        print("✅ No podcasts with missing subscriber_id found. All podcasts are already assigned!")
        return
    
    print(f"\n✅ Found {len(unknown_podcasts)} podcasts with Unknown subscriber:")
    for i, p in enumerate(unknown_podcasts, 1):
        reason = p.get('reason', 'unknown')
        sub_id = p.get('subscriber_id', 'None')
        print(f"  {i}. {p['title']} (reason: {reason}, subscriber_id: {sub_id[:32] if sub_id != 'None' else 'None'}...)")
    
    # Get all podcast IDs from unknown podcasts
    podcast_ids = [p['podcast_id'] for p in unknown_podcasts]
    
    print(f"\n⚠️  Ready to assign {len(podcast_ids)} podcasts to {target_email}")
    response = input("Proceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Assign podcasts
    print("\n🔄 Assigning podcasts...")
    updated, failed = assign_podcasts_to_subscriber(db, podcast_ids, subscriber_id, target_email)
    
    print(f"\n✅ Done! Assigned: {updated}, Failed: {failed}")

if __name__ == '__main__':
    main()

