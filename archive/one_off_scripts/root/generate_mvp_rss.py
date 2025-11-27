import csv
import xml.etree.ElementTree as ET
import datetime
import os
from google.cloud import storage
import markdown2
import re

# RSS feed metadata
FEED_TITLE = 'Copernicus AI: Frontiers of Research'
FEED_DESCRIPTION = 'Educational podcast covering the latest breakthroughs in science, technology, mathematics, and research.'
FEED_LINK = 'https://copernicusai.fyi'
AUDIO_BASE_URL = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/'

# Create root RSS structure
def generate_rss(csv_path, output_path):
    root = ET.Element('rss', {
        'version': '2.0',
        'xmlns:itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'xmlns:atom': 'http://www.w3.org/2005/Atom',
        'xmlns:podcast': 'https://podcastindex.org/namespace/1.0',
        'xmlns:content': 'http://purl.org/rss/1.0/modules/content/'
    })
    channel = ET.SubElement(root, 'channel')
    # PSP-1: itunes:explicit MUST be first
    ET.SubElement(channel, 'itunes:explicit').text = 'no'
    # Atom self-link for standards compliance
    ET.SubElement(channel, 'atom:link', {
        'href': 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml',
        'rel': 'self',
        'type': 'application/rss+xml'
    })
    # Guarantee podcast namespace usage
    ET.SubElement(channel, '{https://podcastindex.org/namespace/1.0}locked').text = 'no'
    ET.SubElement(channel, 'title').text = FEED_TITLE
    ET.SubElement(channel, 'description').text = FEED_DESCRIPTION
    ET.SubElement(channel, 'link').text = FEED_LINK
    ET.SubElement(channel, 'language').text = 'en-us'
    # Add itunes:category with subcategory
    science_cat = ET.SubElement(channel, 'itunes:category', {'text': 'Science'})
    ET.SubElement(science_cat, 'itunes:category', {'text': 'Physics'})
    ET.SubElement(channel, 'itunes:author').text = 'CopernicusAI'
    ET.SubElement(channel, 'itunes:summary').text = FEED_DESCRIPTION
    ET.SubElement(channel, 'itunes:type').text = 'episodic'
    ET.SubElement(channel, 'copyright').text = 'Copyright 2025 CopernicusAI. All rights reserved.'
    # iTunes owner info
    itunes_owner = ET.SubElement(channel, 'itunes:owner')
    itunes_owner_name = 'Gary Welz'
    itunes_owner_email = 'garywelz@gmail.com'
    ET.SubElement(itunes_owner, 'itunes:name').text = itunes_owner_name if itunes_owner_name else 'CopernicusAI'
    ET.SubElement(itunes_owner, 'itunes:email').text = itunes_owner_email if itunes_owner_email else 'team@copernicusai.fyi'
    # Add podcast cover image (itunes:image and <image> tags)
    ET.SubElement(channel, 'itunes:image', href='https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg')
    image_tag = ET.SubElement(channel, 'image')
    ET.SubElement(image_tag, 'url').text = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg'
    ET.SubElement(image_tag, 'title').text = FEED_TITLE
    ET.SubElement(image_tag, 'link').text = FEED_LINK

    # Set up GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket('regal-scholar-453620-r7-podcast-storage')

    guid_set = set()
    title_set = set()
    itunes_author = 'CopernicusAI'
    with open(csv_path, newline='') as csvfile:
        rdr = csv.reader(csvfile)
        for row in rdr:
            # Skip headers/section rows and invalid rows
            if (not row or len(row) < 1 or not row[0].strip() or row[0].startswith('Copernicus') or row[0] in ['File Name','Biology','Chemistry','Computer Science','Mathematics','Physics','News']):
                continue
            try:
                fname, title, duration = row[:3]
            except ValueError:
                continue
            fname = fname.strip()
            title = title.strip() if title else ''
            duration = duration.strip() if duration else ''
            # Strict: Only emit episodes with BOTH filename and title
            if not fname or not title:
                continue
            # GUID logic: skip if already used
            if fname in guid_set:
                continue
            guid_set.add(fname)
            # Title fallback and uniqueness
            if not title:
                title = fname
            orig_title = title
            suffix = 2
            while title in title_set:
                title = f"{orig_title} ({suffix})"
                suffix += 1
            title_set.add(title)
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = title
            # Link (per-episode URL)
            ET.SubElement(item, 'link').text = f'{FEED_LINK}/episodes/{fname}'
            desc_blob = bucket.blob(f'descriptions/{fname}.md')
            try:
                desc_markdown = desc_blob.download_as_text()
                desc_html = markdown2.markdown(desc_markdown)
            except Exception:
                desc_html = f'<p>{title} (Duration: {duration})</p>'
            # Always write description
            ET.SubElement(item, 'description').text = desc_html
            # itunes:summary (first 200 chars of description, plain text)
            def html_to_text(html):
                return re.sub('<[^<]+?>', '', html)
            summary_text = html_to_text(desc_html)[:200] if desc_html else title
            ET.SubElement(item, 'itunes:summary').text = summary_text if summary_text else title
            # content:encoded (full HTML)
            content_encoded = ET.SubElement(item, '{http://purl.org/rss/1.0/modules/content/}encoded')
            content_encoded.text = desc_html if desc_html else title
            # itunes:author
            ET.SubElement(item, 'itunes:author').text = itunes_author
            audio_url = f'{AUDIO_BASE_URL}{fname}.mp3'
            try:
                audio_blob = bucket.blob(f'audio/{fname}.mp3')
                enclosure_length = str(audio_blob.size)
            except Exception:
                enclosure_length = '1'  # Use '1' as placeholder if audio file missing or size unavailable
            ET.SubElement(item, 'enclosure', url=audio_url, type='audio/mpeg', length=enclosure_length)
            # GUID: use canonical filename
            ET.SubElement(item, 'guid').text = fname
            pub_date = datetime.datetime.now().strftime('%a, %d %b %Y 00:00:00 GMT')
            ET.SubElement(item, 'pubDate').text = pub_date
            thumb_url = f'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/{fname}-thumbnail.jpg'
            ET.SubElement(item, 'itunes:image', href=thumb_url)
            # itunes:duration (default to 0:00 if missing)
            ET.SubElement(item, 'itunes:duration').text = duration if duration else '0:00'
            ET.SubElement(item, 'itunes:explicit').text = 'no'

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    generate_rss('Copernicus AI Canonical List 071825.csv', 'copernicus-mvp-rss-feed.xml')
