#!/usr/bin/env python3
"""
Standalone script to sync Firestore episode catalog with RSS feed status.

This script:
1. Reads the RSS feed XML from Google Cloud Storage
2. Extracts all episode GUIDs (slugs) from the feed
3. Updates Firestore episodes to mark them as submitted_to_rss=true
"""

import os
import sys
from datetime import datetime, timezone
from google.cloud import storage
from google.cloud import firestore
import xml.etree.ElementTree as ET

# Configuration - matches main.py
RSS_BUCKET_NAME = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
RSS_FEED_BLOB_NAME = os.getenv("COPERNICUS_RSS_FEED_BLOB", "feeds/copernicus-mvp-rss-feed.xml")
EPISODE_COLLECTION_NAME = os.getenv("COPERNICUS_EPISODE_COLLECTION", "episodes")

def main():
    print("🔄 Starting RSS feed sync...")
    
    # Initialize clients
    print("📦 Initializing GCS and Firestore clients...")
    storage_client = storage.Client()
    # Use the named database 'copernicusai' (not the default)
    db = firestore.Client(database='copernicusai')
    
    # Read RSS feed from GCS
    print(f"📡 Reading RSS feed from gs://{RSS_BUCKET_NAME}/{RSS_FEED_BLOB_NAME}...")
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print(f"❌ ERROR: RSS feed file not found in storage")
        sys.exit(1)
    
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    
    # Extract all GUIDs (episode slugs) from RSS feed
    rss_guids = set()
    for guid_elem in root.findall(".//guid"):
        if guid_elem.text:
            rss_guids.add(guid_elem.text.strip())
    
    print(f"✅ Found {len(rss_guids)} episodes in RSS feed")
    print(f"   Episodes: {', '.join(sorted(list(rss_guids))[:10])}{'...' if len(rss_guids) > 10 else ''}")
    
    # Update Firestore episodes
    print(f"\n📊 Updating Firestore episodes collection '{EPISODE_COLLECTION_NAME}'...")
    episodes_collection = db.collection(EPISODE_COLLECTION_NAME)
    
    updated_count = 0
    not_found_in_rss = 0
    already_correct = 0
    not_found_in_firestore = 0
    
    # Get all episodes from Firestore
    all_episodes = list(episodes_collection.stream())
    print(f"   Found {len(all_episodes)} episodes in Firestore")
    
    for episode_doc in all_episodes:
        episode_data = episode_doc.to_dict() or {}
        slug = episode_data.get("slug") or episode_data.get("episode_id") or episode_doc.id
        
        # Check if this episode is in the RSS feed
        is_in_rss = slug in rss_guids
        currently_marked = episode_data.get("submitted_to_rss", False)
        
        if is_in_rss and not currently_marked:
            # Update to mark as submitted
            episodes_collection.document(episode_doc.id).update({
                "submitted_to_rss": True,
                "visibility": "public",
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            updated_count += 1
            print(f"   ✅ Marked {slug} as submitted_to_rss=True")
        elif not is_in_rss and currently_marked:
            # Update to mark as not submitted (in case it was removed from RSS)
            episodes_collection.document(episode_doc.id).update({
                "submitted_to_rss": False,
                "visibility": "private",
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            not_found_in_rss += 1
            print(f"   ⚠️  Marked {slug} as submitted_to_rss=False (not in RSS feed)")
        elif is_in_rss and currently_marked:
            already_correct += 1
    
    # Check for episodes in RSS feed that aren't in Firestore
    firestore_slugs = {ep.to_dict().get("slug") or ep.to_dict().get("episode_id") or ep.id 
                       for ep in all_episodes}
    missing_in_firestore = rss_guids - firestore_slugs
    
    # Create Firestore entries for RSS-only episodes
    created_count = 0
    if missing_in_firestore:
        print(f"\n📝 Creating {len(missing_in_firestore)} new Firestore entries from RSS feed...")
        
        # Parse RSS items to extract episode data
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                guid_elem = item.find("guid")
                if guid_elem is None or not guid_elem.text:
                    continue
                slug = guid_elem.text.strip()
                
                if slug not in missing_in_firestore:
                    continue
                
                # Extract data from RSS item
                title_elem = item.find("title")
                title = title_elem.text if title_elem is not None and title_elem.text else "Untitled Episode"
                
                description_elem = item.find("description")
                description = description_elem.text if description_elem is not None and description_elem.text else ""
                
                pub_date_elem = item.find("pubDate")
                pub_date = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else None
                
                # Extract audio URL from enclosure
                audio_url = None
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    audio_url = enclosure.get("url")
                
                # Extract thumbnail from itunes:image
                thumbnail_url = None
                for ns in ["{http://www.itunes.com/dtds/podcast-1.0.dtd}", ""]:
                    image_elem = item.find(f"{ns}image")
                    if image_elem is not None:
                        thumbnail_url = image_elem.get("href") or image_elem.text
                        break
                
                # Extract category
                category = None
                category_elem = item.find("category")
                if category_elem is not None:
                    category = category_elem.text
                
                # Extract category from slug if not found
                if not category and slug:
                    parts = slug.split("-")
                    if len(parts) >= 2:
                        cat_map = {
                            "bio": "Biology",
                            "chem": "Chemistry", 
                            "compsci": "Computer Science",
                            "math": "Mathematics",
                            "phys": "Physics"
                        }
                        category = cat_map.get(parts[1], parts[1].title())
                
                # Extract duration
                duration = None
                for ns in ["{http://www.itunes.com/dtds/podcast-1.0.dtd}", ""]:
                    duration_elem = item.find(f"{ns}duration")
                    if duration_elem is not None:
                        duration = duration_elem.text
                        break
                
                # Create Firestore document
                now = datetime.now(timezone.utc).isoformat()
                episode_data = {
                    "slug": slug,
                    "episode_id": slug,
                    "title": title,
                    "description_markdown": description,
                    "description_html": description,  # Will be converted later if needed
                    "summary": description[:200] if description else "",
                    "audio_url": audio_url,
                    "thumbnail_url": thumbnail_url,
                    "category": category,
                    "category_slug": slug.split("-")[1] if "-" in slug else None,
                    "submitted_to_rss": True,
                    "visibility": "public",
                    "created_at": pub_date or now,
                    "generated_at": pub_date or now,
                    "updated_at": now,
                    "engagement_metrics": {
                        "user_ratings": [],
                        "feedback_comments": [],
                        "play_count": 0,
                        "completion_rate": 0.0,
                        "shares": 0
                    },
                    "metadata_extended": {},
                }
                
                if duration:
                    episode_data["duration"] = duration
                
                # Use slug as document ID
                episodes_collection.document(slug).set(episode_data)
                created_count += 1
                print(f"   ✅ Created {slug}: {title[:50]}...")
        
        not_found_in_firestore = len(missing_in_firestore)
    
    # Summary
    print(f"\n✅ RSS sync complete!")
    print(f"   📊 Summary:")
    print(f"      - Episodes in RSS feed: {len(rss_guids)}")
    print(f"      - Episodes in Firestore (before): {len(all_episodes)}")
    print(f"      - Updated to submitted: {updated_count}")
    print(f"      - Updated to not submitted: {not_found_in_rss}")
    print(f"      - Already correct: {already_correct}")
    print(f"      - Created new entries: {created_count}")
    print(f"      - Total episodes in Firestore (after): {len(all_episodes) + created_count}")
    
    return {
        "rss_feed_episodes": len(rss_guids),
        "firestore_episodes_before": len(all_episodes),
        "firestore_episodes_after": len(all_episodes) + created_count,
        "updated_to_submitted": updated_count,
        "updated_to_not_submitted": not_found_in_rss,
        "already_correct": already_correct,
        "created_new_entries": created_count
    }

if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: {e}")
        print(traceback.format_exc())
        sys.exit(1)

