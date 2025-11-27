#!/usr/bin/env python3
"""
Script to reassign podcasts from one subscriber to another.
Run this to fix podcasts incorrectly assigned to john.covington and move them to gwelz@jjay.cuny.edu
"""

import hashlib
import sys
from google.cloud import firestore

def generate_subscriber_id(email: str) -> str:
    """Generate subscriber ID from email (same as backend)"""
    return hashlib.sha256(email.encode()).hexdigest()

def find_subscriber_by_email(db, email: str):
    """Find subscriber document by email"""
    subscriber_id = generate_subscriber_id(email)
    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
    
    if subscriber_doc.exists:
        return subscriber_doc
    return None

def list_podcasts_for_subscriber(db, subscriber_id: str):
    """List all podcasts for a subscriber"""
    podcasts = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    podcast_list = []
    for podcast in podcasts:
        data = podcast.to_dict()
        podcast_list.append({
            'podcast_id': podcast.id,
            'title': data.get('result', {}).get('title') or data.get('request', {}).get('topic', 'Untitled'),
            'created_at': str(data.get('created_at', 'Unknown'))
        })
    return podcast_list

def reassign_podcasts(db, from_subscriber_id: str, to_subscriber_id: str, podcast_ids=None):
    """Reassign podcasts from one subscriber to another"""
    if podcast_ids is None:
        # Get all podcasts from source subscriber
        podcasts_query = db.collection('podcast_jobs').where('subscriber_id', '==', from_subscriber_id)
        podcast_ids = [podcast.id for podcast in podcasts_query.stream()]
    
    print(f"\n📋 Found {len(podcast_ids)} podcasts to reassign")
    
    updated_count = 0
    failed_count = 0
    
    for podcast_id in podcast_ids:
        try:
            podcast_doc = db.collection('podcast_jobs').document(podcast_id).get()
            if not podcast_doc.exists:
                print(f"❌ Podcast {podcast_id} not found")
                failed_count += 1
                continue
            
            podcast_data = podcast_doc.to_dict()
            current_subscriber = podcast_data.get('subscriber_id')
            
            if current_subscriber != from_subscriber_id:
                print(f"⚠️  Podcast {podcast_id} belongs to different subscriber (expected {from_subscriber_id}, found {current_subscriber})")
                failed_count += 1
                continue
            
            # Update the podcast
            db.collection('podcast_jobs').document(podcast_id).update({
                'subscriber_id': to_subscriber_id,
                'reassigned_by_script': True,
                'previous_subscriber_id': from_subscriber_id
            })
            
            title = podcast_data.get('result', {}).get('title') or podcast_data.get('request', {}).get('topic', 'Untitled')
            print(f"✅ Reassigned: {title[:60]}...")
            updated_count += 1
            
        except Exception as e:
            print(f"❌ Failed to reassign podcast {podcast_id}: {e}")
            failed_count += 1
    
    # Update subscriber counts
    if updated_count > 0:
        from_subscriber_doc = db.collection('subscribers').document(from_subscriber_id).get()
        to_subscriber_doc = db.collection('subscribers').document(to_subscriber_id).get()
        
        if from_subscriber_doc.exists:
            from_data = from_subscriber_doc.to_dict()
            from_count = from_data.get('podcasts_generated', 0)
            db.collection('subscribers').document(from_subscriber_id).update({
                'podcasts_generated': max(from_count - updated_count, 0)
            })
        
        if to_subscriber_doc.exists:
            to_data = to_subscriber_doc.to_dict()
            to_count = to_data.get('podcasts_generated', 0)
            db.collection('subscribers').document(to_subscriber_id).update({
                'podcasts_generated': to_count + updated_count
            })
    
    print(f"\n✅ Reassigned {updated_count} podcast(s)")
    if failed_count > 0:
        print(f"⚠️  Failed to reassign {failed_count} podcast(s)")
    
    return updated_count, failed_count

def main():
    """Main function"""
    print("=" * 80)
    print("PODCAST REASSIGNMENT SCRIPT")
    print("=" * 80)
    
    # Initialize Firestore
    db = firestore.Client(database='copernicusai')
    
    # Find subscribers
    print("\n🔍 Finding subscribers...")
    
    gwelz_email = 'gwelz@jjay.cuny.edu'
    gwelz_subscriber = find_subscriber_by_email(db, gwelz_email)
    
    if not gwelz_subscriber:
        print(f"❌ Subscriber not found: {gwelz_email}")
        sys.exit(1)
    
    gwelz_subscriber_id = gwelz_subscriber.id
    gwelz_data = gwelz_subscriber.to_dict()
    print(f"✅ Found: {gwelz_email}")
    print(f"   Subscriber ID: {gwelz_subscriber_id}")
    print(f"   Current podcasts: {gwelz_data.get('podcasts_generated', 0)}")
    
    # Find john.covington subscriber (need to search by email pattern)
    print("\n🔍 Searching for john.covington subscriber...")
    
    # Try to find by searching all subscribers for "john" or "covington"
    all_subscribers = db.collection('subscribers').stream()
    john_subscriber = None
    john_subscriber_id = None
    
    for sub in all_subscribers:
        data = sub.to_dict()
        email = data.get('email', '').lower()
        if 'john' in email and 'covington' in email:
            john_subscriber = sub
            john_subscriber_id = sub.id
            print(f"✅ Found: {data.get('email')}")
            print(f"   Subscriber ID: {john_subscriber_id}")
            print(f"   Current podcasts: {data.get('podcasts_generated', 0)}")
            break
    
    if not john_subscriber:
        print("⚠️  Could not find john.covington subscriber. Listing all subscribers:")
        print("\nAll subscribers:")
        all_subscribers = db.collection('subscribers').stream()
        for sub in all_subscribers:
            data = sub.to_dict()
            email = data.get('email', 'Unknown')
            count = data.get('podcasts_generated', 0)
            print(f"  - {email}: {count} podcasts (ID: {sub.id[:32]}...)")
        
        print("\n❌ Please manually identify the subscriber ID to move podcasts FROM")
        sys.exit(1)
    
    # List podcasts for john
    print(f"\n📋 Listing podcasts for {john_subscriber.to_dict().get('email')}...")
    john_podcasts = list_podcasts_for_subscriber(db, john_subscriber_id)
    print(f"Found {len(john_podcasts)} podcasts:")
    for i, pod in enumerate(john_podcasts[:10], 1):  # Show first 10
        print(f"  {i}. {pod['title'][:60]}...")
    if len(john_podcasts) > 10:
        print(f"  ... and {len(john_podcasts) - 10} more")
    
    # Confirm
    print(f"\n⚠️  WARNING: This will reassign {len(john_podcasts)} podcasts")
    print(f"   FROM: {john_subscriber.to_dict().get('email')}")
    print(f"   TO:   {gwelz_email}")
    
    response = input("\nProceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        sys.exit(0)
    
    # Reassign
    print("\n🔄 Reassigning podcasts...")
    updated, failed = reassign_podcasts(db, john_subscriber_id, gwelz_subscriber_id)
    
    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)
    print(f"✅ Reassigned: {updated}")
    if failed > 0:
        print(f"⚠️  Failed: {failed}")

if __name__ == '__main__':
    main()

