import csv
import datetime
from lxml import etree
import requests

NEWS_LAUNCH_DATE = 'Fri, 28 Mar 2025'
TODAY_DATE = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S -0400')
NEWS_EPISODES = [
    'news-bio-28032025',
    'news-chem-28032025',
    'news-compsci-28032025',
    'news-math-28032025',
    'news-phys-28032025',
]

# CONFIGURATION
CSV_FILE = "Copernicus AI Canonical List 071825.csv"
OUTPUT_FEED = "copernicus-mvp-rss-feed.xml"
BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
GCS_AUDIO_URL = f"https://storage.googleapis.com/{BUCKET_NAME}/audio/"
GCS_THUMB_URL = f"https://storage.googleapis.com/{BUCKET_NAME}/thumbnails/"
CHANNEL_IMAGE = f"https://storage.googleapis.com/{BUCKET_NAME}/images/copernicus-original-portrait-optimized.jpg"

NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "content": "http://purl.org/rss/1.0/modules/content/"
}

def normalize_duration(duration_str):
    # Converts '4,35' -> '4:35', '24,02' -> '24:02', etc.
    if not duration_str:
        return "0:00"
    return duration_str.replace(',', ':')

def load_description(fname):
    import requests
    url = f'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/descriptions/{fname}.md'
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception:
        pass
    return None

def parse_csv(csv_path):
    """Parse canonical CSV and return list of episode dicts."""
    episodes = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            fname = row.get("File Name", "").strip()
            title = row.get("Title", "").strip()
            duration = row.get("Duration", "").strip()
            file_size = row.get("File size in bytes", "").replace(',', '').strip()
            if fname and title and duration and file_size:
                description = load_description(fname) or title
                season = row.get("Season", "1").strip()
                episode = row.get("Episode", "").strip()
                episodes.append({
                    "fname": fname,
                    "title": title,
                    "duration": normalize_duration(duration),
                    "file_size": file_size,
                    "description": description,
                    "season": season,
                    "episode": episode
                })
    return episodes

def main():
    episodes = parse_csv(CSV_FILE)

    # Build RSS root
    rss = etree.Element("rss", version="2.0", nsmap=NAMESPACES)
    channel = etree.SubElement(rss, "channel")

    # --- Channel-level tags ---
    etree.SubElement(channel, "title").text = "Copernicus AI Podcast"
    etree.SubElement(channel, "link").text = "https://copernicusai.fyi/"
    etree.SubElement(channel, "description").text = "The Copernicus AI Podcast explores the frontiers of science and technology with short, accessible episodes."
    etree.SubElement(channel, "language").text = "en-us"
    itunes_cat = etree.SubElement(channel, "{%s}category" % NAMESPACES["itunes"], text="Science")
    # Add all five subcategories in alphabetical order
    etree.SubElement(itunes_cat, "{%s}category" % NAMESPACES["itunes"], text="Biology")
    etree.SubElement(itunes_cat, "{%s}category" % NAMESPACES["itunes"], text="Chemistry")
    etree.SubElement(itunes_cat, "{%s}category" % NAMESPACES["itunes"], text="Computer Science")
    etree.SubElement(itunes_cat, "{%s}category" % NAMESPACES["itunes"], text="Mathematics")
    etree.SubElement(itunes_cat, "{%s}category" % NAMESPACES["itunes"], text="Physics")
    etree.SubElement(channel, "{%s}author" % NAMESPACES["itunes"]).text = "CopernicusAI"
    etree.SubElement(channel, "{%s}summary" % NAMESPACES["itunes"]).text = "The Copernicus AI Podcast explores the frontiers of science and technology with short, accessible episodes."
    etree.SubElement(channel, "{%s}type" % NAMESPACES["itunes"]).text = "episodic"
    # Add channel-level itunes:explicit tag
    etree.SubElement(channel, "{%s}explicit" % NAMESPACES["itunes"]).text = "no"
    etree.SubElement(channel, "copyright").text = f"Copyright {datetime.datetime.now().year} Gary Welz. All rights reserved."
    owner = etree.SubElement(channel, "{%s}owner" % NAMESPACES["itunes"])
    etree.SubElement(owner, "{%s}name" % NAMESPACES["itunes"]).text = "Gary Welz"
    etree.SubElement(owner, "{%s}email" % NAMESPACES["itunes"]).text = "garywelz@gmail.com"
    etree.SubElement(channel, "{%s}image" % NAMESPACES["itunes"], href=CHANNEL_IMAGE)
    image = etree.SubElement(channel, "image")
    etree.SubElement(image, "url").text = CHANNEL_IMAGE
    etree.SubElement(image, "title").text = "Copernicus AI Podcast"
    etree.SubElement(image, "link").text = "https://copernicusai.fyi/"

    # Atom self-link
    atom_link = etree.SubElement(channel, "{%s}link" % NAMESPACES["atom"])
    atom_link.set("href", f"https://storage.googleapis.com/{BUCKET_NAME}/feeds/{OUTPUT_FEED}")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # --- Episode items ---
    # News episodes first, in user-specified order
    news_order = [
        "news-bio-28032025",
        "news-chem-28032025",
        "news-compsci-28032025",
        "news-math-28032025",
        "news-phys-28032025"
    ]
    # Build ordered list: news first, then rest
    sorted_episodes = []
    used = set()
    for news_id in news_order:
        for ep in episodes:
            if ep["fname"] == news_id:
                sorted_episodes.append(ep)
                used.add(news_id)
    for ep in episodes:
        if ep["fname"] not in used:
            sorted_episodes.append(ep)
    # Now emit with season/episode numbers
    for idx, ep in enumerate(sorted_episodes):
        fname = ep["fname"]
        title = ep["title"]
        duration = ep["duration"]
        file_size = ep["file_size"]
        audio_url = f"{GCS_AUDIO_URL}{fname}.mp3"
        thumb_url = f"{GCS_THUMB_URL}{fname}-thumb.jpg"
        guid = fname
        # Use canonical season and episode numbers from CSV
        season_number = ep.get("season", "1")
        episode_number = ep.get("episode", str(idx+1))
        # Fetch description from a source (e.g., GCS markdown or a field in CSV). For now, fallback to title if not available.
        description = ep.get("description") or title
        # Use first paragraph of description for summary
        summary = ''
        if description:
            # Split on double newline (blank line) or first single newline if no double newline
            import re
            parts = re.split(r'\n\s*\n', description)
            if parts:
                summary = parts[0].strip()
            else:
                summary = description.strip().split('\n')[0]
        else:
            summary = title
        item = etree.SubElement(channel, "item")
        etree.SubElement(item, "title").text = title
        etree.SubElement(item, "guid").text = guid
        etree.SubElement(item, "link").text = audio_url
        etree.SubElement(item, "description").text = description
        etree.SubElement(item, "{%s}summary" % NAMESPACES["itunes"]).text = summary
        if ep["fname"] in NEWS_EPISODES:
            etree.SubElement(item, "pubDate").text = NEWS_LAUNCH_DATE
        else:
            etree.SubElement(item, "pubDate").text = TODAY_DATE
        etree.SubElement(item, "{%s}image" % NAMESPACES["itunes"], href=thumb_url)
        etree.SubElement(item, "{%s}duration" % NAMESPACES["itunes"]).text = duration
        etree.SubElement(item, "{%s}explicit" % NAMESPACES["itunes"]).text = "no"
        etree.SubElement(item, "{%s}author" % NAMESPACES["itunes"]).text = "CopernicusAI"
        etree.SubElement(item, "{%s}content" % NAMESPACES["content"]).text = f"<![CDATA[<p>{title}</p>]]>"
        etree.SubElement(item, "{%s}season" % NAMESPACES["itunes"]).text = str(season_number)
        etree.SubElement(item, "{%s}episode" % NAMESPACES["itunes"]).text = str(episode_number)
        enclosure = etree.SubElement(item, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("type", "audio/mpeg")
        enclosure.set("length", file_size)

    # Write to file
    tree = etree.ElementTree(rss)
    tree.write(OUTPUT_FEED, pretty_print=True, xml_declaration=True, encoding="utf-8")
    print(f"RSS feed written to {OUTPUT_FEED}")

if __name__ == "__main__":
    main()