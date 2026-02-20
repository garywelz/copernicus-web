"""
List all valid episodes from RSS feed and help identify YouTube duplicates
"""

import json
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

def get_all_valid_episodes():
    """Get all valid episodes from RSS feed"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print("❌ RSS feed file not found")
        return None
    
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        print("❌ RSS feed missing channel element")
        return None
    
    items = channel.findall("item")
    
    episodes = []
    for item in items:
        guid_elem = item.find("guid")
        title_elem = item.find("title")
        enclosure = item.find("enclosure")
        pub_date_elem = item.find("pubDate")
        
        guid = guid_elem.text if guid_elem is not None else None
        title = unescape(title_elem.text) if title_elem is not None else "Untitled"
        audio_url = enclosure.get("url") if enclosure is not None else ""
        pub_date = pub_date_elem.text if pub_date_elem is not None else ""
        
        has_audio = bool(audio_url and audio_url.strip())
        
        if guid and has_audio:
            episodes.append({
                'guid': guid,
                'title': title,
                'pub_date': pub_date
            })
    
    # Sort by publication date (newest first)
    episodes.sort(key=lambda x: x['pub_date'], reverse=True)
    
    return episodes

def main():
    print("=" * 80)
    print("📋 VALID EPISODES IN RSS FEED (Should be in YouTube)")
    print("=" * 80)
    print()
    
    episodes = get_all_valid_episodes()
    
    if not episodes:
        print("❌ Could not retrieve episodes")
        return
    
    print(f"Total valid episodes: {len(episodes)}")
    print(f"YouTube playlist has: 111 videos")
    print(f"Expected in YouTube: {len(episodes)} videos")
    print(f"Videos to remove: {111 - len(episodes)} videos")
    print()
    print("=" * 80)
    print("✅ VALID GUIDs (Should appear EXACTLY ONCE in YouTube)")
    print("=" * 80)
    print()
    print("Each GUID below should appear exactly once in your YouTube playlist.")
    print("If you find 2+ videos with the same GUID → Remove duplicates (keep newest)")
    print("If you find a video that doesn't match any GUID → Remove it")
    print()
    print("-" * 80)
    
    for i, ep in enumerate(episodes, 1):
        print(f"{i:3d}. GUID: {ep['guid']:30s} | {ep['title'][:45]}")
    
    print()
    print("=" * 80)
    print("🔍 HOW TO FIND DUPLICATES IN YOUTUBE")
    print("=" * 80)
    print()
    print("STEP 1: Export YouTube Playlist Data")
    print("  - Go to your YouTube playlist")
    print("  - For each video, note:")
    print("    * Video title")
    print("    * Publication date")
    print("    * Description (look for GUID in format: ever-XXX-XXXXXX or news-XXX-XXXXXX)")
    print()
    print("STEP 2: Compare with Valid GUID List")
    print("  - Match each YouTube video to a GUID from the list above")
    print("  - Mark videos that:")
    print("    * Don't match any GUID → REMOVE")
    print("    * Match a GUID that already has a video → REMOVE (duplicate, keep newest)")
    print()
    print("STEP 3: Common Duplicate Patterns")
    print("  - Look for videos with identical or very similar titles")
    print("  - Check publication dates - duplicates often have different dates")
    print("  - Videos with old/broken thumbnails (you've already removed many)")
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print()
    print(f"YouTube Playlist: 111 videos")
    print(f"Valid Episodes (RSS): {len(episodes)}")
    print(f"Videos to Remove: {111 - len(episodes)}")
    print()
    print("After cleanup, you should have exactly {len(episodes)} videos,")
    print("each matching one GUID from the list above (no duplicates).")
    print()
    
    # Save to JSON for reference
    output_data = {
        'valid_episodes_count': len(episodes),
        'current_youtube_count': 111,
        'videos_to_remove': 111 - len(episodes),
        'target_count': len(episodes),
        'episodes': episodes,
        'guid_list': [ep['guid'] for ep in episodes]
    }
    
    output_file = "youtube_valid_episodes_list.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Reference data saved to: {output_file}")
    print()
    
    # Also create a simple text file with just GUIDs for easy copy-paste
    guid_file = "youtube_valid_guids.txt"
    with open(guid_file, 'w') as f:
        for ep in episodes:
            f.write(f"{ep['guid']}\n")
    
    print(f"✅ GUID list saved to: {guid_file} (one GUID per line)")
    print()

if __name__ == "__main__":
    main()


