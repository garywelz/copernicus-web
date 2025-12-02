#!/usr/bin/env python3
"""List all GUIDs in RSS feed to see what's actually there"""

from google.cloud import storage
import xml.etree.ElementTree as ET

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

items = channel.findall("item")
itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

print(f"Found {len(items)} items in RSS feed\n")
print("="*80)

uuid_guids = [
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

print("Checking for UUID GUIDs in RSS feed:\n")

found_count = 0
for uuid_guid in uuid_guids:
    found = False
    for item in items:
        guid_elem = item.find("guid")
        if guid_elem is not None and guid_elem.text:
            guid = guid_elem.text.strip()
            if guid == uuid_guid:
                found = True
                found_count += 1
                title_elem = item.find("title")
                title = title_elem.text if title_elem else "Unknown"
                if title and "<![CDATA[" in title:
                    title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
                
                itunes_image_elem = item.find(f"{itunes_ns}image")
                thumb_url = itunes_image_elem.get("href", "") if itunes_image_elem is not None else ""
                
                print(f"✅ Found: {uuid_guid}")
                print(f"   Title: {title[:60]}")
                print(f"   Thumbnail URL: {thumb_url}")
                print()
                break
    
    if not found:
        print(f"❌ Not found: {uuid_guid}\n")

print("="*80)
print(f"\nFound {found_count} out of {len(uuid_guids)} UUID GUIDs in RSS feed")

# Also list all GUIDs to see patterns
print("\n" + "="*80)
print("All GUIDs in RSS feed (first 20):")
print("="*80)
for i, item in enumerate(items[:20], 1):
    guid_elem = item.find("guid")
    if guid_elem is not None and guid_elem.text:
        guid = guid_elem.text.strip()
        title_elem = item.find("title")
        title = title_elem.text if title_elem else "Unknown"
        if title and "<![CDATA[" in title:
            title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
        
        is_canonical = guid.startswith('ever-')
        marker = "✅" if is_canonical else "⚠️"
        print(f"{marker} {i}. {guid[:50]} - {title[:40]}")

