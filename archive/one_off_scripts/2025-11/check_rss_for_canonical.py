#!/usr/bin/env python3
"""Check RSS feed to see if episodes have canonical filenames stored"""

from google.cloud import storage
import xml.etree.ElementTree as ET
import re

uuid_guids = [
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

print("🔍 Checking RSS feed for canonical filenames...\n")
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
items = channel.findall("item")

# List all thumbnails to check for canonical patterns
all_thumbnails = list(bucket.list_blobs(prefix="thumbnails/"))
thumbnail_names = [blob.name for blob in all_thumbnails if blob.name.endswith(('.jpg', '.jpeg'))]

print(f"Found {len(thumbnail_names)} thumbnails in bucket\n")

for uuid_guid in uuid_guids:
    print(f"\n📋 UUID GUID: {uuid_guid}")
    
    # Find in RSS feed
    for item in items:
        guid_elem = item.find("guid")
        if guid_elem and guid_elem.text and guid_elem.text.strip() == uuid_guid:
            title_elem = item.find("title")
            title = title_elem.text if title_elem else "Unknown"
            if title and "<![CDATA[" in title:
                title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
            
            print(f"  Title: {title[:60]}")
            
            # Check if there's a canonical filename pattern in the title or elsewhere
            # Look for patterns like "ever-bio-250040" in the title or description
            description_elem = item.find("description")
            description = description_elem.text if description_elem else ""
            
            # Try to extract canonical pattern from title/description
            # Look for "ever-{category}-{number}" pattern
            import re
            canonical_pattern = re.search(r'ever-(bio|math|phys|chem|compsci)-\d+', title + " " + description, re.IGNORECASE)
            
            if canonical_pattern:
                potential_canonical = canonical_pattern.group(0)
                print(f"  🔍 Found potential canonical: {potential_canonical}")
                
                # Check if thumbnail exists with this canonical name
                canonical_thumb = f"thumbnails/{potential_canonical}-thumb.jpg"
                if any(t == canonical_thumb for t in thumbnail_names):
                    print(f"  ✅ THUMBNAIL EXISTS with canonical name: {canonical_thumb}")
                else:
                    print(f"  ❌ No thumbnail found with canonical name")
            else:
                print(f"  ⚠️  No canonical pattern found in title/description")
            
            # Check what thumbnail URL is in RSS
            itunes_image_elem = item.find(f"{itunes_ns}image")
            if itunes_image_elem is not None:
                rss_thumb_url = itunes_image_elem.get("href", "")
                print(f"  RSS thumbnail URL: {rss_thumb_url}")
            
            break

print("\n" + "="*80)

