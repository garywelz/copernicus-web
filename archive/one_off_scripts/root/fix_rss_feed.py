#!/usr/bin/env python3
"""
RSS Feed Fix Script
Based on cursor agent analysis to fix podcast feed rejection issues
"""

import xml.etree.ElementTree as ET
import re
import requests
from datetime import datetime, timedelta
import os

def fix_rss_feed():
    """Fix RSS feed issues preventing platform acceptance"""
    
    # Download current RSS feed
    rss_url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml"
    print(f"📥 Downloading RSS feed from: {rss_url}")
    
    response = requests.get(rss_url)
    if response.status_code != 200:
        print(f"❌ Failed to download RSS feed: {response.status_code}")
        return
    
    # Parse XML
    print("🔍 Parsing RSS feed...")
    root = ET.fromstring(response.content)
    
    # Find channel
    channel = root.find('channel')
    if channel is None:
        print("❌ No channel found in RSS feed")
        return
    
    # Track fixes
    fixes_applied = {
        'future_dates': 0,
        'html_cleaned': 0,
        'enclosure_lengths': 0,
        'hashtag_formatting': 0
    }
    
    # Get current date for realistic past dates
    current_date = datetime.now()
    
    # Process each item
    items = channel.findall('item')
    print(f"📋 Processing {len(items)} episodes...")
    
    for i, item in enumerate(items):
        print(f"\n🎧 Processing episode {i+1}/{len(items)}")
        
        # Fix 1: Future publication dates
        pubdate_elem = item.find('pubDate')
        if pubdate_elem is not None:
            try:
                # Parse current date - handle both GMT and other timezone formats
                date_text = pubdate_elem.text.strip()
                
                # Try different date formats
                current_pubdate = None
                for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S GMT']:
                    try:
                        current_pubdate = datetime.strptime(date_text, fmt)
                        break
                    except ValueError:
                        continue
                
                if current_pubdate is None:
                    # If we can't parse, assume it's future and fix it
                    current_pubdate = datetime(2025, 7, 29)  # Default future date
                
                # If date is in the future, set to a realistic past date
                if current_pubdate.year >= 2025 or current_pubdate > current_date:
                    # Set to current date minus (episode number * 7 days) for realistic spacing
                    new_date = current_date - timedelta(days=(i * 7 + 30))  # Start 30 days ago
                    new_pubdate = new_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                    pubdate_elem.text = new_pubdate
                    fixes_applied['future_dates'] += 1
                    print(f"  ✅ Fixed future date: {date_text} → {new_pubdate}")
                    
            except Exception as e:
                print(f"  ⚠️ Could not parse pubDate '{pubdate_elem.text}': {e}")
                # Force fix for unparseable dates
                new_date = current_date - timedelta(days=(i * 7 + 30))
                new_pubdate = new_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
                pubdate_elem.text = new_pubdate
                fixes_applied['future_dates'] += 1
                print(f"  ✅ Force-fixed unparseable date → {new_pubdate}")
        
        # Fix 2: Clean excessive HTML from descriptions
        description_elem = item.find('description')
        if description_elem is not None:
            original_desc = description_elem.text
            if original_desc:
                # Remove complex HTML tags but keep basic formatting
                cleaned_desc = clean_html_description(original_desc)
                if cleaned_desc != original_desc:
                    description_elem.text = cleaned_desc
                    fixes_applied['html_cleaned'] += 1
                    print(f"  ✅ Cleaned HTML from description")
        
        # Fix 3: Clean content:encoded as well
        content_encoded = item.find('.//{http://purl.org/rss/1.0/modules/content/}encoded')
        if content_encoded is not None:
            original_content = content_encoded.text
            if original_content:
                cleaned_content = clean_html_description(original_content)
                if cleaned_content != original_content:
                    content_encoded.text = cleaned_content
                    print(f"  ✅ Cleaned HTML from content:encoded")
        
        # Fix 4: Update enclosure length to match actual file size
        enclosure_elem = item.find('enclosure')
        if enclosure_elem is not None:
            audio_url = enclosure_elem.get('url')
            if audio_url:
                try:
                    # Get actual file size
                    head_response = requests.head(audio_url, timeout=10)
                    if head_response.status_code == 200:
                        actual_size = head_response.headers.get('content-length')
                        if actual_size:
                            current_length = enclosure_elem.get('length', '0')
                            if current_length != actual_size:
                                enclosure_elem.set('length', actual_size)
                                fixes_applied['enclosure_lengths'] += 1
                                print(f"  ✅ Updated enclosure length: {current_length} → {actual_size}")
                except Exception as e:
                    print(f"  ⚠️ Could not verify file size for {audio_url}: {e}")
    
    # Generate fixed RSS feed
    output_file = "/home/gdubs/copernicus-web-public/fixed_rss_feed.xml"
    print(f"\n💾 Saving fixed RSS feed to: {output_file}")
    
    # Write with proper XML declaration
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    
    # Print summary
    print(f"\n📊 FIXES APPLIED:")
    print(f"  🗓️ Future dates corrected: {fixes_applied['future_dates']}")
    print(f"  🧹 HTML descriptions cleaned: {fixes_applied['html_cleaned']}")
    print(f"  📏 Enclosure lengths updated: {fixes_applied['enclosure_lengths']}")
    print(f"  🏷️ Hashtag formatting fixed: {fixes_applied['hashtag_formatting']}")
    
    print(f"\n✅ Fixed RSS feed saved to: {output_file}")
    print(f"📤 Upload this file to replace the current RSS feed at:")
    print(f"   https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml")
    
    return output_file

def clean_html_description(html_content):
    """Clean excessive HTML from description while preserving basic formatting"""
    
    # Convert h1 hashtags to simple text
    html_content = re.sub(r'<h1[^>]*>([^<]+)</h1>', r'\n\nTags: \1', html_content)
    
    # Convert h2, h3 to simple bold text
    html_content = re.sub(r'<h[23][^>]*>([^<]+)</h[23]>', r'\n\n**\1**\n', html_content)
    
    # Convert ordered lists to simple numbered format
    html_content = re.sub(r'<ol[^>]*>', '\n', html_content)
    html_content = re.sub(r'</ol>', '\n', html_content)
    html_content = re.sub(r'<li[^>]*>', '• ', html_content)
    html_content = re.sub(r'</li>', '\n', html_content)
    
    # Keep basic formatting but remove complex tags
    html_content = re.sub(r'</?strong>', '**', html_content)
    html_content = re.sub(r'</?em>', '*', html_content)
    
    # Remove remaining HTML tags except basic ones
    allowed_tags = ['p', 'br', 'a']
    html_content = re.sub(r'<(?!/?(?:' + '|'.join(allowed_tags) + r')\b)[^>]+>', '', html_content)
    
    # Clean up excessive whitespace
    html_content = re.sub(r'\n\s*\n\s*\n', '\n\n', html_content)
    html_content = re.sub(r'&amp;amp;', '&', html_content)
    
    return html_content.strip()

if __name__ == "__main__":
    print("🔧 RSS Feed Fix Script")
    print("=" * 50)
    fix_rss_feed()
