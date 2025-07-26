# Alternative RSS generator using lxml for robust namespace and tag emission
import csv
import datetime
from lxml import etree
import markdown2
from google.cloud import storage
import re

FEED_TITLE = "Copernicus AI Podcast"
FEED_DESCRIPTION = "The Copernicus AI Podcast explores the frontiers of science and technology with short, accessible episodes."
FEED_LINK = "https://copernicusai.fyi"
AUDIO_BASE_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/"

NAMESPACES = {
    None: 'http://www.w3.org/2005/Atom',
    'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
    'atom': 'http://www.w3.org/2005/Atom',
    'podcast': 'https://podcastindex.org/namespace/1.0',
    'content': 'http://purl.org/rss/1.0/modules/content/'
}

def generate_rss_lxml(csv_path, output_path):
    NSMAP = {
        'itunes': NAMESPACES['itunes'],
        'atom': NAMESPACES['atom'],
        'podcast': NAMESPACES['podcast'],
        'content': NAMESPACES['content']
    }
    rss = etree.Element('rss', nsmap=NSMAP, version='2.0')
    channel = etree.SubElement(rss, 'channel')
    # PSP-1: itunes:explicit MUST be first
    etree.SubElement(channel, '{%s}explicit' % NAMESPACES['itunes']).text = 'no'
    # Atom self-link
    etree.SubElement(channel, '{%s}link' % NAMESPACES['atom'], href='https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml', rel='self', type='application/rss+xml')
    # Guarantee podcast namespace usage
    etree.SubElement(channel, '{%s}locked' % NAMESPACES['podcast']).text = 'no'
    etree.SubElement(channel, 'title').text = FEED_TITLE
    etree.SubElement(channel, 'description').text = FEED_DESCRIPTION
    etree.SubElement(channel, 'link').text = FEED_LINK
    etree.SubElement(channel, 'language').text = 'en-us'
    # itunes:category with subcategory
    cat = etree.SubElement(channel, '{%s}category' % NAMESPACES['itunes'], text='Science')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Artificial Intelligence')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Biology')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Chemistry')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Computer Science')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Mathematics')
    etree.SubElement(cat, '{%s}category' % NAMESPACES['itunes'], text='Physics')
    etree.SubElement(channel, '{%s}author' % NAMESPACES['itunes']).text = 'CopernicusAI'
    etree.SubElement(channel, '{%s}summary' % NAMESPACES['itunes']).text = FEED_DESCRIPTION
    etree.SubElement(channel, '{%s}type' % NAMESPACES['itunes']).text = 'episodic'
    etree.SubElement(channel, 'copyright').text = 'Copyright 2025 CopernicusAI. All rights reserved.'
    # itunes:owner
    owner = etree.SubElement(channel, '{%s}owner' % NAMESPACES['itunes'])
    etree.SubElement(owner, '{%s}name' % NAMESPACES['itunes']).text = 'Gary Welz'
    etree.SubElement(owner, '{%s}email' % NAMESPACES['itunes']).text = 'garywelz@gmail.com'
    # itunes:image
    etree.SubElement(channel, '{%s}image' % NAMESPACES['itunes'], href='https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg')
    # <image> for RSS
    image_tag = etree.SubElement(channel, 'image')
    etree.SubElement(image_tag, 'url').text = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg'
    etree.SubElement(image_tag, 'title').text = FEED_TITLE
    etree.SubElement(image_tag, 'link').text = FEED_LINK
    # GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket('regal-scholar-453620-r7-podcast-storage')
    guid_set = set()
    title_set = set()
    with open(csv_path, newline='') as csvfile:
        rdr = csv.reader(csvfile)
        for row in rdr:
            # Strict: Only emit episodes with BOTH filename and title
            if not row or len(row) < 2:
                continue
            fname, title = row[0].strip(), row[1].strip()
            duration = row[2].strip() if len(row) > 2 and row[2] else ''
            if not fname or not title or fname in ['File Name','Biology','Chemistry','Mathematics','Computer Science','Physics','News'] or title in ['Title','']:
                continue
            # GUID logic: skip if already used
            if fname in guid_set:
                continue
            guid_set.add(fname)
            # Get season and episode from canonical CSV columns if present
            season = row[4].strip() if len(row) > 4 and row[4] else ''
            episode = row[5].strip() if len(row) > 5 and row[5] else ''

            # Title uniqueness
            orig_title = title
            suffix = 2
            while title in title_set:
                title = f"{orig_title} ({suffix})"
                suffix += 1
            title_set.add(title)
            item = etree.SubElement(channel, 'item')
            etree.SubElement(item, 'title').text = title
            etree.SubElement(item, 'link').text = f'{FEED_LINK}/episodes/{fname}'
            desc_blob = bucket.blob(f'descriptions/{fname}.md')
            try:
                desc_markdown = desc_blob.download_as_text()
                if desc_markdown.strip():
                    desc_html = markdown2.markdown(desc_markdown)
                else:
                    desc_html = '<p>Description coming soon for this episode.</p>'
            except Exception:
                desc_html = '<p>Description coming soon for this episode.</p>'
            etree.SubElement(item, 'description').text = desc_html
            def html_to_text(html):
                return re.sub('<[^<]+?>', '', html)
            summary_text = html_to_text(desc_html).strip()[:200] if desc_html else 'Description coming soon.'
            etree.SubElement(item, '{%s}summary' % NAMESPACES['itunes']).text = summary_text if summary_text else 'Description coming soon.'
            content_encoded = etree.SubElement(item, '{%s}encoded' % NAMESPACES['content'])
            content_encoded.text = desc_html if desc_html else 'Description coming soon.'
            etree.SubElement(item, '{%s}author' % NAMESPACES['itunes']).text = 'CopernicusAI'
            audio_url = f'{AUDIO_BASE_URL}{fname}.mp3'
            file_size = row[3].strip() if len(row) > 3 and row[3] else ''
            enclosure_length = file_size if file_size.isdigit() else '1'
            etree.SubElement(item, 'enclosure', url=audio_url, type='audio/mpeg', length=enclosure_length)
            etree.SubElement(item, 'guid').text = fname
            pub_date = datetime.datetime.now().strftime('%a, %d %b %Y 00:00:00 GMT')
            etree.SubElement(item, 'pubDate').text = pub_date
            thumb_url = f'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{fname}-thumb.jpg'
            etree.SubElement(item, '{%s}image' % NAMESPACES['itunes'], href=thumb_url)
            # Add <media:thumbnail> and <media:content> for maximum compatibility
            media_ns = 'http://search.yahoo.com/mrss/'
            etree.SubElement(item, '{%s}thumbnail' % media_ns, url=thumb_url)
            etree.SubElement(item, '{%s}content' % media_ns, url=thumb_url, medium='image')
            etree.SubElement(item, '{%s}duration' % NAMESPACES['itunes']).text = duration if duration else '0:00'
            etree.SubElement(item, '{%s}explicit' % NAMESPACES['itunes']).text = 'no'
            # Insert season and episode tags if present
            if season:
                etree.SubElement(item, '{%s}season' % NAMESPACES['itunes']).text = season
            if episode:
                etree.SubElement(item, '{%s}episode' % NAMESPACES['itunes']).text = episode
    tree = etree.ElementTree(rss)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)

if __name__ == '__main__':
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'Copernicus AI Canonical List 071825.csv'
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'copernicus-mvp-rss-feed.xml'
    generate_rss_lxml(csv_path, output_path)
