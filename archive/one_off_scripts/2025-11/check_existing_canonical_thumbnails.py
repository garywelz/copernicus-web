#!/usr/bin/env python3
"""Check if thumbnails already exist with canonical naming"""

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

print("🔍 Checking if thumbnails exist with canonical naming...\n")
print("="*80)

storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")

# Get RSS feed to see what canonical filenames are expected
rss_bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
rss_blob = rss_bucket.blob("feeds/copernicus-mvp-rss-feed.xml")

if rss_blob.exists():
    xml_bytes = rss_blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel:
        items = channel.findall("item")
        guid_to_title = {}
        for item in items:
            guid_elem = item.find("guid")
            if guid_elem and guid_elem.text:
                guid = guid_elem.text.strip()
                title_elem = item.find("title")
                if title_elem and title_elem.text:
                    title = title_elem.text
                    if "<![CDATA[" in title:
                        title = title.split("<![CDATA[")[1].split("]]>")[0] if "]]>" in title else title
                    guid_to_title[guid] = title

# List all thumbnails to see what exists
all_thumbnails = list(bucket.list_blobs(prefix="thumbnails/"))
thumbnail_names = [blob.name for blob in all_thumbnails if blob.name.endswith(('.jpg', '.jpeg', '.png', '.webp'))]

print(f"Found {len(thumbnail_names)} total thumbnails in bucket\n")

for guid in episodes:
    print(f"\n📋 GUID: {guid}")
    title = guid_to_title.get(guid, "Unknown")
    print(f"  Title: {title[:60]}")
    
    # Check if this GUID IS a canonical filename (starts with ever-)
    is_canonical = guid.startswith('ever-')
    
    if is_canonical:
        canonical = guid
        print(f"  ✅ GUID is already canonical: {canonical}")
    else:
        # Try to find canonical filename pattern
        # Look for thumbnails that might match
        print(f"  ⚠️  GUID is not canonical (UUID format)")
        # Check if there's a thumbnail with this exact GUID
        guid_thumb = f"thumbnails/{guid}-thumb.jpg"
        guid_exists = any(t == guid_thumb for t in thumbnail_names)
        print(f"  GUID thumbnail exists: {guid_exists}")
    
    # Check for canonical thumbnail
    canonical_thumb = f"thumbnails/{guid}-thumb.jpg"
    canonical_exists = any(t == canonical_thumb for t in thumbnail_names)
    
    # Also check for variations
    variations = [
        f"thumbnails/{guid}-thumb.jpg",
        f"thumbnails/{guid}-fallback-thumb.jpg",
        f"thumbnails/{guid}.jpg",
    ]
    
    found_variations = [v for v in variations if any(t == v for t in thumbnail_names)]
    
    if found_variations:
        print(f"  ✅ Found existing thumbnails:")
        for var in found_variations:
            print(f"      - {var}")
    else:
        print(f"  ❌ No thumbnail found with GUID/canonical name")

print("\n" + "="*80)
print("\n🔍 Searching for canonical-named thumbnails that might match...")
print("="*80)

# For UUID GUIDs, try to find if there's a canonical filename pattern
for guid in episodes:
    if not guid.startswith('ever-'):
        # This is a UUID - check if there are any thumbnails with similar patterns
        # Look for thumbnails that might be related
        matching = [t for t in thumbnail_names if guid[:8] in t or guid[-8:] in t]
        if matching:
            print(f"\n⚠️  GUID {guid} might have related thumbnails:")
            for match in matching[:5]:  # Show first 5
                print(f"    - {match}")

