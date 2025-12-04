#!/usr/bin/env python3
"""Check if the 4 missing podcasts have scripts/data needed for audio regeneration"""

import sys
from google.cloud import firestore

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def main():
    print("🔍 Checking Audio Regeneration Data")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # The 4 podcasts needing audio regeneration
    podcasts = [
        "ever-phys-250042",  # Quantum Computing Advances
        "ever-phys-250044",  # Prime Number Theory update
        "ever-phys-250045",  # New materials created using AI
        "ever-phys-250046",  # Matrix Multiplication advances
    ]
    
    print(f"\n📋 Checking {len(podcasts)} podcasts for regeneration data...\n")
    
    results = []
    
    for canonical in podcasts:
        print(f"🔍 Checking: {canonical}")
        print("-" * 80)
        
        # Check episodes collection
        episode_doc = db.collection('episodes').document(canonical).get()
        title = "Unknown"
        has_script = False
        has_request = False
        job_id = None
        
        if episode_doc.exists:
            episode_data = episode_doc.to_dict() or {}
            title = episode_data.get('title', 'Unknown')
            has_script = bool(episode_data.get('script'))
            job_id = episode_data.get('job_id')
            print(f"   Title: {title}")
            print(f"   Has script: {has_script}")
            print(f"   Job ID: {job_id}")
        else:
            print(f"   ⚠️  Not in episodes collection")
        
        # Check podcast_jobs collection
        if job_id:
            job_doc = db.collection('podcast_jobs').document(job_id).get()
            if job_doc.exists:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                request_data = job_data.get('request', {})
                
                job_has_script = bool(result.get('script'))
                job_has_request = bool(request_data)
                
                print(f"   Job exists: ✅")
                print(f"   Job has script: {job_has_script}")
                print(f"   Job has request: {job_has_request}")
                
                if job_has_script:
                    has_script = True
                if job_has_request:
                    has_request = True
            else:
                print(f"   Job not found by ID")
        else:
            # Try searching by canonical
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
            for job_doc in jobs_query:
                job_data = job_doc.to_dict() or {}
                result = job_data.get('result', {})
                request_data = job_data.get('request', {})
                
                print(f"   Found job by canonical: {job_doc.id}")
                print(f"   Job has script: {bool(result.get('script'))}")
                print(f"   Job has request: {bool(request_data)}")
                
                if result.get('script'):
                    has_script = True
                if request_data:
                    has_request = True
                break
        
        # Determine if regeneration is possible
        can_regenerate = has_script or has_request
        
        results.append({
            'canonical': canonical,
            'title': title,
            'can_regenerate': can_regenerate,
            'has_script': has_script,
            'has_request': has_request,
            'job_id': job_id
        })
        
        if can_regenerate:
            print(f"   ✅ Can regenerate audio")
        else:
            print(f"   ❌ Cannot regenerate - missing script and request data")
        
        print()
    
    # Summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    can_regenerate_list = [r for r in results if r['can_regenerate']]
    cannot_regenerate_list = [r for r in results if not r['can_regenerate']]
    
    print(f"✅ Can regenerate: {len(can_regenerate_list)}/{len(podcasts)}")
    print(f"❌ Cannot regenerate: {len(cannot_regenerate_list)}/{len(podcasts)}")
    
    if can_regenerate_list:
        print(f"\n📋 Podcasts that can be regenerated:")
        for item in can_regenerate_list:
            print(f"  - {item['title']} ({item['canonical']})")
            if item['has_script']:
                print(f"    Has script: ✅")
            if item['has_request']:
                print(f"    Has request: ✅")
    
    if cannot_regenerate_list:
        print(f"\n📋 Podcasts that cannot be regenerated (need original data):")
        for item in cannot_regenerate_list:
            print(f"  - {item['title']} ({item['canonical']})")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

