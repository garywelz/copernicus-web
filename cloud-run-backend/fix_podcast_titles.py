#!/usr/bin/env python3
"""
Fix podcast titles by removing "Copernicus AI: Frontiers of Science - " prefix
"""

import sys
import os

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

print("Starting title fix script...", flush=True)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from datetime import datetime

print("Imports successful", flush=True)

# Podcasts to fix
PODCASTS_TO_FIX = {
    'ever-chem-250017': 'AI-Designed Materials: A Paradigm Shift',
    'ever-phys-250032': 'Quantum Error Correction: The Dawn of Fault-Tolerant Quantum Computing'
}

PREFIX = 'Copernicus AI: Frontiers of Science - '

def fix_titles():
    """Remove show name prefix from podcast titles"""
    db = firestore.Client(database='copernicusai')
    
    print(f"🔧 Fixing titles for {len(PODCASTS_TO_FIX)} podcasts...\n")
    
    fixed_episodes = 0
    fixed_jobs = 0
    missing = []
    
    for canonical, expected_title in PODCASTS_TO_FIX.items():
        print(f"Processing {canonical}...")
        
        # Check and fix episodes collection
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
                print(f"  ✅ Fixed episodes title: {current_title[:50]}... → {new_title[:50]}...")
                fixed_episodes += 1
            else:
                print(f"  ⚠️  Episodes title doesn't have prefix: {current_title[:50]}...")
        else:
            print(f"  ⚠️  Not found in episodes collection")
            missing.append(f"{canonical} (episodes)")
        
        # Check and fix podcast_jobs collection
        jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream()
        job_found = False
        
        for job_doc in jobs_query:
            job_found = True
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
                print(f"  ✅ Fixed podcast_jobs title: {current_title[:50]}... → {new_title[:50]}...")
                fixed_jobs += 1
            else:
                print(f"  ⚠️  podcast_jobs title doesn't have prefix: {current_title[:50]}...")
        
        if not job_found:
            print(f"  ⚠️  Not found in podcast_jobs collection")
            missing.append(f"{canonical} (podcast_jobs)")
        
        print()
    
    print("=" * 70)
    print(f"✅ Complete!")
    print(f"   Fixed in episodes: {fixed_episodes}")
    print(f"   Fixed in podcast_jobs: {fixed_jobs}")
    if missing:
        print(f"   Missing from: {', '.join(missing)}")
    print("=" * 70)
    
    # Check if ever-phys-250032 is only in one collection
    print("\n🔍 Checking ever-phys-250032 location...")
    canonical = 'ever-phys-250032'
    
    ep_doc = db.collection(EPISODE_COLLECTION_NAME).document(canonical).get()
    jobs_query = list(db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream())
    
    in_episodes = ep_doc.exists
    in_jobs = len(jobs_query) > 0
    
    print(f"  In episodes collection: {in_episodes}")
    print(f"  In podcast_jobs collection: {in_jobs}")
    
    if in_episodes and not in_jobs:
        print(f"\n  ✅ This explains the count discrepancy!")
        print(f"     This podcast is in episodes but not in podcast_jobs")
    elif in_jobs and not in_episodes:
        print(f"\n  ✅ This explains the count discrepancy!")
        print(f"     This podcast is in podcast_jobs but not in episodes")
    else:
        print(f"\n  ⚠️  Found in both collections (or neither)")

if __name__ == '__main__':
    fix_titles()

