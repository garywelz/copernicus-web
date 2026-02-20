"""
Fix RSS feed entries for YouTube-failed episodes by updating audio URLs
"""

import os
import sys
from google.cloud import firestore
from google.cloud import storage
from services.rss_service import RSSService
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

# Initialize clients
db = firestore.Client(database='copernicusai')
storage_client = storage.Client()
bucket = storage_client.bucket(RSS_BUCKET_NAME)

# Episodes reported by YouTube as failing
YOUTUBE_FAILED_EPISODES = [
    ("Silicon compounds", "ever-chem-250021"),
    ("Quantum Computing chip advances", "ever-phys-250043"),
    ("Matrix Multiplication advances", "ever-phys-250046")
]

def check_audio_file_exists(canonical_filename: str) -> tuple:
    """Check if audio file exists in GCS"""
    possible_paths = [
        f"audio/{canonical_filename}.mp3",
        f"generated/audio/{canonical_filename}.mp3",
        f"audio/{canonical_filename}-audio.mp3",
    ]
    
    for path in possible_paths:
        blob = bucket.blob(path)
        if blob.exists():
            blob.reload()
            return True, f"https://storage.googleapis.com/{RSS_BUCKET_NAME}/{path}", blob.size
    
    return False, None, 0

def find_episode_data(canonical_filename: str):
    """Find episode data from database"""
    # Check episodes collection first
    episode_doc = db.collection('episodes').document(canonical_filename).get()
    if episode_doc.exists:
        data = episode_doc.to_dict()
        return {
            'source': 'episodes',
            'canonical': canonical_filename,
            'title': data.get('title'),
            'audio_url': data.get('audio_url'),
            'thumbnail_url': data.get('thumbnail_url'),
            'description': data.get('description_markdown') or data.get('description_html', ''),
            'subscriber_id': data.get('subscriber_id'),
            'data': data
        }
    
    # Check podcast_jobs collection
    jobs_query = db.collection('podcast_jobs').where(
        'result.canonical_filename', '==', canonical_filename
    ).limit(1).stream()
    
    for job_doc in jobs_query:
        job_data = job_doc.to_dict()
        result = job_data.get('result', {})
        return {
            'source': 'podcast_jobs',
            'job_id': job_doc.id,
            'canonical': canonical_filename,
            'title': result.get('title') or job_data.get('request', {}).get('topic', ''),
            'audio_url': result.get('audio_url'),
            'thumbnail_url': result.get('thumbnail_url'),
            'description': result.get('description', ''),
            'subscriber_id': job_data.get('subscriber_id'),
            'data': job_data
        }
    
    return None

async def main():
    print("=" * 80)
    print("🔧 FIXING YOUTUBE RSS FEED ENTRIES")
    print("=" * 80)
    print()
    
    rss_service = RSSService()
    
    for title, canonical in YOUTUBE_FAILED_EPISODES:
        print(f"\n{'='*80}")
        print(f"📋 Episode: {title} ({canonical})")
        print(f"{'='*80}")
        
        # Find episode data
        episode_data = find_episode_data(canonical)
        
        if not episode_data:
            print(f"❌ Episode not found in database")
            continue
        
        print(f"✅ Found in {episode_data['source']}")
        print(f"   Title: {episode_data['title']}")
        print(f"   Audio URL in DB: {episode_data['audio_url'] or 'MISSING'}")
        
        # Check if audio file exists
        audio_exists, audio_url, audio_size = check_audio_file_exists(canonical)
        
        if audio_exists:
            print(f"✅ Audio file exists in GCS: {audio_url} ({audio_size} bytes)")
            
            # Check if URL matches
            if episode_data['audio_url'] != audio_url:
                print(f"⚠️  Audio URL mismatch - DB has different URL")
                print(f"   Will use GCS URL: {audio_url}")
            
            # Update RSS feed entry
            try:
                # Get subscriber data if available
                subscriber_data = None
                if episode_data.get('subscriber_id'):
                    subscriber_doc = db.collection('subscribers').document(episode_data['subscriber_id']).get()
                    if subscriber_doc.exists:
                        subscriber_data = subscriber_doc.to_dict()
                
                # Prepare podcast data in the format RSS service expects
                podcast_data = {
                    'result': {
                        'canonical_filename': canonical,
                        'title': episode_data['title'],
                        'audio_url': audio_url,
                        'thumbnail_url': episode_data.get('thumbnail_url'),
                        'description': episode_data.get('description', ''),
                    },
                    'request': episode_data['data'].get('request', {}),
                    'subscriber_id': episode_data.get('subscriber_id')
                }
                
                # Update RSS feed
                print(f"🔄 Updating RSS feed entry...")
                await rss_service.update_rss_feed(
                    podcast_data,
                    subscriber_data,
                    True,  # submit_to_rss
                    None   # creator_attribution (can be extracted from subscriber_data if needed)
                )
                print(f"✅ RSS feed updated successfully")
                
            except Exception as e:
                print(f"❌ Failed to update RSS feed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ Audio file NOT found in GCS")
            print(f"   Checked paths:")
            for path in [f"audio/{canonical}.mp3", f"generated/audio/{canonical}.mp3"]:
                print(f"     - {path}")
            print(f"   Action needed: Regenerate audio or remove from RSS feed")
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Verify RSS feed at: https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml")
    print("2. Wait for YouTube to re-fetch the RSS feed (may take a few hours)")
    print("3. Check YouTube dashboard for updated status")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

