"""
Manually fix RSS feed entry with empty audio URL
"""

import asyncio
from google.cloud import storage
from xml.etree import ElementTree as ET
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

async def fix_audio_url():
    """Fix empty audio URL in RSS feed for ever-phys-250043"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print("❌ RSS feed file not found")
        return
    
    print("=" * 80)
    print("🔧 FIXING AUDIO URL IN RSS FEED")
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
    
    # Find and fix the entry
    fixed = False
    for item in channel.findall("item"):
        guid_el = item.find("guid")
        guid_text = guid_el.text if guid_el is not None else None
        
        if guid_text == "ever-phys-250043":
            title_el = item.find("title")
            title = title_el.text if title_el is not None else guid_text
            print(f"📋 Found entry: {title}")
            
            # Check current audio URL
            enclosure = item.find("enclosure")
            if enclosure is not None:
                current_url = enclosure.get("url", "")
                print(f"   Current audio URL: {current_url or '(empty)'}")
                
                if not current_url:
                    # Fix the audio URL
                    correct_url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/ever-phys-250043.mp3"
                    enclosure.set("url", correct_url)
                    
                    # Update length (3.0 MB = 3141549 bytes)
                    enclosure.set("length", "3141549")
                    
                    print(f"   ✅ Updated audio URL: {correct_url}")
                    fixed = True
                else:
                    print(f"   ✅ Audio URL already set")
                    fixed = True
    
    if not fixed:
        print("❌ Entry not found in RSS feed")
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
        print(f"\n✅ Successfully updated RSS feed")
        print(f"   RSS feed: https://storage.googleapis.com/{RSS_BUCKET_NAME}/{RSS_FEED_BLOB_NAME}")
    except Exception as e:
        print(f"\n❌ Failed to update RSS feed: {e}")
        print("   The feed may have been updated concurrently. Please retry.")

if __name__ == "__main__":
    asyncio.run(fix_audio_url())


