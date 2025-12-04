#!/usr/bin/env python3
"""Fix the 4 RSS feed podcasts that aren't in the database"""

import sys
from google.cloud import firestore
from google.cloud import storage
from google.cloud import secretmanager
from datetime import datetime
import xml.etree.ElementTree as ET
import re

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def get_rss_item_data(guid):
    """Get data for an RSS item by GUID"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        blob = bucket.blob("feeds/copernicus-mvp-rss-feed.xml")
        
        if not blob.exists():
            return None
        
        xml_bytes = blob.download_as_bytes()
        root = ET.fromstring(xml_bytes)
        channel = root.find("channel")
        
        if channel is None:
            return None
        
        for item in channel.findall("item"):
            guid_elem = item.find("guid")
            if guid_elem is not None and guid_elem.text and guid_elem.text.strip() == guid:
                # Extract all data from RSS item
                title_elem = item.find("title")
                link_elem = item.find("link")
                description_elem = item.find("description")
                pub_date_elem = item.find("pubDate")
                
                # iTunes namespace
                itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
                enclosure_elem = item.find("enclosure")
                
                # Media namespace
                media_ns = "{http://search.yahoo.com/mrss/}"
                thumbnail_elem = item.find(f"{media_ns}thumbnail")
                content_elem = item.find(f"{media_ns}content")
                
                title = title_elem.text if title_elem is not None and title_elem.text else "Unknown"
                if title and isinstance(title, str) and "<![CDATA[" in title:
                    title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title, flags=re.DOTALL)
                
                description = description_elem.text if description_elem is not None and description_elem.text else ""
                if description and isinstance(description, str) and "<![CDATA[" in description:
                    description = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', description, flags=re.DOTALL)
                
                audio_url = None
                if enclosure_elem is not None:
                    audio_url = enclosure_elem.get("url")
                
                thumbnail_url = None
                if thumbnail_elem is not None:
                    thumbnail_url = thumbnail_elem.get("url")
                elif content_elem is not None:
                    thumbnail_url = content_elem.get("url")
                
                # Try iTunes image as fallback
                itunes_image_elem = item.find(f"{itunes_ns}image")
                if not thumbnail_url and itunes_image_elem is not None:
                    thumbnail_url = itunes_image_elem.get("href")
                
                return {
                    'guid': guid.strip(),
                    'title': title.strip(),
                    'description': description.strip(),
                    'link': link_elem.text if link_elem is not None else None,
                    'pub_date': pub_date_elem.text if pub_date_elem is not None else None,
                    'audio_url': audio_url,
                    'thumbnail_url': thumbnail_url
                }
        
        return None
    except Exception as e:
        print(f"Error reading RSS feed: {e}")
        return None

def main():
    print("🔧 Fixing RSS Feed Podcasts Missing from Database")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    # The 4 missing podcasts
    missing_guids = [
        "ever-phys-250044",  # Prime Number Theory update
        "ever-phys-250045",  # New materials created using AI
        "ever-phys-250046",  # Matrix Multiplication advances
        "ever-phys-250043",  # Quantum Computing chip advances
    ]
    
    print(f"\n📋 Processing {len(missing_guids)} missing podcasts...\n")
    
    fixed_count = 0
    failed_count = 0
    
    for guid in missing_guids:
        print(f"🔍 Processing: {guid}")
        print("-" * 80)
        
        # Check if it already exists
        episode_doc = db.collection('episodes').document(guid).get()
        if episode_doc.exists:
            print(f"⚠️  Already exists in episodes collection")
            continue
        
        # Get data from RSS feed
        rss_data = get_rss_item_data(guid)
        
        if not rss_data:
            print(f"❌ Could not find in RSS feed")
            failed_count += 1
            continue
        
        print(f"✅ Found in RSS feed:")
        print(f"   Title: {rss_data['title']}")
        print(f"   Audio URL: {rss_data['audio_url']}")
        print(f"   Thumbnail URL: {rss_data['thumbnail_url']}")
        
        # Extract category from canonical filename
        if guid.startswith('ever-'):
            category_parts = guid.split('-')
            if len(category_parts) >= 2:
                category_slug = category_parts[1]
                category_map = {
                    'bio': 'Biology',
                    'chem': 'Chemistry',
                    'compsci': 'Computer Science',
                    'math': 'Mathematics',
                    'phys': 'Physics'
                }
                category = category_map.get(category_slug, 'Physics')
            else:
                category = 'Physics'
        else:
            category = 'Physics'
        
        # Create episode document
        try:
            episode_data = {
                'episode_id': guid,
                'canonical_filename': guid,
                'slug': guid,
                'title': rss_data['title'],
                'category': category,
                'description': rss_data['description'],
                'audio_url': rss_data['audio_url'],
                'thumbnail_url': rss_data['thumbnail_url'],
                'link': rss_data['link'],
                'pub_date': rss_data['pub_date'],
                'submitted_to_rss': True,
                'created_at': datetime.utcnow().isoformat(),
                'generated_at': rss_data['pub_date'] if rss_data['pub_date'] else datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                # Try to infer subscriber_id from other physics podcasts
                'subscriber_id': None,  # Will need to be set manually or inferred
            }
            
            # Save to episodes collection
            db.collection('episodes').document(guid).set(episode_data)
            print(f"✅ Created episode document: {guid}")
            
            # Check if we can find a corresponding job
            # Search for jobs with similar title
            jobs = db.collection('podcast_jobs').where('result.canonical_filename', '==', guid).limit(1).stream()
            job_found = False
            for job_doc in jobs:
                job_found = True
                print(f"   Found corresponding job: {job_doc.id}")
                break
            
            if not job_found:
                print(f"   ⚠️  No corresponding job found (episode-only entry)")
            
            fixed_count += 1
            print()
            
        except Exception as e:
            print(f"❌ Error creating episode: {e}")
            failed_count += 1
            print()
    
    # Summary
    print("="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Total processed: {len(missing_guids)}")
    print(f"✅ Fixed: {fixed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"⚠️  Already existed: {len(missing_guids) - fixed_count - failed_count}")
    
    if fixed_count > 0:
        print(f"\n✅ Successfully added {fixed_count} podcasts to database!")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

