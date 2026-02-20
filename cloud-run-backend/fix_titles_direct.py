#!/usr/bin/env python3
"""
Direct script to fix podcast titles without using API endpoints
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from datetime import datetime
from utils.subscriber_helpers import get_subscriber_by_email

PREFIX = 'Copernicus AI: Frontiers of Science - '

def fix_missing_titles_for_subscriber(email):
    """Fix missing titles for a subscriber"""
    db = firestore.Client(database='copernicusai')
    
    # Get subscriber
    subscriber_doc = get_subscriber_by_email(email)
    if not subscriber_doc:
        print(f"❌ Subscriber not found: {email}")
        return
    
    subscriber_id = subscriber_doc.id
    print(f"✅ Found subscriber: {email} (ID: {subscriber_id})")
    print(f"\n🔧 Fixing missing titles...\n")
    
    fixed_count = 0
    skipped_count = 0
    errors = []
    
    # Get all episodes for this subscriber
    episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
    
    for episode_doc in episodes_query:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id
        current_title = episode_data.get('title', '')
        
        # Check if title needs fixing
        needs_fix = (
            not current_title or 
            current_title == 'Untitled' or 
            current_title == 'Untitled Episode' or
            not current_title.strip()
        )
        
        if not needs_fix:
            skipped_count += 1
            continue
        
        # Try to find title from podcast_jobs
        title_found = None
        jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
        
        for job_doc in jobs_query:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            request_data = job_data.get('request', {})
            
            # Try multiple sources for title
            title_found = (
                result.get('title') or
                request_data.get('topic') or
                episode_data.get('topic') or
                None
            )
            break
        
        # If still no title, try episode_data.topic
        if not title_found:
            title_found = episode_data.get('topic')
        
        if title_found and title_found != 'Untitled' and title_found.strip():
            # Update the episode with the found title
            try:
                episode_doc.reference.update({
                    'title': title_found,
                    'updated_at': datetime.utcnow().isoformat()
                })
                fixed_count += 1
                print(f"  ✅ {canonical}: '{current_title or '(missing)'}' → '{title_found[:60]}...'")
            except Exception as e:
                errors.append(f"Failed to update {canonical}: {str(e)}")
                print(f"  ❌ {canonical}: Error - {e}")
        else:
            skipped_count += 1
            print(f"  ⚠️  {canonical}: No title found")
    
    print(f"\n{'='*70}")
    print(f"✅ Complete! Fixed: {fixed_count}, Skipped: {skipped_count}, Errors: {len(errors)}")
    print(f"{'='*70}")

def fix_title_prefixes():
    """Remove 'Copernicus AI: Frontiers of Science - ' prefix from specific podcasts"""
    db = firestore.Client(database='copernicusai')
    
    podcasts_to_fix = ['ever-chem-250017', 'ever-phys-250032']
    
    print(f"\n🔧 Fixing title prefixes...\n")
    
    fixed_episodes = 0
    fixed_jobs = 0
    
    for canonical in podcasts_to_fix:
        print(f"Processing {canonical}...")
        
        # Fix episodes collection
        ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(canonical)
        ep_doc = ep_ref.get()
        
        if ep_doc.exists:
            ep_data = ep_doc.to_dict() or {}
            current_title = ep_data.get('title', '')
            
            if current_title.startswith(PREFIX):
                new_title = current_title.replace(PREFIX, '', 1)
                ep_ref.update({
                    'title': new_title,
                    'updated_at': datetime.utcnow().isoformat()
                })
                print(f"  ✅ Fixed episodes: '{current_title[:50]}...' → '{new_title[:50]}...'")
                fixed_episodes += 1
        
        # Fix podcast_jobs collection
        jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream()
        for job_doc in jobs_query:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            current_title = result.get('title', '')
            
            if current_title.startswith(PREFIX):
                new_title = current_title.replace(PREFIX, '', 1)
                result['title'] = new_title
                job_doc.reference.update({
                    'result': result,
                    'updated_at': datetime.utcnow().isoformat()
                })
                print(f"  ✅ Fixed podcast_jobs: '{current_title[:50]}...' → '{new_title[:50]}...'")
                fixed_jobs += 1
        
        print()
    
    print(f"{'='*70}")
    print(f"✅ Title prefixes fixed: {fixed_episodes} episodes, {fixed_jobs} jobs")
    print(f"{'='*70}")

def delete_podcast_without_audio():
    """Delete podcast that has no audio"""
    db = firestore.Client(database='copernicusai')
    
    canonical_to_delete = 'ever-chem-250021'
    
    print(f"\n🗑️  Deleting {canonical_to_delete} (no audio)...\n")
    
    deleted_episodes = 0
    deleted_jobs = 0
    
    # Delete from episodes
    ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(canonical_to_delete)
    ep_doc = ep_ref.get()
    if ep_doc.exists:
        ep_data = ep_doc.to_dict() or {}
        title = ep_data.get('title', 'Unknown')
        ep_ref.delete()
        print(f"  ✅ Deleted from episodes: {title}")
        deleted_episodes = 1
    
    # Delete from podcast_jobs
    jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical_to_delete).stream()
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        title = result.get('title', 'Unknown')
        job_doc.reference.delete()
        print(f"  ✅ Deleted from podcast_jobs: {title} (job_id: {job_doc.id})")
        deleted_jobs += 1
    
    print(f"\n{'='*70}")
    print(f"✅ Deletion complete: {deleted_episodes} episode(s), {deleted_jobs} job(s)")
    print(f"{'='*70}")

def main():
    email = "gwelz@jjay.cuny.edu"
    
    print(f"{'='*70}")
    print(f"🔧 Fixing Podcast Titles and Deleting Invalid Podcast")
    print(f"{'='*70}\n")
    
    # Step 1: Fix missing titles for subscriber
    fix_missing_titles_for_subscriber(email)
    
    # Step 2: Fix title prefixes
    fix_title_prefixes()
    
    # Step 3: Delete podcast without audio
    delete_podcast_without_audio()
    
    print(f"\n{'='*70}")
    print(f"✅ All tasks complete!")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()




