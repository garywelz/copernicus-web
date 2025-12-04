#!/usr/bin/env python3
"""Check the actual podcast count for gwelz@jjay.cuny.edu"""

import sys
from google.cloud import firestore
from google.cloud import secretmanager
import hashlib

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def generate_subscriber_id(email: str) -> str:
    """Generate subscriber ID from email"""
    return hashlib.sha256(email.encode()).hexdigest()

def main():
    print("🔍 Checking Podcast Count for gwelz@jjay.cuny.edu")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    email = "gwelz@jjay.cuny.edu"
    subscriber_id = generate_subscriber_id(email)
    
    print(f"\n📧 Subscriber: {email}")
    print(f"   Subscriber ID: {subscriber_id}")
    print()
    
    # Get subscriber document
    subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
    if subscriber_doc.exists:
        subscriber_data = subscriber_doc.to_dict() or {}
        stored_count = subscriber_data.get('podcasts_generated', 0)
        print(f"📊 Stored count in subscriber document: {stored_count}")
    else:
        print(f"⚠️  Subscriber document not found")
    
    # Count from podcast_jobs
    print("\n📊 Counting from podcast_jobs collection...")
    jobs = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
    job_podcasts = []
    job_canonicals = set()
    
    for job_doc in jobs:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        title = result.get('title') or job_data.get('request', {}).get('topic', 'Untitled')
        
        if canonical:
            job_canonicals.add(canonical)
        else:
            job_canonicals.add(job_doc.id)  # Use job_id if no canonical
        
        job_podcasts.append({
            'job_id': job_doc.id,
            'canonical': canonical,
            'title': title
        })
    
    print(f"   Found {len(job_podcasts)} podcast jobs")
    print(f"   Unique canonicals: {len(job_canonicals)}")
    
    # Count from episodes
    print("\n📊 Counting from episodes collection...")
    episodes = db.collection('episodes').where('subscriber_id', '==', subscriber_id).stream()
    episode_podcasts = []
    episode_canonicals = set()
    
    for episode_doc in episodes:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id  # Episode ID is canonical filename
        title = episode_data.get('title', 'Unknown')
        
        episode_canonicals.add(canonical)
        episode_podcasts.append({
            'canonical': canonical,
            'title': title
        })
    
    print(f"   Found {len(episode_podcasts)} episodes")
    print(f"   Unique canonicals: {len(episode_canonicals)}")
    
    # Combine to get unique count
    all_canonicals = job_canonicals.union(episode_canonicals)
    
    print(f"\n📊 Combined unique podcasts: {len(all_canonicals)}")
    
    # List all podcasts
    print(f"\n📋 All Podcasts for {email}:")
    print("-" * 80)
    
    # Create a combined list
    all_podcasts = {}
    
    # Add from jobs
    for job in job_podcasts:
        canonical = job['canonical'] or job['job_id']
        if canonical not in all_podcasts:
            all_podcasts[canonical] = {
                'title': job['title'],
                'canonical': job['canonical'],
                'source': 'job'
            }
    
    # Add from episodes
    for ep in episode_podcasts:
        canonical = ep['canonical']
        if canonical not in all_podcasts:
            all_podcasts[canonical] = {
                'title': ep['title'],
                'canonical': canonical,
                'source': 'episode'
            }
        else:
            all_podcasts[canonical]['source'] = 'both'
    
    # Sort and display
    sorted_podcasts = sorted(all_podcasts.items(), key=lambda x: x[1]['title'])
    
    for i, (canonical, info) in enumerate(sorted_podcasts, 1):
        print(f"{i:3d}. {info['title'][:60]}")
        print(f"     Canonical: {canonical}")
        print(f"     Source: {info['source']}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Stored count: {stored_count if subscriber_doc.exists else 'N/A'}")
    print(f"Actual unique podcasts: {len(all_canonicals)}")
    print(f"Difference: {len(all_canonicals) - (stored_count if subscriber_doc.exists else 0)}")
    
    if len(all_canonicals) != (stored_count if subscriber_doc.exists else 0):
        print(f"\n⚠️  MISMATCH DETECTED!")
        print(f"   Should update stored count to: {len(all_canonicals)}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

