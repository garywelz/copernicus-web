"""
Diagnose YouTube ingestion failures for specific episodes
Checks audio file existence, integrity, and validity
"""

import os
import sys
from google.cloud import firestore
from google.cloud import storage
import requests
from urllib.parse import urlparse

# Initialize clients
db = firestore.Client(database='copernicusai')
storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")

# Episodes reported by YouTube as failing
YOUTUBE_FAILED_EPISODES = [
    "Silicon compounds",
    "Quantum Computing chip advances",
    "Matrix Multiplication advances"
]

def extract_blob_name_from_url(url: str) -> str:
    """Extract blob name from GCS URL"""
    if not url:
        return None
    
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    
    # Remove bucket name if present
    bucket_name = "regal-scholar-453620-r7-podcast-storage"
    if path.startswith(f"{bucket_name}/"):
        return path[len(bucket_name) + 1:]
    return path

def check_audio_file_integrity(audio_url: str, canonical_filename: str = None) -> dict:
    """Check if audio file exists and is valid MP3, including encoding details"""
    result = {
        'url': audio_url,
        'exists': False,
        'accessible': False,
        'size': 0,
        'size_mb': 0,
        'valid_mp3': False,
        'bitrate': None,
        'sample_rate': None,
        'duration': None,
        'error': None,
        'blob_path': None,
        'youtube_compatible': False
    }
    
    if not audio_url:
        result['error'] = 'No audio URL provided'
        return result
    
    try:
        # Extract blob name
        blob_name = extract_blob_name_from_url(audio_url)
        
        # Try alternative paths if canonical filename provided
        if not blob_name and canonical_filename:
            alt_paths = [
                f"audio/{canonical_filename}.mp3",
                f"generated/audio/{canonical_filename}.mp3",
                f"audio/{canonical_filename}-audio.mp3",
            ]
            for alt_path in alt_paths:
                alt_blob = bucket.blob(alt_path)
                if alt_blob.exists():
                    blob_name = alt_path
                    break
        
        if not blob_name:
            result['error'] = 'Could not determine blob path'
            return result
        
        result['blob_path'] = blob_name
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            result['error'] = f'Blob does not exist: {blob_name}'
            return result
        
        result['exists'] = True
        
        # Get blob metadata
        blob.reload()
        result['size'] = blob.size
        result['size_mb'] = round(blob.size / (1024 * 1024), 2)
        
        # Check if size is reasonable (> 100KB for a podcast)
        if blob.size < 100 * 1024:
            result['error'] = f'File too small: {blob.size} bytes (expected > 100KB)'
            return result
        
        # Download first few bytes to check MP3 header
        try:
            chunk = blob.download_as_bytes(start=0, end=min(4096, blob.size - 1))
            
            if len(chunk) == 0:
                result['error'] = 'File appears to be empty'
                return result
            
            # Check for MP3 header
            # MP3 files can start with:
            # - ID3 tag: b'ID3'
            # - MPEG frame sync: 0xFF followed by 0xFB, 0xF3, 0xFA, or 0xF2
            is_mp3 = False
            if chunk[:3] == b'ID3':
                is_mp3 = True
            elif len(chunk) >= 2 and chunk[0] == 0xFF:
                if chunk[1] in [0xFB, 0xF3, 0xFA, 0xF2, 0xE3, 0xE2]:
                    is_mp3 = True
            
            # Also check for "MP3" string in first 100 bytes (some metadata)
            if not is_mp3 and b'MP3' in chunk[:100]:
                is_mp3 = True
            
            result['valid_mp3'] = is_mp3
            result['accessible'] = True
            
            if not is_mp3:
                result['error'] = f'Invalid MP3 header. First bytes: {chunk[:16].hex()}'
            else:
                # Try to get encoding details using ffprobe if available
                try:
                    import subprocess
                    import json
                    import tempfile
                    
                    # Download file to temp location for ffprobe
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                        blob.download_to_filename(temp_file.name)
                        temp_path = temp_file.name
                    
                    try:
                        # Use ffprobe to get detailed audio info
                        ffprobe_cmd = [
                            'ffprobe', '-v', 'quiet', '-print_format', 'json',
                            '-show_format', '-show_streams', temp_path
                        ]
                        probe_result = subprocess.run(
                            ffprobe_cmd,
                            capture_output=True,
                            timeout=10,
                            text=True
                        )
                        
                        if probe_result.returncode == 0:
                            probe_data = json.loads(probe_result.stdout)
                            
                            # Extract audio stream info
                            audio_stream = None
                            for stream in probe_data.get('streams', []):
                                if stream.get('codec_type') == 'audio':
                                    audio_stream = stream
                                    break
                            
                            if audio_stream:
                                result['bitrate'] = int(audio_stream.get('bit_rate', 0)) // 1000  # Convert to kbps
                                result['sample_rate'] = int(audio_stream.get('sample_rate', 0))
                                
                                # Get duration from format
                                format_info = probe_data.get('format', {})
                                duration = float(format_info.get('duration', 0))
                                if duration > 0:
                                    result['duration'] = f"{int(duration // 60)}:{int(duration % 60):02d}"
                                
                                # Check YouTube compatibility
                                # YouTube requires: bitrate >= 64kbps, sample rate typically 44.1kHz or 48kHz
                                bitrate_ok = result['bitrate'] >= 64
                                sample_rate_ok = result['sample_rate'] in [44100, 48000, 22050, 24000]
                                result['youtube_compatible'] = bitrate_ok and sample_rate_ok
                                
                                if not result['youtube_compatible']:
                                    issues = []
                                    if not bitrate_ok:
                                        issues.append(f"bitrate too low ({result['bitrate']} kbps, need >= 64)")
                                    if not sample_rate_ok:
                                        issues.append(f"sample rate {result['sample_rate']} Hz (prefer 44.1kHz or 48kHz)")
                                    result['error'] = f"YouTube compatibility issues: {', '.join(issues)}"
                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
                    # ffprobe not available or failed - that's okay, we still have basic validation
                    pass
            
        except Exception as e:
            result['error'] = f'Error checking file integrity: {str(e)}'
            return result
        
    except Exception as e:
        result['error'] = f'Error accessing file: {str(e)}'
        return result
    
    return result

def find_episodes_by_title(title: str):
    """Find episodes by partial title match"""
    episodes = []
    
    # Search in episodes collection
    episodes_ref = db.collection('episodes')
    for doc in episodes_ref.stream():
        data = doc.to_dict() or {}
        episode_title = data.get('title', '')
        if title.lower() in episode_title.lower() or episode_title.lower() in title.lower():
            episodes.append({
                'collection': 'episodes',
                'doc_id': doc.id,
                'canonical': data.get('canonical_filename', doc.id),
                'title': episode_title,
                'audio_url': data.get('audio_url'),
                'created_at': data.get('created_at', 'Unknown')
            })
    
    # Search in podcast_jobs collection
    jobs_ref = db.collection('podcast_jobs')
    for doc in jobs_ref.stream():
        data = doc.to_dict() or {}
        result = data.get('result', {})
        job_title = result.get('title', '') if result else ''
        request = data.get('request', {})
        topic = request.get('topic', '') if request else ''
        
        title_match = title.lower() in job_title.lower() if job_title else False
        topic_match = title.lower() in topic.lower() if topic else False
        
        if title_match or topic_match:
            episodes.append({
                'collection': 'podcast_jobs',
                'doc_id': doc.id,
                'canonical': result.get('canonical_filename', doc.id) if result else doc.id,
                'title': job_title or topic,
                'audio_url': result.get('audio_url') if result else None,
                'created_at': data.get('created_at', 'Unknown'),
                'status': data.get('status', 'Unknown')
            })
    
    return episodes

def main():
    print("=" * 80)
    print("🔍 YOUTUBE ERROR DIAGNOSIS")
    print("=" * 80)
    print()
    
    all_results = []
    
    for episode_title in YOUTUBE_FAILED_EPISODES:
        print(f"\n{'='*80}")
        print(f"📋 Episode: {episode_title}")
        print(f"{'='*80}")
        
        # Find episodes matching this title
        episodes = find_episodes_by_title(episode_title)
        
        if not episodes:
            print(f"❌ No episodes found matching '{episode_title}'")
            all_results.append({
                'title': episode_title,
                'found': False,
                'episodes': []
            })
            continue
        
        print(f"✅ Found {len(episodes)} matching episode(s):")
        for i, ep in enumerate(episodes, 1):
            print(f"\n  Episode {i}:")
            print(f"    Collection: {ep['collection']}")
            print(f"    Document ID: {ep['doc_id']}")
            print(f"    Canonical: {ep['canonical']}")
            print(f"    Title: {ep['title']}")
            print(f"    Audio URL: {ep['audio_url'] or 'MISSING'}")
            print(f"    Created: {ep['created_at']}")
            if 'status' in ep:
                print(f"    Status: {ep['status']}")
            
            # Check audio file
            if ep['audio_url']:
                print(f"\n    🔍 Checking audio file...")
                audio_check = check_audio_file_integrity(ep['audio_url'], ep['canonical'])
                
                print(f"      Exists: {audio_check['exists']}")
                print(f"      Size: {audio_check['size_mb']} MB ({audio_check['size']} bytes)")
                print(f"      Valid MP3: {audio_check['valid_mp3']}")
                if audio_check.get('bitrate'):
                    print(f"      Bitrate: {audio_check['bitrate']} kbps")
                if audio_check.get('sample_rate'):
                    print(f"      Sample Rate: {audio_check['sample_rate']} Hz")
                if audio_check.get('duration'):
                    print(f"      Duration: {audio_check['duration']}")
                print(f"      YouTube Compatible: {audio_check.get('youtube_compatible', 'Unknown')}")
                print(f"      Blob Path: {audio_check['blob_path']}")
                
                if audio_check['error']:
                    print(f"      ⚠️  Error: {audio_check['error']}")
                
                ep['audio_check'] = audio_check
            else:
                print(f"    ❌ No audio URL in database")
                ep['audio_check'] = {'exists': False, 'error': 'No audio URL'}
        
        all_results.append({
            'title': episode_title,
            'found': True,
            'episodes': episodes
        })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    total_found = sum(1 for r in all_results if r['found'])
    total_episodes = sum(len(r['episodes']) for r in all_results)
    
    print(f"\nEpisodes searched: {len(YOUTUBE_FAILED_EPISODES)}")
    print(f"Episodes found: {total_found}")
    print(f"Total matching records: {total_episodes}")
    
    # Count issues
    missing_audio = 0
    corrupt_audio = 0
    valid_audio = 0
    
    for result in all_results:
        for ep in result['episodes']:
            if 'audio_check' in ep:
                check = ep['audio_check']
                if not check.get('exists'):
                    missing_audio += 1
                elif not check.get('valid_mp3'):
                    corrupt_audio += 1
                elif check.get('valid_mp3'):
                    valid_audio += 1
    
    print(f"\nAudio Status:")
    print(f"  ✅ Valid MP3: {valid_audio}")
    print(f"  ❌ Missing: {missing_audio}")
    print(f"  ⚠️  Corrupt/Invalid: {corrupt_audio}")
    
    if missing_audio > 0 or corrupt_audio > 0:
        print(f"\n⚠️  ACTION REQUIRED:")
        print(f"   {missing_audio} episodes need audio regeneration")
        print(f"   {corrupt_audio} episodes have corrupt audio files")
    
    return all_results

if __name__ == "__main__":
    results = main()

