#!/usr/bin/env python3
"""
Extract Podcasts from RSS Feed

Extracts podcast metadata from RSS feed and converts to unified schema format.
Source: Google Cloud Storage RSS feed, not local files.
"""

import json
import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from urllib.parse import urlparse

# RSS feed URL
RSS_FEED_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml"

def parse_rss_feed(rss_content: str) -> List[Dict]:
    """
    Parse RSS feed XML and extract podcast items.
    Returns list of podcast dictionaries.
    """
    root = ET.fromstring(rss_content)
    
    # Namespace map
    namespaces = {
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'media': 'http://search.yahoo.com/mrss/',
        'atom': 'http://www.w3.org/2005/Atom'
    }
    
    # Find channel
    channel = root.find('channel')
    if channel is None:
        return []
    
    # Find all items
    items = channel.findall('item')
    podcasts = []
    
    for item in items:
        podcast = {}
        
        # Title
        title_elem = item.find('title')
        if title_elem is not None and title_elem.text:
            podcast['title'] = title_elem.text
        
        # GUID
        guid_elem = item.find('guid')
        if guid_elem is not None:
            guid = guid_elem.text
            podcast['guid'] = guid
            podcast['id'] = f"podcast_{guid}"
        
        # Description
        desc_elem = item.find('description')
        if desc_elem is not None and desc_elem.text:
            podcast['description'] = desc_elem.text
        
        # Content (encoded)
        content_elem = item.find('content:encoded', namespaces)
        if content_elem is not None and content_elem.text:
            podcast['content'] = content_elem.text
        
        # Link
        link_elem = item.find('link')
        if link_elem is not None and link_elem.text:
            podcast['url'] = link_elem.text
        
        # Audio URL (enclosure)
        enclosure = item.find('enclosure')
        if enclosure is not None:
            audio_url = enclosure.get('url')
            if audio_url:
                podcast['audioUrl'] = audio_url
                # Extract file size
                length = enclosure.get('length')
                if length:
                    try:
                        podcast['fileSize'] = int(length)
                    except:
                        pass
        
        # Thumbnail (itunes:image or media:thumbnail)
        image_elem = item.find('itunes:image', namespaces)
        if image_elem is not None:
            image_url = image_elem.get('href')
            if image_url:
                podcast['thumbnailUrl'] = image_url
        
        if 'thumbnailUrl' not in podcast:
            thumb_elem = item.find('media:thumbnail', namespaces)
            if thumb_elem is not None:
                thumb_url = thumb_elem.get('url')
                if thumb_url:
                    podcast['thumbnailUrl'] = thumb_url
        
        # Duration
        duration_elem = item.find('itunes:duration', namespaces)
        if duration_elem is not None and duration_elem.text:
            podcast['duration'] = duration_elem.text
            # Parse duration to seconds
            try:
                duration_str = duration_elem.text
                parts = duration_str.split(':')
                if len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    podcast['duration_seconds'] = hours * 3600 + minutes * 60 + seconds
                elif len(parts) == 2:
                    minutes, seconds = map(int, parts)
                    podcast['duration_seconds'] = minutes * 60 + seconds
            except:
                pass
        
        # Publication date
        pubdate_elem = item.find('pubDate')
        if pubdate_elem is not None and pubdate_elem.text:
            podcast['published_date'] = pubdate_elem.text
            # Parse date to get year
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pubdate_elem.text)
                podcast['year'] = str(dt.year)
                podcast['published_date_iso'] = dt.isoformat() + 'Z'
            except:
                pass
        
        # Category
        category_elem = item.find('category')
        if category_elem is not None and category_elem.text:
            category = category_elem.text.lower()
            # Map to our categories
            category_map = {
                'physics': 'physics',
                'biology': 'biology',
                'chemistry': 'chemistry',
                'mathematics': 'mathematics',
                'math': 'mathematics',
                'computer science': 'computer_science',
                'cs': 'computer_science',
                'technology': 'computer_science'
            }
            podcast['category'] = category_map.get(category, 'interdisciplinary')
        else:
            # Try to infer from guid or title
            guid_lower = podcast.get('guid', '').lower()
            if 'bio' in guid_lower:
                podcast['category'] = 'biology'
            elif 'chem' in guid_lower:
                podcast['category'] = 'chemistry'
            elif 'phys' in guid_lower:
                podcast['category'] = 'physics'
            elif 'math' in guid_lower:
                podcast['category'] = 'mathematics'
            elif 'compsci' in guid_lower or 'cs' in guid_lower:
                podcast['category'] = 'computer_science'
            else:
                podcast['category'] = 'interdisciplinary'
        
        # Episode number
        episode_elem = item.find('itunes:episode', namespaces)
        if episode_elem is not None and episode_elem.text:
            try:
                podcast['episode'] = int(episode_elem.text)
            except:
                pass
        
        # Season
        season_elem = item.find('itunes:season', namespaces)
        if season_elem is not None and season_elem.text:
            try:
                podcast['season'] = int(season_elem.text)
            except:
                pass
        
        # Extract references from description/content
        references = extract_references(podcast.get('description', '') + ' ' + podcast.get('content', ''))
        if references:
            podcast['references'] = references
        
        # Extract keywords/tags from description
        keywords = extract_keywords(podcast.get('description', ''))
        if keywords:
            podcast['keywords'] = keywords
        
        # Add required fields for unified schema
        podcast['source'] = 'copernicus_ai'
        podcast['acquired_date'] = datetime.now().isoformat() + 'Z'
        podcast['subcategories'] = []
        podcast['related_papers'] = []
        podcast['related_videos'] = []
        podcast['related_processes'] = []
        podcast['related_podcasts'] = []
        
        podcasts.append(podcast)
    
    return podcasts

def extract_references(text: str) -> List[Dict]:
    """Extract paper references from text."""
    references = []
    
    # Look for DOI patterns
    doi_pattern = r'10\.\d{4,}/[^\s\)]+'
    dois = re.findall(doi_pattern, text)
    for doi in dois:
        references.append({
            'doi': doi,
            'url': f'https://doi.org/{doi}',
            'paper_id': f'crossref_{doi.replace("/", "_").replace(".", "_")}'
        })
    
    # Look for PubMed IDs
    pubmed_pattern = r'PMID[:\s]+(\d+)'
    pubmed_ids = re.findall(pubmed_pattern, text, re.IGNORECASE)
    for pmid in pubmed_ids:
        references.append({
            'pmid': pmid,
            'url': f'https://pubmed.ncbi.nlm.nih.gov/{pmid}',
            'paper_id': f'pubmed_{pmid}'
        })
    
    # Look for arXiv IDs
    arxiv_pattern = r'arxiv[:\s]+(\d{4}\.\d{4,5})'
    arxiv_ids = re.findall(arxiv_pattern, text, re.IGNORECASE)
    for arxiv_id in arxiv_ids:
        references.append({
            'arxiv_id': arxiv_id,
            'url': f'https://arxiv.org/abs/{arxiv_id}',
            'paper_id': f'arxiv_{arxiv_id}'
        })
    
    return references

def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text (hashtags, etc.)."""
    keywords = []
    
    # Extract hashtags
    hashtag_pattern = r'#(\w+)'
    hashtags = re.findall(hashtag_pattern, text)
    keywords.extend(hashtags)
    
    return list(set(keywords))  # Deduplicate

def main():
    """Main function."""
    import argparse
    import requests
    
    parser = argparse.ArgumentParser(description="Extract podcasts from RSS feed")
    parser.add_argument("--rss-url", default=RSS_FEED_URL, help="RSS feed URL")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()
    
    print("=" * 70)
    print("Extract Podcasts from RSS Feed")
    print("=" * 70)
    print(f"RSS Feed: {args.rss_url}")
    print()
    
    try:
        # Fetch RSS feed
        print("📥 Fetching RSS feed...")
        response = requests.get(args.rss_url, timeout=30)
        response.raise_for_status()
        rss_content = response.text
        print(f"✅ Fetched RSS feed ({len(rss_content)} bytes)")
        print()
        
        # Parse RSS feed
        print("📝 Parsing RSS feed...")
        podcasts = parse_rss_feed(rss_content)
        print(f"✅ Found {len(podcasts)} podcasts")
        print()
        
        # Show summary
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        
        # Count by category
        categories = {}
        for podcast in podcasts:
            cat = podcast.get('category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"Total Podcasts: {len(podcasts)}")
        print("\nBy Category:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
        
        print()
        print("Sample Podcasts:")
        for i, podcast in enumerate(podcasts[:5], 1):
            print(f"  [{i}] {podcast.get('title', 'Unknown')} (ID: {podcast.get('id', 'unknown')})")
            print(f"      Category: {podcast.get('category', 'unknown')}")
            if 'references' in podcast and podcast['references']:
                print(f"      References: {len(podcast['references'])}")
        
        # Output
        if args.output:
            print()
            print(f"💾 Saving to {args.output}...")
            with open(args.output, 'w') as f:
                json.dump(podcasts, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(podcasts)} podcasts to {args.output}")
        elif args.json:
            print()
            print(json.dumps(podcasts, indent=2, ensure_ascii=False))
        else:
            print()
            print("💡 Use --output to save podcasts to JSON file")
            print("   Example: --output podcasts_from_rss.json")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
