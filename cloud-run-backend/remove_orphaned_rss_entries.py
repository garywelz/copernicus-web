"""
Remove orphaned RSS feed entries that don't have corresponding episodes or audio files
"""

import asyncio
from google.cloud import storage
from xml.etree import ElementTree as ET
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

# Episodes to remove from RSS (they don't exist in database)
ORPHANED_EPISODES = [
    "ever-chem-250021",  # "Silicon compounds"
    "ever-phys-250046",   # "Matrix Multiplication advances"
]

async def remove_orphaned_entries():
    """Remove orphaned entries from RSS feed"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print("❌ RSS feed file not found")
        return
    
    print("=" * 80)
    print("🗑️  REMOVING ORPHANED RSS ENTRIES")
    print("=" * 80)
    print()
    
    # Download current RSS feed
    blob.reload()
    current_generation = blob.generation
    xml_bytes = blob.download_as_bytes()
    
    # Parse XML
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        print("❌ RSS feed missing channel element")
        return
    
    # Find and remove orphaned entries
    removed_count = 0
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        guid_text = guid_el.text if guid_el is not None else None
        
        if guid_text in ORPHANED_EPISODES:
            title_el = item.find("title")
            title = title_el.text if title_el is not None else guid_text
            print(f"🗑️  Removing: {title} ({guid_text})")
            channel.remove(item)
            removed_count += 1
    
    if removed_count == 0:
        print("✅ No orphaned entries found to remove")
        return
    
    # Save updated RSS feed
    new_xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    # Restore CDATA markers
    xml_text = new_xml_bytes.decode("utf-8")
    xml_text = xml_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
    new_xml_bytes = xml_text.encode("utf-8")
    
    try:
        blob.upload_from_string(
            new_xml_bytes,
            content_type="application/rss+xml",
            if_generation_match=current_generation,
        )
        print(f"\n✅ Successfully removed {removed_count} orphaned entry/entries from RSS feed")
        print(f"   RSS feed updated at: https://storage.googleapis.com/{RSS_BUCKET_NAME}/{RSS_FEED_BLOB_NAME}")
    except Exception as e:
        print(f"\n❌ Failed to update RSS feed: {e}")
        print("   The feed may have been updated concurrently. Please retry.")

if __name__ == "__main__":
    asyncio.run(remove_orphaned_entries())


