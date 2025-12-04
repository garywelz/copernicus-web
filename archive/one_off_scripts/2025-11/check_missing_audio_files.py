#!/usr/bin/env python3
"""Check if audio files exist in GCS for the 4 missing podcasts"""

import sys
from google.cloud import storage
from google.cloud import firestore
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"
BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def check_audio_in_gcs(canonical_filename):
    """Check if audio file exists in GCS for a canonical filename"""
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
            blob.reload()
            return {
                'exists': True,
                'path': path,
                'size': blob.size,
                'size_mb': round(blob.size / (1024 * 1024), 2),
                'url': blob.public_url
            }
    
    return {'exists': False, 'paths_checked': possible_paths}

def main():
    print("🔍 Checking Missing Audio Files")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # The 5 podcasts with missing audio
    podcasts_to_check = [
        "ever-phys-250042",  # Quantum Computing Advances (failed job)
        "ever-phys-250043",  # Quantum Computing chip advances
        "ever-phys-250044",  # Prime Number Theory update
        "ever-phys-250045",  # New materials created using AI
        "ever-phys-250046",  # Matrix Multiplication advances
    ]
    
    print(f"\n📋 Checking {len(podcasts_to_check)} podcasts for audio files...\n")
    
    results = []
    
    for canonical in podcasts_to_check:
        print(f"🔍 Checking: {canonical}")
        print("-" * 80)
        
        # Get episode data
        episode_doc = db.collection('episodes').document(canonical).get()
        title = "Unknown"
        audio_url = None
        
        if episode_doc.exists:
            episode_data = episode_doc.to_dict() or {}
            title = episode_data.get('title', 'Unknown')
            audio_url = episode_data.get('audio_url')
        
        print(f"   Title: {title}")
        print(f"   Current audio_url: {audio_url or 'Missing'}")
        
        # Check GCS
        gcs_result = check_audio_in_gcs(canonical)
        
        if gcs_result['exists']:
            print(f"   ✅ Audio found in GCS:")
            print(f"      Path: {gcs_result['path']}")
            print(f"      Size: {gcs_result['size_mb']} MB")
            print(f"      URL: {gcs_result['url']}")
            
            # If audio_url is missing, we should update it
            if not audio_url:
                print(f"   ⚠️  Audio URL missing in database - should update!")
                results.append({
                    'canonical': canonical,
                    'title': title,
                    'action': 'update_url',
                    'audio_url': gcs_result['url']
                })
            else:
                print(f"   ✅ Audio URL already set in database")
        else:
            print(f"   ❌ Audio NOT found in GCS")
            print(f"      Checked paths: {', '.join(gcs_result['paths_checked'])}")
            results.append({
                'canonical': canonical,
                'title': title,
                'action': 'regenerate',
                'audio_url': None
            })
        
        print()
    
    # Summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    update_needed = [r for r in results if r['action'] == 'update_url']
    regenerate_needed = [r for r in results if r['action'] == 'regenerate']
    
    print(f"Total checked: {len(podcasts_to_check)}")
    print(f"✅ Audio exists, need URL update: {len(update_needed)}")
    print(f"❌ Audio missing, need regeneration: {len(regenerate_needed)}")
    
    if update_needed:
        print(f"\n📋 Podcasts needing URL update ({len(update_needed)}):")
        for item in update_needed:
            print(f"  - {item['title']} ({item['canonical']})")
            print(f"    URL: {item['audio_url']}")
    
    if regenerate_needed:
        print(f"\n📋 Podcasts needing audio regeneration ({len(regenerate_needed)}):")
        for item in regenerate_needed:
            print(f"  - {item['title']} ({item['canonical']})")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

