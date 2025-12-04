#!/usr/bin/env python3
"""
Script to:
1. Extract actual durations from MP3 files and fix incorrect durations
2. Compare /api/admin/podcasts and /api/admin/podcasts/database endpoints to ensure they match
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from google.cloud import firestore
from google.cloud import storage
from urllib.parse import urlparse
from config.constants import RSS_BUCKET_NAME, EPISODE_COLLECTION_NAME
from datetime import datetime

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️  pydub not available - cannot extract actual durations from MP3 files")

def extract_blob_name_from_url(url: str) -> str:
    """Extract the blob name within the bucket from a public GCS URL."""
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        return None
    if path.startswith(f"{RSS_BUCKET_NAME}/"):
        return path[len(RSS_BUCKET_NAME) + 1:]
    return path

def get_audio_duration(audio_url: str, bucket) -> str:
    """Extract actual duration from MP3 file in GCS"""
    if not audio_url or not PYDUB_AVAILABLE:
        return None
    
    try:
        blob_name = extract_blob_name_from_url(audio_url)
        if not blob_name:
            # Try alternative paths
            canonical = audio_url.split('/')[-1].replace('.mp3', '').split('-audio')[0]
            alt_paths = [
                f"audio/{canonical}.mp3",
                f"generated/audio/{canonical}.mp3",
                f"audio/{canonical}-audio.mp3",
            ]
            for alt_path in alt_paths:
                alt_blob = bucket.blob(alt_path)
                if alt_blob.exists():
                    blob_name = alt_path
                    break
        
        if not blob_name:
            return None
        
        blob = bucket.blob(blob_name)
        if not blob.exists():
            return None
        
        # Download audio file to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Extract duration using pydub
            audio = AudioSegment.from_mp3(temp_path)
            duration_ms = len(audio)
            duration_sec = duration_ms / 1000.0
            
            # Format as MM:SS
            minutes = int(duration_sec // 60)
            seconds = int(duration_sec % 60)
            duration_str = f"{minutes}:{seconds:02d}"
            
            return duration_str
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        print(f"   ⚠️  Error extracting duration: {e}")
        return None

def fix_durations():
    """Find and fix episodes with estimated durations"""
    db = firestore.Client(database='copernicusai')
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    
    print("🔍 Finding episodes with estimated durations...\n")
    
    all_episodes = []
    for ep_doc in db.collection(EPISODE_COLLECTION_NAME).stream():
        ep_data = ep_doc.to_dict() or {}
        canonical = ep_doc.id
        duration = str(ep_data.get('duration', '')) if ep_data.get('duration') else ''
        created_at = ep_data.get('created_at') or ep_data.get('generated_at', '')
        
        all_episodes.append({
            'canonical': canonical,
            'created_at': created_at,
            'duration': duration,
            'title': ep_data.get('title', 'Unknown'),
            'audio_url': ep_data.get('audio_url'),
            'ep_ref': ep_doc.reference
        })
    
    # Sort by created_at descending
    all_episodes.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Find ever-phys-250042
    target_index = None
    for i, ep in enumerate(all_episodes):
        if ep['canonical'] == 'ever-phys-250042':
            target_index = i
            break
    
    if target_index is None:
        print("❌ Could not find ever-phys-250042")
        return
    
    print(f"Found ever-phys-250042 at position {target_index + 1}\n")
    
    # Check episodes after (newer) ever-phys-250042
    episodes_after = all_episodes[:target_index]
    
    issues = []
    for ep in episodes_after:
        duration = ep['duration']
        # Check if it's an estimated duration
        is_estimated = (
            not duration or
            duration == 'Unknown' or
            ('-' in duration and 'minute' in duration.lower()) or
            (duration.lower().endswith('minutes') and ':' not in duration) or
            (duration.lower().endswith('minute') and ':' not in duration) or
            duration.startswith('5-10') or duration.startswith('10-15')
        )
        
        if is_estimated and ep['audio_url']:
            issues.append(ep)
    
    print(f"Found {len(issues)} episodes with estimated durations that have audio:\n")
    
    fixed = 0
    for ep in issues:
        print(f"Processing {ep['canonical']}: {ep['title'][:60]}")
        print(f"  Current duration: {ep['duration']}")
        
        actual_duration = get_audio_duration(ep['audio_url'], bucket)
        if actual_duration:
            print(f"  ✅ Actual duration: {actual_duration}")
            # Update in database
            ep['ep_ref'].update({
                'duration': actual_duration,
                'updated_at': datetime.utcnow().isoformat()
            })
            fixed += 1
        else:
            print(f"  ❌ Could not extract duration")
        print()
    
    print(f"✅ Fixed {fixed}/{len(issues)} durations\n")

def compare_endpoints():
    """Compare what the two endpoints would return"""
    db = firestore.Client(database='copernicusai')
    
    print("📊 Comparing endpoint data structures...\n")
    
    # Simulate /api/admin/podcasts endpoint
    podcasts_list = []
    episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
    for episode_doc in episodes:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id
        
        podcasts_list.append({
            'canonical_filename': canonical,
            'title': episode_data.get('title', 'Untitled'),
            'topic': episode_data.get('topic', ''),
            'category': episode_data.get('category', ''),
            'subscriber_id': episode_data.get('subscriber_id'),
            'submitted_to_rss': episode_data.get('submitted_to_rss', False),
            'created_at': episode_data.get('created_at') or episode_data.get('generated_at'),
            'audio_url': episode_data.get('audio_url'),
            'thumbnail_url': episode_data.get('thumbnail_url')
        })
    
    podcasts_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Simulate /api/admin/podcasts/database endpoint
    database_list = []
    episodes = db.collection(EPISODE_COLLECTION_NAME).stream()
    for episode_doc in episodes:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id
        
        duration = episode_data.get('duration')
        audio_url = episode_data.get('audio_url')
        
        # Check podcast_jobs if needed (simplified for comparison)
        if not duration or duration == 'Unknown' or not audio_url:
            try:
                job_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
                for job_doc in job_query:
                    job_data = job_doc.to_dict() or {}
                    result = job_data.get('result', {})
                    if not duration or duration == 'Unknown':
                        duration = result.get('duration') or job_data.get('request', {}).get('duration') or duration
                    if not audio_url:
                        audio_url = result.get('audio_url') or audio_url
                    break
            except:
                pass
        
        if not duration or duration == 'Unknown':
            request_data = episode_data.get('request', {})
            duration = request_data.get('duration') or 'Unknown'
        
        database_list.append({
            'canonical_filename': canonical,
            'title': episode_data.get('title', 'Untitled'),
            'topic': episode_data.get('topic', ''),
            'category': episode_data.get('category', ''),
            'subscriber_email': 'N/A',  # Simplified
            'duration': duration,
            'file_size_display': 'N/A',  # Simplified
            'created_at': episode_data.get('created_at') or episode_data.get('generated_at'),
            'submitted_to_rss': episode_data.get('submitted_to_rss', False),
        })
    
    database_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    print(f"📊 Comparison Results:")
    print(f"  /api/admin/podcasts: {len(podcasts_list)} podcasts")
    print(f"  /api/admin/podcasts/database: {len(database_list)} podcasts")
    print()
    
    # Compare canonical filenames
    podcasts_canonicals = set(p['canonical_filename'] for p in podcasts_list)
    database_canonicals = set(d['canonical_filename'] for d in database_list)
    
    if podcasts_canonicals == database_canonicals:
        print("✅ Both endpoints return the same podcasts")
    else:
        only_in_podcasts = podcasts_canonicals - database_canonicals
        only_in_database = database_canonicals - podcasts_canonicals
        
        if only_in_podcasts:
            print(f"⚠️  Podcasts only in /podcasts endpoint: {only_in_podcasts}")
        if only_in_database:
            print(f"⚠️  Podcasts only in /podcasts/database endpoint: {only_in_database}")
    
    print()
    print("✅ Endpoint comparison complete\n")

if __name__ == '__main__':
    print("=" * 70)
    print("Fixing Durations and Comparing Endpoints")
    print("=" * 70)
    print()
    
    if PYDUB_AVAILABLE:
        fix_durations()
    else:
        print("⚠️  Skipping duration fixes - pydub not available\n")
    
    compare_endpoints()
    
    print("=" * 70)
    print("✅ Complete!")
    print("=" * 70)

