#!/usr/bin/env python3
"""
Script to fix podcast count discrepancies and create missing episodes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from google.cloud import firestore
from datetime import datetime
from config.constants import EPISODE_COLLECTION_NAME

def create_missing_episodes():
    """Create episodes for podcasts that exist in podcast_jobs but not in episodes"""
    db = firestore.Client(database='copernicusai')
    
    print("🔍 Finding podcasts in podcast_jobs without episodes...")
    
    # Get all podcast_jobs with canonical filenames
    all_jobs = db.collection('podcast_jobs').stream()
    
    missing_episodes = []
    for job_doc in all_jobs:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        
        if not canonical:
            continue
        
        # Check if episode exists
        ep_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
        if not ep_doc.exists:
            missing_episodes.append({
                'canonical': canonical,
                'job_data': job_data,
                'job_id': job_doc.id
            })
    
    print(f"\n📋 Found {len(missing_episodes)} missing episodes:")
    for ep in missing_episodes:
        result = ep['job_data'].get('result', {})
        request = ep['job_data'].get('request', {})
        title = result.get('title') or request.get('topic', 'Unknown')
        status = ep['job_data'].get('status')
        print(f"   - {ep['canonical']}: {title[:60]} (status: {status})")
    
    if missing_episodes:
        print(f"\n❓ Create these {len(missing_episodes)} missing episodes? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            print("\n🔄 Creating missing episodes...")
            created = 0
            for ep in missing_episodes:
                try:
                    canonical = ep['canonical']
                    job_data = ep['job_data']
                    result = job_data.get('result', {})
                    request = job_data.get('request', {})
                    
                    # Create episode document
                    episode_data = {
                        'canonical_filename': canonical,
                        'job_id': ep['job_id'],
                        'subscriber_id': job_data.get('subscriber_id'),
                        'title': result.get('title') or request.get('topic', 'Untitled'),
                        'topic': request.get('topic', ''),
                        'category': request.get('category', ''),
                        'summary': result.get('description', ''),
                        'script': result.get('script', ''),
                        'duration': result.get('duration'),
                        'audio_url': result.get('audio_url'),
                        'thumbnail_url': result.get('thumbnail_url'),
                        'transcript_url': result.get('transcript_url'),
                        'description_url': result.get('description_url'),
                        'submitted_to_rss': job_data.get('submitted_to_rss', False),
                        'created_at': result.get('generated_at') or job_data.get('created_at') or datetime.utcnow().isoformat(),
                        'generated_at': result.get('generated_at') or job_data.get('created_at') or datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat(),
                    }
                    
                    db.collection(EPISODE_COLLECTION_NAME).document(canonical).set(episode_data)
                    created += 1
                    print(f"   ✅ Created: {canonical}")
                except Exception as e:
                    print(f"   ❌ Failed to create {ep['canonical']}: {e}")
            
            print(f"\n✅ Created {created}/{len(missing_episodes)} episodes")
        else:
            print("\n⏭️  Skipped creating episodes")
    else:
        print("\n✅ No missing episodes found!")

if __name__ == '__main__':
    create_missing_episodes()

