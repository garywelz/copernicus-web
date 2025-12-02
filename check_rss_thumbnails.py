#!/usr/bin/env python3
"""Check what thumbnail URLs are in the RSS feed for the 8 episodes"""

from google.cloud import storage
import xml.etree.ElementTree as ET

# The 8 episodes
episodes = [
    'ever-bio-250040',
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    'ever-math-250036',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

print("🔍 Checking RSS feed for thumbnail URLs...\n")
print("="*80)

storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
blob = bucket.blob("feeds/copernicus-mvp-rss-feed.xml")

if not blob.exists():
    print("RSS feed not found!")
    exit(1)

xml_bytes = blob.download_as_bytes()
root = ET.fromstring(xml_bytes)
channel = root.find("channel")

if channel is None:
    print("RSS feed missing channel element!")
    exit(1)

itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
media_ns = "{http://search.yahoo.com/mrss/}"

items = channel.findall("item")

print(f"Found {len(items)} items in RSS feed\n")

for guid in episodes:
    found = False
    for item in items:
        guid_elem = item.find("guid")
        if guid_elem is not None and guid_elem.text and guid_elem.text.strip() == guid:
            found = True
            
            title_elem = item.find("title")
            title = title_elem.text if title_elem is not None else "Unknown"
            if title and "<![CDATA[" in title:
                title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
            
            # Get thumbnail URL from RSS
            itunes_image_elem = item.find(f"{itunes_ns}image")
            thumbnail_url = None
            if itunes_image_elem is not None:
                thumbnail_url = itunes_image_elem.get("href", "")
            
            media_thumb_elem = item.find(f"{media_ns}thumbnail")
            media_thumb_url = None
            if media_thumb_elem is not None:
                media_thumb_url = media_thumb_elem.get("url", "")
            
            print(f"✓ {title[:60]}")
            print(f"  GUID: {guid}")
            print(f"  iTunes image URL: {thumbnail_url}")
            print(f"  Media thumbnail URL: {media_thumb_url}")
            
            # Extract blob name from URL
            if thumbnail_url:
                if "thumbnails/" in thumbnail_url:
                    blob_name = thumbnail_url.split("thumbnails/")[1]
                    print(f"  Blob name: thumbnails/{blob_name}")
                    
                    # Check if this blob exists
                    thumb_blob = bucket.blob(f"thumbnails/{blob_name}")
                    if thumb_blob.exists():
                        print(f"  ✅ EXISTS in GCS")
                    else:
                        print(f"  ❌ NOT FOUND in GCS")
            
            print()
            break
    
    if not found:
        print(f"✗ GUID {guid} NOT FOUND in RSS feed\n")

print("="*80)

