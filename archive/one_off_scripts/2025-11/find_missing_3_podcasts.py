#!/usr/bin/env python3
"""Find the 3 missing podcasts (64 expected, 61 found)"""

import sys
from google.cloud import firestore
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def main():
    print("🔍 Finding the 3 Missing Podcasts")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # Get all podcast_jobs
    print("\n📊 Analyzing podcast_jobs collection...")
    all_jobs = list(db.collection('podcast_jobs').stream())
    print(f"Total jobs: {len(all_jobs)}")
    
    # Count by status
    by_status = {}
    failed_jobs = []
    generating_jobs = []
    
    for job_doc in all_jobs:
        job_data = job_doc.to_dict() or {}
        status = job_data.get('status', 'unknown')
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename')
        title = result.get('title') or job_data.get('request', {}).get('topic', 'Untitled')
        
        if status not in by_status:
            by_status[status] = []
        by_status[status].append({
            'job_id': job_doc.id,
            'canonical': canonical,
            'title': title[:60]
        })
        
        if status == 'failed':
            failed_jobs.append({
                'job_id': job_doc.id,
                'canonical': canonical,
                'title': title,
                'error': job_data.get('error'),
                'created_at': job_data.get('created_at')
            })
        
        if status == 'generating_content':
            generating_jobs.append({
                'job_id': job_doc.id,
                'canonical': canonical,
                'title': title,
                'created_at': job_data.get('created_at')
            })
    
    print("\n📊 Jobs by Status:")
    for status, items in sorted(by_status.items()):
        print(f"  {status}: {len(items)}")
    
    # Check for failed jobs that might be the missing ones
    if failed_jobs:
        print(f"\n❌ Failed Jobs ({len(failed_jobs)}):")
        for job in failed_jobs:
            print(f"  - {job['title'][:60]}")
            print(f"    Job ID: {job['job_id']}")
            print(f"    Canonical: {job['canonical'] or 'None'}")
            if job['error']:
                print(f"    Error: {str(job['error'])[:100]}")
            print()
    
    # Check for stuck generating jobs
    if generating_jobs:
        print(f"\n⏳ Stuck in 'generating_content' Status ({len(generating_jobs)}):")
        for job in generating_jobs:
            print(f"  - {job['title'][:60]}")
            print(f"    Job ID: {job['job_id']}")
            print(f"    Created: {job['created_at']}")
            print()
    
    # Get all episodes
    print("\n📊 Analyzing episodes collection...")
    all_episodes = list(db.collection('episodes').stream())
    print(f"Total episodes: {len(all_episodes)}")
    
    # Check for episodes without corresponding jobs
    episode_canonicals = set(episode_doc.id for episode_doc in all_episodes)
    job_canonicals = set()
    
    for job_doc in all_jobs:
        job_data = job_doc.to_dict() or {}
        canonical = job_data.get('result', {}).get('canonical_filename')
        if canonical:
            job_canonicals.add(canonical)
    
    orphan_episodes = episode_canonicals - job_canonicals
    if orphan_episodes:
        print(f"\n⚠️  Episodes without corresponding jobs ({len(orphan_episodes)}):")
        for canonical in list(orphan_episodes)[:10]:
            episode_doc = db.collection('episodes').document(canonical).get()
            if episode_doc.exists:
                episode_data = episode_doc.to_dict() or {}
                title = episode_data.get('title', 'Unknown')
                print(f"  - {title[:60]} ({canonical})")
    
    # Check RSS feed for entries not in database
    print("\n📊 Checking RSS feed for missing entries...")
    try:
        from google.cloud import storage
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        blob = bucket.blob("feeds/copernicus-mvp-rss-feed.xml")
        
        if blob.exists():
            import xml.etree.ElementTree as ET
            xml_bytes = blob.download_as_bytes()
            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")
            
            if channel is not None:
                rss_items = channel.findall("item")
                print(f"RSS feed has {len(rss_items)} items")
                
                rss_guids = set()
                for item in rss_items:
                    guid_elem = item.find("guid")
                    if guid_elem is not None and guid_elem.text:
                        rss_guids.add(guid_elem.text.strip())
                
                # Find RSS items not in database
                missing_from_db = rss_guids - episode_canonicals - job_canonicals
                if missing_from_db:
                    print(f"\n⚠️  RSS feed items not in database ({len(missing_from_db)}):")
                    for guid in list(missing_from_db)[:10]:
                        # Try to get title from RSS
                        for item in rss_items:
                            item_guid_elem = item.find("guid")
                            if item_guid_elem is not None and item_guid_elem.text and item_guid_elem.text.strip() == guid:
                                title_elem = item.find("title")
                                title = title_elem.text if title_elem is not None else "Unknown"
                                print(f"  - {title[:60]} ({guid})")
                                break
        else:
            print("RSS feed not found")
    except Exception as e:
        print(f"Error checking RSS feed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Total podcast_jobs: {len(all_jobs)}")
    print(f"Total episodes: {len(all_episodes)}")
    print(f"Unique canonicals in jobs: {len(job_canonicals)}")
    print(f"Unique canonicals in episodes: {len(episode_canonicals)}")
    print(f"Orphan episodes: {len(orphan_episodes)}")
    print(f"\nExpected: 64 podcasts")
    print(f"Found in jobs: {len(all_jobs)}")
    print(f"Found in episodes: {len(all_episodes)}")
    
    # Potential missing podcasts
    potential_missing = []
    if failed_jobs:
        potential_missing.extend([f"Failed: {j['title']}" for j in failed_jobs])
    if len(generating_jobs) > 2:
        potential_missing.extend([f"Stuck: {j['title']}" for j in generating_jobs[:3]])
    
    if potential_missing:
        print(f"\n⚠️  Potential missing podcasts:")
        for item in potential_missing[:5]:
            print(f"  - {item}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

