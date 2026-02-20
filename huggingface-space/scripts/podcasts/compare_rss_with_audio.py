#!/usr/bin/env python3
"""
Compare RSS Feed with Audio Files

Compares RSS feed podcasts with audio files in GCS to identify:
1. Podcasts in RSS feed (79)
2. Audio files not in RSS feed (potential missing podcasts)
3. Audio files that should be archived (unwanted)
"""

import json
import sys
import re
import subprocess
from typing import Dict, List, Set
import requests
import xml.etree.ElementTree as ET

# RSS feed URL
RSS_FEED_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml"
AUDIO_BUCKET = "gs://regal-scholar-453620-r7-podcast-storage/audio/"

def get_rss_guids() -> Set[str]:
    """Get GUIDs from RSS feed."""
    print("📥 Fetching RSS feed...")
    response = requests.get(RSS_FEED_URL, timeout=30)
    response.raise_for_status()
    rss_content = response.text
    
    # Parse RSS
    root = ET.fromstring(rss_content)
    channel = root.find('channel')
    if channel is None:
        return set()
    
    items = channel.findall('item')
    guids = set()
    
    for item in items:
        guid_elem = item.find('guid')
        if guid_elem is not None and guid_elem.text:
            guids.add(guid_elem.text)
    
    return guids

def get_audio_files() -> Set[str]:
    """Get audio file names from GCS bucket."""
    print("📁 Listing audio files in GCS...")
    
    try:
        # Use gsutil to list files
        result = subprocess.run(
            ['gsutil', 'ls', AUDIO_BUCKET],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return set()
        
        # Extract file names (remove path and extension)
        audio_files = set()
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '.mp3' in line:
                # Extract filename: audio/filename.mp3 -> filename
                filename = line.split('/')[-1].replace('.mp3', '')
                audio_files.add(filename)
        
        return audio_files
    
    except Exception as e:
        print(f"Error listing audio files: {e}", file=sys.stderr)
        return set()

def main():
    """Main comparison function."""
    print("=" * 70)
    print("Compare RSS Feed with Audio Files")
    print("=" * 70)
    print()
    
    # Get RSS GUIDs
    rss_guids = get_rss_guids()
    print(f"✅ Found {len(rss_guids)} podcasts in RSS feed")
    print()
    
    # Get audio files
    audio_files = get_audio_files()
    print(f"✅ Found {len(audio_files)} audio files in GCS")
    print()
    
    # Compare
    print("=" * 70)
    print("Comparison Results")
    print("=" * 70)
    print()
    
    # Podcasts in RSS feed (wanted)
    in_rss = rss_guids & audio_files
    print(f"✅ In RSS Feed & GCS (wanted): {len(in_rss)}")
    print()
    
    # Audio files not in RSS feed
    not_in_rss = audio_files - rss_guids
    print(f"📁 In GCS but NOT in RSS Feed: {len(not_in_rss)}")
    
    if not_in_rss:
        print("\nAudio files not in RSS feed:")
        for audio_file in sorted(not_in_rss):
            print(f"  - {audio_file}")
        print()
    
    # Expected: 82 total wanted
    # Current: 79 in RSS feed
    # Missing: 82 - 79 = 3 expected in RSS feed
    # Unwanted: 97 - 82 = 15 expected to archive
    
    print("=" * 70)
    print("Analysis")
    print("=" * 70)
    print(f"Total Audio Files: {len(audio_files)}")
    print(f"In RSS Feed: {len(in_rss)}")
    print(f"Not in RSS Feed: {len(not_in_rss)}")
    print()
    print(f"Expected Total Wanted: 82")
    print(f"Current in RSS Feed: 79")
    print(f"Expected Missing from RSS: ~3")
    print(f"Expected to Archive: ~15")
    print()
    
    if len(not_in_rss) >= 3:
        print("📋 Suggested Missing Podcasts (top 3 candidates to add to RSS):")
        for i, audio_file in enumerate(sorted(not_in_rss)[:3], 1):
            print(f"  [{i}] {audio_file}")
        print()
    
    if len(not_in_rss) > 3:
        remaining = sorted(not_in_rss)[3:]
        print(f"📦 Suggested for Archiving ({len(remaining)} files):")
        for audio_file in remaining:
            print(f"  - {audio_file}")
        print()
    
    # Save comparison to file
    comparison = {
        "rss_feed_count": len(rss_guids),
        "audio_files_count": len(audio_files),
        "in_rss_and_gcs": sorted(list(in_rss)),
        "not_in_rss_feed": sorted(list(not_in_rss)),
        "expected_missing_from_rss": 3,
        "expected_to_archive": 15
    }
    
    output_file = "podcast_comparison.json"
    with open(output_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"💾 Comparison saved to {output_file}")
    print()
    
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"✅ RSS Feed: {len(rss_guids)} podcasts (migrated)")
    print(f"📁 Audio Files: {len(audio_files)} files")
    print(f"📋 Not in RSS: {len(not_in_rss)} files")
    print(f"   - ~3 should be added to RSS feed")
    print(f"   - ~15 should be archived")
    print("=" * 70)

if __name__ == "__main__":
    main()
