"""
Analyze RSS feed to help sync with YouTube playlist
Extract all episodes with their GUIDs, titles, and metadata
"""

import asyncio
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

async def analyze_rss_feed():
    """Extract all episode information from RSS feed"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(RSS_BUCKET_NAME)
    blob = bucket.blob(RSS_FEED_BLOB_NAME)
    
    if not blob.exists():
        print("❌ RSS feed file not found")
        return
    
    print("=" * 80)
    print("📊 RSS FEED ANALYSIS FOR YOUTUBE SYNC")
    print("=" * 80)
    print()
    
    # Download RSS feed
    xml_bytes = blob.download_as_bytes()
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    
    if channel is None:
        print("❌ RSS feed missing channel element")
        return
    
    items = channel.findall("item")
    print(f"Total episodes in RSS feed: {len(items)}")
    print()
    
    # Extract all episode information
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
        
        episodes.append({
            'guid': guid,
            'title': title,
            'audio_url': audio_url,
            'pub_date': pub_date,
            'has_audio': has_audio
        })
    
    # Sort by publication date (newest first)
    episodes.sort(key=lambda x: x['pub_date'], reverse=True)
    
    # Print summary
    print("=" * 80)
    print("📋 EPISODE LIST (Newest to Oldest)")
    print("=" * 80)
    print()
    
    episodes_with_audio = [e for e in episodes if e['has_audio']]
    episodes_without_audio = [e for e in episodes if not e['has_audio']]
    
    print(f"Episodes with audio: {len(episodes_with_audio)}")
    print(f"Episodes without audio: {len(episodes_without_audio)}")
    print()
    
    if episodes_without_audio:
        print("⚠️  Episodes WITHOUT audio (should be removed from RSS):")
        for ep in episodes_without_audio:
            print(f"  - {ep['guid']}: {ep['title'][:60]}...")
        print()
    
    # Print all episodes with GUIDs
    print("All episodes in RSS feed:")
    print("-" * 80)
    for i, ep in enumerate(episodes, 1):
        audio_status = "✅" if ep['has_audio'] else "❌ NO AUDIO"
        print(f"{i:3d}. {audio_status} {ep['guid']:30s} | {ep['title'][:40]}")
    
    print()
    print("=" * 80)
    print("💡 RECOMMENDATIONS FOR YOUTUBE SYNC")
    print("=" * 80)
    print()
    print("1. YouTube playlist should contain ONLY these GUIDs:")
    print(f"   Total: {len(episodes_with_audio)} episodes with valid audio")
    print()
    print("2. To sync YouTube playlist with RSS feed:")
    print("   - YouTube automatically syncs from RSS feed")
    print("   - Remove any videos in YouTube playlist that don't match the GUIDs above")
    print("   - Videos with duplicate GUIDs should be removed (keep the newest)")
    print()
    print("3. GUIDs currently in RSS feed (for reference):")
    print("   " + ", ".join([ep['guid'] for ep in episodes_with_audio]))
    print()
    
    # Check for potential duplicates by GUID
    guid_counts = {}
    for ep in episodes:
        if ep['guid']:
            guid_counts[ep['guid']] = guid_counts.get(ep['guid'], 0) + 1
    
    duplicates = {guid: count for guid, count in guid_counts.items() if count > 1}
    if duplicates:
        print("⚠️  DUPLICATE GUIDs FOUND IN RSS FEED:")
        for guid, count in duplicates.items():
            print(f"   {guid}: appears {count} times")
        print("   These should be removed!")
        print()
    
    return episodes_with_audio

if __name__ == "__main__":
    asyncio.run(analyze_rss_feed())


