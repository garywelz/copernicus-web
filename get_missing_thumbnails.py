#!/usr/bin/env python3
"""Script to identify which episodes are missing thumbnails"""

import requests
import json
from google.cloud import secretmanager
from google.cloud import firestore
from google.cloud import storage

GCP_PROJECT_ID = "regal-scholar-453620-r7"

def get_admin_api_key():
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        print(f"Error getting admin API key: {e}")
        return None

def check_missing_thumbnails():
    """Check which episodes in RSS feed are missing thumbnails"""
    from google.cloud import storage
    from xml.etree import ElementTree as ET
    
    # Get RSS feed
    storage_client = storage.Client()
    bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
    blob = bucket.blob("feeds/copernicus-mvp-rss-feed.xml")
    
    if not blob.exists():
        print("RSS feed not found")
        return
    
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        print("RSS feed missing channel element")
        return
    
    podcast_storage_bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
    db = firestore.Client(project=GCP_PROJECT_ID)
    
    items = channel.findall("item")
    itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
    
    missing = []
    
    for item in items:
        guid_elem = item.find("guid")
        guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None
        
        if not guid:
            continue
        
        title_elem = item.find("title")
        title = title_elem.text if title_elem is not None else "Unknown"
        # Remove CDATA markers
        if title and "<![CDATA[" in title:
            title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
        
        # Check if thumbnail exists
        expected_thumbnail_blob_name = f"thumbnails/{guid}-thumb.jpg"
        thumbnail_blob = podcast_storage_bucket.blob(expected_thumbnail_blob_name)
        
        if not thumbnail_blob.exists():
            # Try to get episode title from Firestore
            episode_doc = db.collection('episodes').document(guid).get()
            if episode_doc.exists:
                episode_data = episode_doc.to_dict() or {}
                title = episode_data.get('title', title)
            
            missing.append({
                'guid': guid,
                'title': title[:60] if title else 'Unknown',
                'expected_path': expected_thumbnail_blob_name
            })
    
    if missing:
        print(f"\n❌ Found {len(missing)} episodes with missing thumbnails:\n")
        for i, ep in enumerate(missing, 1):
            print(f"{i}. {ep['title']}")
            print(f"   GUID: {ep['guid']}")
            print(f"   Expected: {ep['expected_path']}")
            print()
    else:
        print("\n✅ All episodes have thumbnails!")

if __name__ == "__main__":
    print("🔍 Checking for missing thumbnails...\n")
    check_missing_thumbnails()

