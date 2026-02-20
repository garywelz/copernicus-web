"""
Export valid episode GUIDs from RSS feed for YouTube playlist cleanup
Creates a reference list of what SHOULD be in the YouTube playlist
"""

import asyncio
import json
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

async def export_valid_guids():
    """Export all valid episode GUIDs from RSS feed"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print("❌ RSS feed file not found")
        return
    
    # Download RSS feed
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        print("❌ RSS feed missing channel element")
        return
    
    items = channel.findall("item")
    
    # Extract all valid episodes (with audio)
    valid_episodes = []
    for item in items:
        guid_elem = item.find("guid")
        title_elem = item.find("title")
        enclosure = item.find("enclosure")
        pub_date_elem = item.find("pubDate")
        
        guid = guid_elem.text if guid_elem is not None else None
        title = unescape(title_elem.text) if title_elem is not None else "Untitled"
        audio_url = enclosure.get("url") if enclosure is not None else ""
        
        has_audio = bool(audio_url and audio_url.strip())
        
        if has_audio and guid:
            valid_episodes.append({
                'guid': guid,
                'title': title,
                'audio_url': audio_url,
                'pub_date': pub_date_elem.text if pub_date_elem is not None else ""
            })
    
    # Sort by publication date (newest first)
    valid_episodes.sort(key=lambda x: x['pub_date'], reverse=True)
    
    # Create output
    guids_only = [ep['guid'] for ep in valid_episodes]
    
    print("=" * 80)
    print("📋 VALID EPISODE GUIDs FOR YOUTUBE PLAYLIST")
    print("=" * 80)
    print()
    print(f"Total valid episodes in RSS feed: {len(valid_episodes)}")
    print()
    print("YouTube playlist SHOULD contain exactly these GUIDs:")
    print()
    print("GUIDs (comma-separated):")
    print(",".join(guids_only))
    print()
    print("=" * 80)
    print("📝 DETAILED LIST")
    print("=" * 80)
    print()
    for i, ep in enumerate(valid_episodes, 1):
        print(f"{i:3d}. {ep['guid']:30s} | {ep['title'][:50]}")
    
    # Save to JSON file
    output_file = "valid_youtube_guids.json"
    with open(output_file, 'w') as f:
        json.dump({
            'total_count': len(valid_episodes),
            'rss_feed_url': f"https://storage.googleapis.com/{RSS_BUCKET_NAME}/{RSS_FEED_BLOB_NAME}",
            'guids': guids_only,
            'episodes': valid_episodes
        }, f, indent=2)
    
    print()
    print(f"✅ Saved to: {output_file}")
    print()
    print("=" * 80)
    print("💡 HOW TO CLEAN UP YOUTUBE PLAYLIST")
    print("=" * 80)
    print()
    print("Since YouTube playlist has 164 videos but RSS feed has only 73:")
    print()
    print("1. MANUAL CLEANUP (Recommended):")
    print("   - Go to your YouTube playlist")
    print("   - Compare each video's title/description with the GUIDs above")
    print("   - Remove videos that don't match any GUID in the list")
    print("   - Remove duplicate videos (keep the newest)")
    print()
    print("2. YOUTUBE RSS SYNC:")
    print("   - YouTube automatically adds new episodes from RSS feed")
    print("   - However, it does NOT automatically remove old episodes")
    print("   - You need to manually remove videos not in the RSS feed")
    print()
    print("3. TO IDENTIFY DUPLICATES:")
    print("   - Look for videos with identical or very similar titles")
    print("   - Check video descriptions for GUIDs")
    print("   - Remove older duplicates, keep the newest")
    print()
    print("4. EXPECTED RESULT:")
    print(f"   - YouTube playlist should have exactly {len(valid_episodes)} videos")
    print("   - Each video should correspond to one GUID from the list above")
    print()
    
    return valid_episodes

if __name__ == "__main__":
    asyncio.run(export_valid_guids())


