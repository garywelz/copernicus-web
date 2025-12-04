#!/usr/bin/env python3
"""Find the 4 YouTube-reported podcasts that aren't in our database"""

import sys
from google.cloud import firestore
from google.cloud import secretmanager

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def search_partial_title(db, search_term):
    """Search for podcasts with partial title match"""
    results = []
    
    # Search in episodes collection
    episodes = db.collection('episodes').stream()
    for episode_doc in episodes:
        episode_data = episode_doc.to_dict() or {}
        title = episode_data.get('title', '')
        if search_term.lower() in title.lower():
            results.append({
                'type': 'episode',
                'canonical': episode_doc.id,
                'title': title,
                'data': episode_data
            })
    
    # Search in podcast_jobs collection
    jobs = db.collection('podcast_jobs').stream()
    for job_doc in jobs:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        title = result.get('title') or job_data.get('request', {}).get('topic', '')
        if search_term.lower() in title.lower():
            results.append({
                'type': 'job',
                'job_id': job_doc.id,
                'canonical': result.get('canonical_filename'),
                'title': title,
                'data': job_data
            })
    
    return results

def main():
    print("🔍 Finding YouTube-Reported Missing Podcasts")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # YouTube-reported missing podcasts
    youtube_missing = [
        "Quantum Computing chip advances",
        "Prime Number Theory update",
        "New materials created using AI",
        "Matrix Multiplication advances"
    ]
    
    print(f"\n📋 Searching for {len(youtube_missing)} YouTube-reported podcasts...\n")
    
    found_count = 0
    not_found = []
    
    for missing_title in youtube_missing:
        print(f"🔍 Searching for: '{missing_title}'")
        print("-" * 80)
        
        # Try exact match first
        exact_match = search_partial_title(db, missing_title)
        
        if exact_match:
            print(f"✅ Found {len(exact_match)} match(es):")
            for match in exact_match:
                print(f"  Title: {match['title']}")
                print(f"  Type: {match['type']}")
                if match.get('canonical'):
                    print(f"  Canonical: {match['canonical']}")
                if match.get('job_id'):
                    print(f"  Job ID: {match['job_id']}")
                print()
            found_count += len(exact_match)
        else:
            # Try searching for keywords
            keywords = missing_title.split()
            print(f"❌ No exact match. Trying keywords: {keywords}")
            
            keyword_matches = []
            for keyword in keywords:
                if len(keyword) > 3:  # Skip short words
                    matches = search_partial_title(db, keyword)
                    keyword_matches.extend(matches)
            
            if keyword_matches:
                # Remove duplicates
                unique_matches = []
                seen = set()
                for match in keyword_matches:
                    match_id = match.get('canonical') or match.get('job_id')
                    if match_id and match_id not in seen:
                        seen.add(match_id)
                        unique_matches.append(match)
                
                if unique_matches:
                    print(f"⚠️  Found {len(unique_matches)} potential matches by keywords:")
                    for match in unique_matches[:3]:  # Show first 3
                        print(f"  - {match['title']}")
                        if match.get('canonical'):
                            print(f"    Canonical: {match['canonical']}")
                    print()
            else:
                print(f"❌ Not found even by keywords")
                not_found.append(missing_title)
                print()
    
    # Check RSS feed for these titles
    print("\n" + "="*80)
    print("📊 Checking RSS Feed")
    print("="*80)
    
    try:
        from google.cloud import storage
        import xml.etree.ElementTree as ET
        import re
        
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        blob = bucket.blob("feeds/copernicus-mvp-rss-feed.xml")
        
        if blob.exists():
            xml_bytes = blob.download_as_bytes()
            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")
            
            if channel is not None:
                rss_items = channel.findall("item")
                print(f"RSS feed has {len(rss_items)} items")
                
                rss_found = []
                for missing_title in youtube_missing:
                    for item in rss_items:
                        title_elem = item.find("title")
                        if title_elem is not None and title_elem.text:
                            rss_title = title_elem.text
                            # Remove CDATA markers
                            if "<![CDATA[" in rss_title:
                                rss_title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', rss_title, flags=re.DOTALL)
                            
                            # Check for partial match
                            if missing_title.lower() in rss_title.lower():
                                guid_elem = item.find("guid")
                                guid = guid_elem.text if guid_elem is not None else "Unknown"
                                rss_found.append({
                                    'search': missing_title,
                                    'found_title': rss_title.strip(),
                                    'guid': guid.strip()
                                })
                                break
                
                if rss_found:
                    print(f"\n✅ Found {len(rss_found)} in RSS feed:")
                    for item in rss_found:
                        print(f"  Search: '{item['search']}'")
                        print(f"  Found: '{item['found_title']}'")
                        print(f"  GUID: {item['guid']}")
                        print()
        else:
            print("RSS feed not found")
    except Exception as e:
        print(f"Error checking RSS feed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Total searched: {len(youtube_missing)}")
    print(f"Found in database: {found_count}")
    print(f"Not found: {len(not_found)}")
    
    if not_found:
        print(f"\n❌ Not found in database:")
        for title in not_found:
            print(f"  - {title}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

