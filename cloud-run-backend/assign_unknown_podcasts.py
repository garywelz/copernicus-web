#!/usr/bin/env python3
"""Assign unknown podcasts to gwelz@jjay.cuny.edu"""

import sys
import os
from google.cloud import firestore
from datetime import datetime
import hashlib

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import db
from utils.logging import structured_logger

def generate_subscriber_id(email: str) -> str:
    """Generate subscriber ID from email (SHA-256 hash)"""
    return hashlib.sha256(email.encode()).hexdigest()

def assign_podcasts_to_subscriber(canonical_filenames: list, email: str):
    """Assign podcasts to a subscriber"""
    if not db:
        print("❌ Firestore database not available")
        return
    
    # Find subscriber
    subscriber_id = generate_subscriber_id(email)
    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
    
    if not subscriber_doc.exists:
        print(f"❌ Subscriber not found: {email}")
        print(f"   Subscriber ID: {subscriber_id}")
        return
    
    subscriber_data = subscriber_doc.to_dict()
    print(f"✅ Found subscriber: {email}")
    print(f"   Subscriber ID: {subscriber_id}")
    
    assigned_count = 0
    failed_count = 0
    
    for canonical in canonical_filenames:
        try:
            # Update episodes collection
            episode_ref = db.collection('episodes').document(canonical)
            episode_doc = episode_ref.get()
            
            if episode_doc.exists:
                episode_ref.update({
                    'subscriber_id': subscriber_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
                episode_data = episode_doc.to_dict()
                title = episode_data.get('title', canonical)
                print(f"✅ Updated episode: {canonical} - {title}")
            else:
                print(f"⚠️  Episode not found: {canonical}")
            
            # Find and update podcast_jobs by canonical filename
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream()
            job_found = False
            for job_doc in jobs_query:
                job_doc.reference.update({
                    'subscriber_id': subscriber_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
                job_data = job_doc.to_dict()
                title = job_data.get('result', {}).get('title') or job_data.get('request', {}).get('topic', canonical)
                print(f"✅ Updated podcast_job: {job_doc.id} - {title}")
                job_found = True
                break
            
            if not job_found:
                print(f"⚠️  Podcast job not found for canonical: {canonical}")
            
            if episode_doc.exists or job_found:
                assigned_count += 1
            else:
                failed_count += 1
                
        except Exception as e:
            print(f"❌ Failed to assign {canonical}: {e}")
            failed_count += 1
    
    print(f"\n✅ Assignment complete:")
    print(f"   Assigned: {assigned_count}")
    print(f"   Failed: {failed_count}")

def main():
    # Podcasts to assign
    podcasts = [
        'ever-phys-250043',
        'ever-phys-250046',
        'ever-phys-250045',
        'ci-250030',
        'ever-phys-250044'
    ]
    
    email = 'gwelz@jjay.cuny.edu'
    
    print(f"🎯 Assigning {len(podcasts)} podcasts to {email}...")
    print(f"   Podcasts: {', '.join(podcasts)}")
    print()
    
    assign_podcasts_to_subscriber(podcasts, email)

if __name__ == '__main__':
    main()

