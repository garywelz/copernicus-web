#!/usr/bin/env python3
"""
Script to delete incomplete podcasts (missing audio URLs)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME

def delete_incomplete_podcasts():
    """Delete podcasts that are missing audio URLs"""
    db = firestore.Client(database='copernicusai')
    
    incomplete_canonicals = [
        'ever-phys-250044',  # Prime Number Theory update
        'ever-phys-250045',  # New materials created using AI
        'ever-phys-250046'   # Matrix Multiplication advances
    ]
    
    print("🗑️  Deleting incomplete podcasts (missing audio URLs)...\n")
    
    deleted_episodes = 0
    deleted_jobs = 0
    
    for canonical in incomplete_canonicals:
        print(f"Processing {canonical}...")
        
        # Delete from episodes collection
        try:
            ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(canonical)
            ep_doc = ep_ref.get()
            if ep_doc.exists:
                ep_ref.delete()
                deleted_episodes += 1
                print(f"  ✅ Deleted from episodes collection")
            else:
                print(f"  ⚠️  Not found in episodes collection")
        except Exception as e:
            print(f"  ❌ Error deleting from episodes: {e}")
        
        # Delete from podcast_jobs collection
        try:
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream()
            for job_doc in jobs_query:
                job_doc.reference.delete()
                deleted_jobs += 1
                print(f"  ✅ Deleted from podcast_jobs collection (job_id: {job_doc.id})")
        except Exception as e:
            print(f"  ❌ Error deleting from podcast_jobs: {e}")
        
        print()
    
    print(f"✅ Deletion complete!")
    print(f"   Deleted {deleted_episodes} episodes")
    print(f"   Deleted {deleted_jobs} podcast jobs")

if __name__ == '__main__':
    delete_incomplete_podcasts()

