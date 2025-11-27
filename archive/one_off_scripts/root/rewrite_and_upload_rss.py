import os
import xml.etree.ElementTree as ET
from google.cloud import storage
import markdown
import requests

# CONFIGURATION
GCS_KEY = '/home/gdubs/copernicus-web-public/regal-scholar-453620-r7-b4a72581927b.json'
BUCKET = 'regal-scholar-453620-r7-podcast-storage'
FEED_BLOB = 'feeds/copernicus-final-rss-feed.xml'
SHOW_IMAGE = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/images/copernicus-original-portrait-optimized.jpg'
AUDIO_PREFIX = 'audio/'
DESC_PREFIX = 'descriptions/'
THUMB_PREFIX = 'thumbnails/'

def get_gcs_client():
    return storage.Client.from_service_account_json(GCS_KEY)

def download_blob_as_text(bucket, blob_name):
    blob = bucket.blob(blob_name)
    return blob.download_as_text()

def upload_blob_from_text(bucket, blob_name, text):
    blob = bucket.blob(blob_name)
    blob.upload_from_string(text, content_type='application/xml')
    print(f"Uploaded updated feed to gs://{BUCKET}/{blob_name}")

def blob_exists(bucket, blob_name):
    return storage.Blob(bucket=bucket, name=blob_name).exists(get_gcs_client())

def get_blob_url(blob_name):
    return f"https://storage.googleapis.com/{BUCKET}/{blob_name}"

def main():
    client = get_gcs_client()
    bucket = client.bucket(BUCKET)
    print("Downloading RSS feed...")
    feed_xml = download_blob_as_text(bucket, FEED_BLOB)

    # Complete episode titles with proper short titles for RSS/Spotify
    EPISODE_TITLES = {
        # Biology Evergreen Series (7 episodes)
        "ever-bio-250006": "CRISPR Chemistry: Molecular Editing",
        "ever-bio-250007": "CRISPR Epigenome: Beyond DNA", 
        "ever-bio-250014": "Minimal Cells: Life's Essentials",
        "ever-bio-250016": "Neural Optogenetics: Light-Controlled Brains",
        "ever-bio-250018": "Organoids: Miniature Organs",
        "ever-bio-250020": "Spatial Biology: Cell Mapping",
        "ever-bio-250028": "Synthetic Biology: Redesigning Life",
        # Chemistry Evergreen Series (4 episodes)
        "ever-chem-250002": "Catalysis Revolution: Transforming Reactions",
        "ever-chem-250005": "Computational Chemistry: Molecular Modeling",
        "ever-chem-250010": "Green Chemistry: Sustainable Synthesis", 
        "ever-chem-250015": "Molecular Machines: Nanoscale Engineering",
        # Computer Science Evergreen Series (3 episodes)
        "ever-compsci-250008": "Edge Computing: Intelligence at the Frontier",
        "ever-compsci-250017": "Neuromorphic Computing: Brain-Inspired Systems",
        "ever-compsci-250024": "Artificial General Intelligence: Promise & Challenges",
        # Mathematics Evergreen Series (8 episodes)
        "ever-math-250009": "Mathematical Logic: 2024 Breakthroughs",
        "ever-math-250011": "Gödel's Incompleteness: Truth's Limits", 
        "ever-math-250012": "Independence in Peano Arithmetic",
        "ever-math-250023": "Continuum Hypothesis: Set Theory's Mystery",
        "ever-math-250025": "Gödel's Incompleteness: Mathematical Truth",
        "ever-math-250029": "Poincaré Conjecture: Century-Long Journey",
        "ever-math-250031": "Independence in Peano Arithmetic",
        "ever-math-250032": "Mathematical Logic: Recent Breakthroughs",
        # Physics Evergreen Series (6 episodes)
        "ever-phys-250019": "Quantum Machine Learning: AI Meets Quantum",
        "ever-phys-250021": "String Theory: Theory of Everything",
        "ever-phys-250022": "Higgs Boson: Hunt for God Particle", 
        "ever-phys-250026": "Quantum Entanglement: Spooky Action",
        "ever-phys-250027": "Quantum Cryptography: Secure Communication",
        "ever-phys-250030": "Quantum Batteries: Future Energy Storage",
        # News Series (date-based canonical IDs)
        "news-bio-28032025": "Biology News 28032025",
        "news-chem-28032025": "Chemistry News 28032025",
        "news-compsci-28032025": "Computer Science News 28032025",
        "news-math-28032025": "Mathematics News 28032025",
        "news-phys-28032025": "Physics News 28032025"
    }
    # Reverse mapping: title to ID
    TITLE_TO_ID = {v: k for k, v in EPISODE_TITLES.items()}

    # Parse XML
    ET.register_namespace('itunes', "http://www.itunes.com/dtds/podcast-1.0.dtd")
    tree = ET.ElementTree(ET.fromstring(feed_xml))
    root = tree.getroot()
    channel = root.find('channel')

    # Update show-level image
    for tag in ['{http://www.itunes.com/dtds/podcast-1.0.dtd}image', 'image']:
        for elem in channel.findall(tag):
            channel.remove(elem)
    itunes_image = ET.Element('{http://www.itunes.com/dtds/podcast-1.0.dtd}image')
    itunes_image.set('href', SHOW_IMAGE)
    channel.insert(0, itunes_image)
    image = ET.Element('image')
    url = ET.SubElement(image, 'url')
    url.text = SHOW_IMAGE
    title = ET.SubElement(image, 'title')
    title.text = 'Copernicus AI Podcast'
    link = ET.SubElement(image, 'link')
    link.text = 'https://www.copernicusai.fyi'
    channel.insert(1, image)
    # Add show-level itunes:summary, itunes:author, itunes:type
    ns = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
    summary_elem = ET.Element(f'{ns}summary')
    summary_elem.text = 'Educational podcast covering the latest breakthroughs in science, technology, mathematics, and research. Join us as we explore cutting-edge discoveries and their implications for the future.'
    channel.append(summary_elem)
    author_elem = ET.Element(f'{ns}author')
    author_elem.text = 'Copernicus AI'
    channel.append(author_elem)
    type_elem = ET.Element(f'{ns}type')
    type_elem.text = 'episodic'
    channel.append(type_elem)

    # Process each episode
    guid_set = set()
    duplicate_guids = set()
    # Remove all existing items
    for item in list(channel.findall('item')):
        channel.remove(item)
    # Add only canonical, complete episodes
    for eid, title in EPISODE_TITLES.items():
        audio_blob = f"{AUDIO_PREFIX}{eid}.mp3"
        desc_blob = f"{DESC_PREFIX}{eid}.md"
        thumb_blob = f"{THUMB_PREFIX}{eid}-thumb.jpg"
        thumb_blob_webp = f"{THUMB_PREFIX}{eid}-thumb.webp"
        # Check all files exist
        if not (blob_exists(bucket, audio_blob) and blob_exists(bucket, desc_blob) and (blob_exists(bucket, thumb_blob) or blob_exists(bucket, thumb_blob_webp))):
            print(f"SKIP: {eid} - missing file(s)")
            continue
        # Build new item
        item = ET.Element('item')
        # Title
        title_elem = ET.SubElement(item, 'title')
        title_elem.text = title
        # Enclosure
        audio_url = get_blob_url(audio_blob)
        enclosure = ET.SubElement(item, 'enclosure')
        enclosure.set('url', audio_url)
        enclosure.set('type', 'audio/mpeg')
        # Add enclosure length (file size in bytes)
        audio_blob_obj = bucket.blob(audio_blob)
        audio_blob_obj.reload()
        enclosure.set('length', str(audio_blob_obj.size or 1))
        # GUID
        guid_elem = ET.SubElement(item, 'guid')
        guid_elem.text = audio_url
        # Description
        desc_md = download_blob_as_text(bucket, desc_blob)
        desc_html = markdown.markdown(desc_md)
        # Truncate HTML description to 4000 chars for Spotify, preserving hashtags/references at end
        def truncate_preserve_tags(html, maxlen=4000):
            if len(html) <= maxlen:
                return html
            # Try to preserve hashtags/references at the end (find last # or link)
            last_hash = html.rfind('#', maxlen-500)
            last_ref = html.rfind('http', maxlen-500)
            cut = max(last_hash, last_ref, maxlen-500)
            if cut > 0:
                return html[:cut].rstrip() + '...'
            return html[:maxlen].rstrip() + '...'
        desc_html_trunc = truncate_preserve_tags(desc_html, 4000)
        # Plain text version for <description>
        import re
        plain_text = re.sub('<[^<]+?>', '', desc_html)
        plain_text_trunc = truncate_preserve_tags(plain_text, 4000)
        # <description>: plain text summary (first 4000 chars, no HTML)
        desc_elem = ET.SubElement(item, 'description')
        desc_elem.text = plain_text_trunc
        # <content:encoded>: full HTML, truncated to 4000 chars if needed
        content_ns = '{http://purl.org/rss/1.0/modules/content/}'
        content_elem = ET.SubElement(item, f'{content_ns}encoded')
        content_elem.text = desc_html_trunc
        # Thumbnail
        ns = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
        canonical_thumb_url = get_blob_url(f"thumbnails/{eid}-thumb.jpg") if blob_exists(bucket, f"thumbnails/{eid}-thumb.jpg") else get_blob_url(f"thumbnails/{eid}-thumb.webp")
        it_img = ET.SubElement(item, f'{ns}image')
        it_img.set('href', canonical_thumb_url)
        # <itunes:duration>
        duration_elem = ET.SubElement(item, f'{ns}duration')
        duration_elem.text = 'Unknown'
        # <pubDate> from audio file's updated time
        import datetime
        dt = audio_blob_obj.updated
        if dt:
            pubdate_elem = ET.SubElement(item, 'pubDate')
            pubdate_elem.text = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
        # <link> canonical episode URL
        link_elem = ET.SubElement(item, 'link')
        link_elem.text = f'https://www.copernicusai.fyi/episodes/{eid}'
        # <itunes:summary>: plain text summary (same as <description>, no HTML)
        itunes_summary = ET.SubElement(item, f'{ns}summary')
        itunes_summary.text = plain_text_trunc if plain_text_trunc else 'Educational podcast covering the latest breakthroughs in science, technology, mathematics, and research. Join us as we explore cutting-edge discoveries and their implications for the future.'
        # <itunes:author>
        itunes_author = ET.SubElement(item, f'{ns}author')
        itunes_author.text = 'Copernicus AI'
        # Add to channel
        channel.append(item)
        print(f"INCLUDE: {eid} - {title}")
    if duplicate_guids:
        print(f"WARNING: Duplicate GUIDs found: {duplicate_guids}")
    else:
        print("All GUIDs are unique.")

    # Write back to string
    new_feed_xml = ET.tostring(root, encoding='unicode')
    upload_blob_from_text(bucket, FEED_BLOB, new_feed_xml)

    # Validate feed
    print("Validating feed...")
    validator_url = f"https://castfeedvalidator.com/?url={get_blob_url(FEED_BLOB)}"
    print(f"Check your feed here: {validator_url}")

if __name__ == '__main__':
    main()