"""
Remove specific episodes from RSS feed
"""

import asyncio
from google.cloud import firestore
from services.rss_service import RSSService
from config.database import db

EPISODES_TO_REMOVE = [
    'ever-phys-250038',  # Quantum Error Correction: Paving the Way...
    'ever-phys-250042'   # Quantum Sensing Revolution: Unveiling Hidden Realities...
]

async def remove_episodes_from_rss():
    """Remove episodes from RSS feed"""
    rss_service = RSSService()
    
    print("=" * 80)
    print("🗑️  REMOVING EPISODES FROM RSS FEED")
    print("=" * 80)
    print()
    
    for canonical in EPISODES_TO_REMOVE:
        print(f"Removing {canonical}...")
        
        # Get episode data from database
        episode_doc = db.collection('episodes').document(canonical).get()
        
        if not episode_doc.exists:
            print(f"  ⚠️  Episode not found in episodes collection, checking podcast_jobs...")
            # Try to find in podcast_jobs
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
            job_data = None
            for job_doc in jobs_query:
                job_data = job_doc.to_dict()
                break
            
            if not job_data:
                print(f"  ❌ Episode {canonical} not found in database")
                continue
            
            # Construct podcast_data from job
            podcast_data = job_data
            subscriber_id = job_data.get('subscriber_id')
        else:
            ep_data = episode_doc.to_dict()
            subscriber_id = ep_data.get('subscriber_id')
            
            # Find corresponding podcast_job
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
            job_data = None
            for job_doc in jobs_query:
                job_data = job_doc.to_dict()
                break
            
            if job_data:
                podcast_data = job_data
            else:
                # Construct from episode data
                podcast_data = {
                    'result': {
                        'canonical_filename': canonical,
                        'title': ep_data.get('title'),
                        'audio_url': ep_data.get('audio_url'),
                        'thumbnail_url': ep_data.get('thumbnail_url'),
                        'description': ep_data.get('description_markdown') or ep_data.get('description_html', ''),
                    },
                    'request': ep_data.get('request', {}),
                    'subscriber_id': subscriber_id
                }
        
        # Get subscriber data if available
        subscriber_data = None
        if subscriber_id:
            subscriber_doc = db.collection('subscribers').document(subscriber_id).get()
            if subscriber_doc.exists:
                subscriber_data = subscriber_doc.to_dict()
        
        try:
            # Remove from RSS feed (submit_to_rss=False means remove)
            await rss_service.update_rss_feed(
                podcast_data,
                subscriber_data,
                False,  # submit_to_rss = False means remove
                None    # attribution_initials
            )
            
            # Update database to mark as not submitted to RSS
            db.collection('episodes').document(canonical).update({
                'submitted_to_rss': False,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Also update podcast_jobs if it exists
            jobs_query = db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).limit(1).stream()
            for job_doc in jobs_query:
                job_doc.reference.update({
                    'submitted_to_rss': False,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
                break
            
            print(f"  ✅ Successfully removed {canonical} from RSS feed")
            
        except Exception as e:
            print(f"  ❌ Failed to remove {canonical}: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 80)
    print("✅ REMOVAL COMPLETE")
    print("=" * 80)
    print()
    print("Verifying RSS feed...")
    print()
    
    # Verify removal
    from monitor_rss_updates import monitor_changes
    result = monitor_changes()
    
    if result and result['episodes_removed']:
        print()
        print("✅ SUCCESS: Both episodes have been removed from RSS feed")
        print(f"✅ RSS feed now has {result['total_episodes']} episodes (target: 72)")
    else:
        print()
        print("⏳ Episodes may still be in RSS feed - check the status above")

if __name__ == "__main__":
    asyncio.run(remove_episodes_from_rss())


