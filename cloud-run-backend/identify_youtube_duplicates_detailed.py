"""
Detailed script to help identify duplicate videos in YouTube playlist
Provides comparison tools and potential duplicate detection
"""

import json
import re
from google.cloud import storage
from xml.etree import ElementTree as ET
from html import unescape
from config.constants import RSS_BUCKET_NAME, RSS_FEED_BLOB_NAME

def normalize_title(title):
    """Normalize title for comparison (remove punctuation, lowercase, etc.)"""
    if not title:
        return ""
    # Lowercase
    normalized = title.lower()
    # Remove common punctuation
    normalized = re.sub(r'[:\-—–]', ' ', normalized)
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    # Strip
    normalized = normalized.strip()
    return normalized

def extract_guid_from_text(text):
    """Extract GUID from text (might be in descriptions)"""
    if not text:
        return None
    # Look for ever-XXX-XXXXXX or news-XXX-XXXXXX patterns
    patterns = [
        r'(ever-[a-z]+-\d+)',
        r'(news-[a-z]+-\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return None

def analyze_for_duplicates():
    """Analyze RSS feed and create tools for duplicate detection"""
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
    
    # Build reference data
    episodes_by_guid = {}
    episodes_by_title = {}
    title_normalized_map = {}
    
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
            title_norm = normalize_title(title)
            
            episodes_by_guid[guid] = {
                'guid': guid,
                'title': title,
                'title_normalized': title_norm,
                'audio_url': audio_url,
                'pub_date': pub_date
            }
            
            # Track by normalized title for duplicate detection
            if title_norm not in episodes_by_title:
                episodes_by_title[title_norm] = []
            episodes_by_title[title_norm].append(guid)
            
            title_normalized_map[guid] = title_norm
    
    print("=" * 80)
    print("📊 YOUTUBE DUPLICATE DETECTION TOOL")
    print("=" * 80)
    print()
    print(f"RSS Feed contains {len(episodes_by_guid)} unique episodes")
    print(f"Your YouTube playlist has 111 videos")
    print(f"Target: 73 videos (should be {len(episodes_by_guid)} after adding missing episode)")
    print()
    
    # Find episodes with similar titles
    print("=" * 80)
    print("⚠️  POTENTIAL DUPLICATES (Similar Titles in RSS Feed)")
    print("=" * 80)
    print()
    
    similar_titles_found = False
    for title_norm, guids in episodes_by_title.items():
        if len(guids) > 1:
            similar_titles_found = True
            print(f"Title: '{episodes_by_guid[guids[0]]['title']}'")
            print(f"  Found {len(guids)} episode(s) with similar title:")
            for guid in guids:
                ep = episodes_by_guid[guid]
                print(f"    - {guid}: Published {ep['pub_date']}")
            print()
    
    if not similar_titles_found:
        print("✅ No duplicate titles found in RSS feed")
        print()
    
    # Special case: Quantum Error Correction episodes
    print("=" * 80)
    print("🔍 SPECIAL CASE: Quantum Error Correction Episodes")
    print("=" * 80)
    print()
    
    qec_episodes = [ep for guid, ep in episodes_by_guid.items() if 'quantum error correction' in ep['title_normalized']]
    if qec_episodes:
        print(f"Found {len(qec_episodes)} Quantum Error Correction episode(s):")
        for ep in qec_episodes:
            print(f"  - {ep['guid']}: {ep['title']}")
            print(f"    Published: {ep['pub_date']}")
        print()
        print("⚠️  These have very similar titles - check YouTube for duplicates!")
        print()
    
    # Create comparison checklist
    print("=" * 80)
    print("📋 MANUAL CHECKLIST FOR YOUTUBE PLAYLIST")
    print("=" * 80)
    print()
    print("For each video in your YouTube playlist:")
    print()
    print("STEP 1: Find the GUID")
    print("  - Check video description for GUID (format: ever-XXX-XXXXXX or news-XXX-XXXXXX)")
    print("  - GUID might appear in description text or metadata")
    print()
    print("STEP 2: Compare with RSS Feed")
    print("  - If GUID matches one below → KEEP (if it's the only video with that GUID)")
    print("  - If GUID matches but there's another video with same GUID → Remove duplicate")
    print("  - If GUID doesn't match any below → REMOVE")
    print("  - If no GUID found → Check title similarity with list below")
    print()
    
    # Print all valid GUIDs
    print("=" * 80)
    print("✅ VALID GUIDs (Should be in YouTube - exactly one video per GUID)")
    print("=" * 80)
    print()
    
    # Sort by publication date
    sorted_episodes = sorted(episodes_by_guid.values(), key=lambda x: x['pub_date'], reverse=True)
    
    for i, ep in enumerate(sorted_episodes, 1):
        print(f"{i:3d}. {ep['guid']:30s} | {ep['title'][:45]}")
    
    print()
    print("=" * 80)
    print("📝 DUPLICATE DETECTION STRATEGY")
    print("=" * 80)
    print()
    print("Since you have 111 videos but should have 73:")
    print()
    print("1. GROUP BY TITLE:")
    print("   - Sort YouTube playlist by title")
    print("   - Look for videos with identical or very similar titles")
    print("   - Compare their publication dates - keep the newest")
    print()
    print("2. GROUP BY DESCRIPTION:")
    print("   - Videos from RSS feeds often have GUIDs in descriptions")
    print("   - If two videos have the same GUID → Remove duplicate (keep newest)")
    print()
    print("3. COMMON PATTERNS TO LOOK FOR:")
    print("   - 'Quantum Error Correction' (2 similar episodes - check GUIDs carefully)")
    print("   - 'Quantum Computing' (multiple episodes - verify they're different)")
    print("   - Videos with old/broken thumbnails (you've already removed many)")
    print("   - News episodes (news-bio, news-chem, etc. - should be exactly 5)")
    print()
    print("4. VERIFICATION:")
    print("   - After cleanup, you should have exactly 73 videos")
    print("   - Each video should correspond to one GUID from the list above")
    print("   - No duplicate GUIDs")
    print()
    
    # Save reference data
    output_data = {
        'total_valid_episodes': len(episodes_by_guid),
        'current_youtube_count': 111,
        'target_count': len(episodes_by_guid),
        'videos_to_remove': 111 - len(episodes_by_guid),
        'episodes': sorted_episodes,
        'guids_list': [ep['guid'] for ep in sorted_episodes],
        'similar_titles_in_rss': {title: guids for title, guids in episodes_by_title.items() if len(guids) > 1}
    }
    
    output_file = "youtube_duplicate_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Analysis saved to: {output_file}")
    print()
    print("=" * 80)
    print("💡 NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Use the GUID list above to verify each YouTube video")
    print("2. Remove videos that don't match any GUID")
    print("3. Remove duplicate videos (same GUID, keep newest)")
    print("4. Final count should be exactly 73 videos")
    print()
    
    return episodes_by_guid

if __name__ == "__main__":
    analyze_for_duplicates()


