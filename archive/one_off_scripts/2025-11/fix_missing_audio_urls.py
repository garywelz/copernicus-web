#!/usr/bin/env python3
"""Fix missing audio URLs in database for podcasts that have audio files"""

import sys
from google.cloud import storage
from google.cloud import firestore
from datetime import datetime

GCP_PROJECT_ID = "regal-scholar-453620-r7"
BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"

def check_audio_in_gcs(canonical_filename):
    """Check if audio file exists in GCS and return URL"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    
    # Try different possible paths
    possible_paths = [
        f"audio/{canonical_filename}.mp3",
        f"audio/{canonical_filename}-audio.mp3",
        f"podcasts/{canonical_filename}.mp3",
        f"podcasts/{canonical_filename}-audio.mp3",
    ]
    
    for path in possible_paths:
        blob = bucket.blob(path)
        if blob.exists():
            return blob.public_url
    
    return None

def main():
    print("🔧 Fixing Missing Audio URLs")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # Podcast with audio but missing URL
    canonical = "ever-phys-250043"
    
    print(f"\n🔍 Processing: {canonical}")
    print("-" * 80)
    
    # Check if audio exists in GCS
    audio_url = check_audio_in_gcs(canonical)
    
    if not audio_url:
        print(f"❌ Audio file not found in GCS")
        return
    
    print(f"✅ Found audio in GCS: {audio_url}")
    
    # Get episode document
    episode_ref = db.collection('episodes').document(canonical)
    episode_doc = episode_ref.get()
    
    if not episode_doc.exists:
        print(f"❌ Episode document not found")
        return
    
    episode_data = episode_doc.to_dict() or {}
    title = episode_data.get('title', 'Unknown')
    
    print(f"   Title: {title}")
    print(f"   Current audio_url: {episode_data.get('audio_url', 'Missing')}")
    
    # Update audio URL
    try:
        episode_ref.update({
            'audio_url': audio_url,
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"✅ Updated audio URL in database")
        print(f"   New URL: {audio_url}")
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        return
    
    # Also update podcast_jobs if it exists
    try:
        jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
        for job_doc in jobs_query:
            job_doc.reference.update({
                'result.audio_url': audio_url,
                'updated_at': datetime.utcnow().isoformat()
            })
            print(f"✅ Updated audio URL in podcast_jobs: {job_doc.id}")
            break
    except Exception as e:
        print(f"⚠️  Could not update podcast_jobs: {e}")
    
    print("\n" + "="*80)
    print("✅ Done!")
    print("="*80)

if __name__ == "__main__":
    main()

