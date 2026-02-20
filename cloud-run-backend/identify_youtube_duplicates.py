"""
Tool to help identify duplicate episodes in YouTube playlist
Provides a reference list and comparison method
"""

import json
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

def analyze_rss_for_duplicates():
    """Analyze RSS feed to create reference for duplicate detection"""
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
    
    # Extract episode information
    episodes = {}
    titles_map = {}  # For finding potential duplicates by title
    
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
        
        if guid:
            # Normalize title for duplicate detection (remove common variations)
            title_normalized = title.lower().strip()
            title_normalized = title_normalized.replace(":", "").replace(" - ", " ")
            
            episodes[guid] = {
                'guid': guid,
                'title': title,
                'title_normalized': title_normalized,
                'audio_url': audio_url,
                'pub_date': pub_date,
                'has_audio': has_audio
            }
            
            # Track titles for duplicate detection
            if title_normalized not in titles_map:
                titles_map[title_normalized] = []
            titles_map[title_normalized].append(guid)
    
    # Find potential duplicates by title
    potential_duplicates = {norm_title: guids for norm_title, guids in titles_map.items() if len(guids) > 1}
    
    print("=" * 80)
    print("📊 RSS FEED ANALYSIS FOR DUPLICATE DETECTION")
    print("=" * 80)
    print()
    print(f"Total unique GUIDs in RSS feed: {len(episodes)}")
    print()
    
    if potential_duplicates:
        print("⚠️  POTENTIAL DUPLICATES IN RSS FEED (by title similarity):")
        print("-" * 80)
        for norm_title, guids in potential_duplicates.items():
            print(f"\nTitle: {episodes[guids[0]]['title']}")
            print(f"  Found {len(guids)} GUID(s):")
            for guid in guids:
                ep = episodes[guid]
                print(f"    - {guid}")
                print(f"      Published: {ep['pub_date']}")
                print(f"      Audio: {'✅' if ep['has_audio'] else '❌'}")
        print()
    else:
        print("✅ No duplicate titles found in RSS feed")
        print()
    
    print("=" * 80)
    print("📋 REFERENCE: ALL VALID EPISODES")
    print("=" * 80)
    print()
    print("These are the ONLY episodes that should be in your YouTube playlist:")
    print()
    
    # Sort by publication date
    sorted_episodes = sorted(episodes.values(), key=lambda x: x['pub_date'], reverse=True)
    
    for i, ep in enumerate(sorted_episodes, 1):
        print(f"{i:3d}. GUID: {ep['guid']:30s} | {ep['title'][:45]}")
    
    print()
    print("=" * 80)
    print("💡 HOW TO IDENTIFY DUPLICATES IN YOUTUBE PLAYLIST")
    print("=" * 80)
    print()
    print("Since your playlist has 111 videos but RSS feed has 73 unique GUIDs:")
    print()
    print("1. DUPLICATE DETECTION METHOD:")
    print("   - Look for videos with identical or very similar titles")
    print("   - Check video descriptions - they may contain GUIDs")
    print("   - Compare publication dates - keep the newest version")
    print()
    print("2. COMMON DUPLICATE PATTERNS:")
    print("   - Same title, different publication dates")
    print("   - Very similar titles (e.g., 'Quantum Computing' vs 'Quantum Computing chip advances')")
    print("   - Videos with old/broken thumbnails (you've already removed these)")
    print()
    print("3. MANUAL CHECKLIST:")
    print("   - For each of the 73 GUIDs above, there should be EXACTLY 1 video in YouTube")
    print("   - If you find 2+ videos with the same GUID (check descriptions), remove duplicates")
    print("   - Remove any video that doesn't match a GUID from the list above")
    print()
    print(f"4. EXPECTED RESULT:")
    print(f"   - YouTube playlist should have exactly {len(episodes)} videos")
    print(f"   - Each video should have a unique GUID matching one from the list above")
    print()
    print("5. TIP FOR YOUTUBE:")
    print("   - Use YouTube's playlist editor to sort by date")
    print("   - This makes it easier to spot duplicates (same titles near each other)")
    print()
    
    # Save to JSON for reference
    output_data = {
        'total_valid_episodes': len(episodes),
        'episodes': sorted_episodes,
        'potential_duplicates_in_rss': len(potential_duplicates),
        'duplicate_titles': {norm_title: guids for norm_title, guids in potential_duplicates.items()}
    }
    
    output_file = "youtube_duplicate_reference.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Reference data saved to: {output_file}")
    print()
    
    return episodes

if __name__ == "__main__":
    analyze_rss_for_duplicates()


