#!/usr/bin/env python3
"""
Fix podcast titles and delete podcast without audio
"""

import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from datetime import datetime

PREFIX = 'Copernicus AI: Frontiers of Science - '

# Podcasts to fix titles
PODCASTS_TO_FIX = {
    'ever-chem-250017': 'AI-Designed Materials: A Paradigm Shift',
    'ever-phys-250032': 'Quantum Error Correction: The Dawn of Fault-Tolerant Quantum Computing'
}

# Podcast to delete (no audio)
PODCAST_TO_DELETE = 'ever-chem-250021'

def fix_titles():
    """Remove show name prefix from podcast titles"""
    db = firestore.Client(database='copernicusai')
    
    print(f"🔧 Fixing titles for {len(PODCASTS_TO_FIX)} podcasts...\n")
    
    fixed_episodes = 0
    fixed_jobs = 0
    
    for canonical, expected_title in PODCASTS_TO_FIX.items():
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
                print(f"  ✅ Fixed episodes title: {current_title[:60]}...")
                print(f"     → {new_title[:60]}...")
                fixed_episodes += 1
            else:
                print(f"  ⚠️  Title doesn't start with prefix: {current_title[:60]}...")
        else:
            print(f"  ❌ Not found in episodes collection")
        
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
                print(f"  ✅ Fixed podcast_jobs title: {current_title[:60]}...")
                print(f"     → {new_title[:60]}...")
                fixed_jobs += 1
        
        print()
    
    print("=" * 70)
    print(f"✅ Titles fixed: {fixed_episodes} in episodes, {fixed_jobs} in podcast_jobs")
    print("=" * 70)

def delete_podcast_without_audio():
    """Delete podcast that has no audio"""
    db = firestore.Client(database='copernicusai')
    
    print(f"\n🗑️  Deleting podcast {PODCAST_TO_DELETE} (no audio)...\n")
    
    deleted_episodes = 0
    deleted_jobs = 0
    
    # Delete from episodes collection
    ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(PODCAST_TO_DELETE)
    ep_doc = ep_ref.get()
    
    if ep_doc.exists:
        ep_data = ep_doc.to_dict() or {}
        title = ep_data.get('title', 'Unknown')
        print(f"  Found in episodes: {title}")
        ep_ref.delete()
        deleted_episodes = 1
        print(f"  ✅ Deleted from episodes collection")
    else:
        print(f"  ⚠️  Not found in episodes collection")
    
    # Delete from podcast_jobs collection
    jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', PODCAST_TO_DELETE).stream()
    
    for job_doc in jobs_query:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        title = result.get('title', 'Unknown')
        print(f"  Found in podcast_jobs: {title} (job_id: {job_doc.id})")
        job_doc.reference.delete()
        deleted_jobs += 1
        print(f"  ✅ Deleted from podcast_jobs collection")
    
    if not deleted_jobs:
        print(f"  ⚠️  Not found in podcast_jobs collection")
    
    print()
    print("=" * 70)
    print(f"✅ Deletion complete: {deleted_episodes} episode(s), {deleted_jobs} job(s)")
    print("=" * 70)

if __name__ == '__main__':
    fix_titles()
    delete_podcast_without_audio()
    print("\n✅ All tasks complete!")




