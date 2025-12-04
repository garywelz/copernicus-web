#!/usr/bin/env python3
"""
Script to find incomplete podcasts (missing audio URLs or audio files)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from google.cloud import firestore
from google.cloud import storage
from config.constants import RSS_BUCKET_NAME
from urllib.parse import urlparse

def get_incomplete_podcasts():
    """Find all podcasts that are missing audio URLs or audio files"""
    db = firestore.Client(database='copernicusai')
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    
    incomplete = []
    episodes_without_audio_url = []
    episodes_with_missing_audio = []
    
    print("🔍 Scanning episodes collection...")
    episodes = db.collection('episodes').stream()
    
    for episode_doc in episodes:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id
        audio_url = episode_data.get('audio_url')
        title = episode_data.get('title', 'Untitled')
        subscriber_id = episode_data.get('subscriber_id', 'Unknown')
        
        # Check if audio URL is missing
        if not audio_url:
            episodes_without_audio_url.append({
                'canonical': canonical,
                'title': title,
                'subscriber_id': subscriber_id,
                'created_at': episode_data.get('created_at', 'Unknown')
            })
            continue
        
        # Check if audio file exists in GCS
        try:
            parsed = urlparse(audio_url)
            path = parsed.path.lstrip("/")
            
            # Extract blob name
            if path.startswith(f"{RSS_BUCKET_NAME}/"):
                blob_name = path[len(RSS_BUCKET_NAME) + 1:]
            else:
                blob_name = path
            
            blob = bucket.blob(blob_name)
            
            if not blob.exists():
                # Try alternative paths
                alt_paths = [
                    f"audio/{canonical}.mp3",
                    f"generated/audio/{canonical}.mp3",
                    f"audio/{canonical}-audio.mp3",
                    f"generated/audio/{canonical}-audio.mp3"
                ]
                found = False
                for alt_path in alt_paths:
                    alt_blob = bucket.blob(alt_path)
                    if alt_blob.exists():
                        found = True
                        break
                
                if not found:
                    episodes_with_missing_audio.append({
                        'canonical': canonical,
                        'title': title,
                        'subscriber_id': subscriber_id,
                        'audio_url': audio_url,
                        'created_at': episode_data.get('created_at', 'Unknown')
                    })
        except Exception as e:
            episodes_with_missing_audio.append({
                'canonical': canonical,
                'title': title,
                'subscriber_id': subscriber_id,
                'audio_url': audio_url,
                'error': str(e),
                'created_at': episode_data.get('created_at', 'Unknown')
            })
    
    print(f"\n📊 Results:")
    print(f"   Episodes without audio URL: {len(episodes_without_audio_url)}")
    print(f"   Episodes with missing audio file: {len(episodes_with_missing_audio)}")
    
    if episodes_without_audio_url:
        print(f"\n❌ Episodes without audio URL ({len(episodes_without_audio_url)}):")
        for ep in episodes_without_audio_url:
            print(f"   - {ep['canonical']}: {ep['title'][:60]}")
    
    if episodes_with_missing_audio:
        print(f"\n❌ Episodes with missing audio file ({len(episodes_with_missing_audio)}):")
        for ep in episodes_with_missing_audio:
            print(f"   - {ep['canonical']}: {ep['title'][:60]}")
    
    return {
        'without_audio_url': episodes_without_audio_url,
        'missing_audio_file': episodes_with_missing_audio
    }

if __name__ == '__main__':
    incomplete = get_incomplete_podcasts()
    print(f"\n✅ Scan complete!")
    print(f"   Total incomplete: {len(incomplete['without_audio_url']) + len(incomplete['missing_audio_file'])}")

