import xml.etree.ElementTree as ET
import subprocess
import re
import urllib.request

# CONFIGURATION
RSS_FEED_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/rss-feed.xml"
GCS_BUCKET = "gs://regal-scholar-453620-r7-podcast-storage"

# 1. Download and parse RSS feed
print("Downloading and parsing RSS feed...")
response = urllib.request.urlopen(RSS_FEED_URL)
rss_data = response.read()
root = ET.fromstring(rss_data)

referenced_files = set()

# Find all URLs in <enclosure> tags (audio), <itunes:image>, <image>, and <media:content>
for item in root.findall(".//item"):
    # Audio files
    enclosure = item.find("enclosure")
    if enclosure is not None and "url" in enclosure.attrib:
        referenced_files.add(enclosure.attrib["url"])
    # Episode images (itunes:image)
    itunes_image = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
    if itunes_image is not None and "href" in itunes_image.attrib:
        referenced_files.add(itunes_image.attrib["href"])
    # Media content (optional, for video podcasts)
    media_content = item.find("{http://search.yahoo.com/mrss/}content")
    if media_content is not None and "url" in media_content.attrib:
        referenced_files.add(media_content.attrib["url"])

# Also check channel-level images
channel_image = root.find("./channel/image/url")
if channel_image is not None:
    referenced_files.add(channel_image.text)
itunes_channel_image = root.find("./channel/{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
if itunes_channel_image is not None and "href" in itunes_channel_image.attrib:
    referenced_files.add(itunes_channel_image.attrib["href"])

def url_to_gcs_path(url):
    match = re.search(r'/regal-scholar-453620-r7-podcast-storage/(.+)', url)
    if match:
        return match.group(1)
    return None

referenced_gcs_paths = set()
for url in referenced_files:
    rel_path = url_to_gcs_path(url)
    if rel_path:
        referenced_gcs_paths.add(rel_path)

print(f"Found {len(referenced_gcs_paths)} referenced GCS files in RSS feed.")

# 2. List all files in the GCS bucket
print("Listing all files in GCS bucket...")
cmd = ["gsutil", "ls", "-r", f"{GCS_BUCKET}/**"]
all_files_output = subprocess.check_output(cmd).decode("utf-8")
all_gcs_files = set()
for line in all_files_output.splitlines():
    if line.startswith(GCS_BUCKET):
        rel_path = line.replace(GCS_BUCKET + "/", "")
        all_gcs_files.add(rel_path)

print(f"Found {len(all_gcs_files)} total files in GCS bucket.")

# 3. Find files not referenced in RSS feed
unused_files = sorted(all_gcs_files - referenced_gcs_paths)

print("\nUnused files (not referenced in RSS feed):")
for f in unused_files:
    print(f)

print(f"\nTotal unused files: {len(unused_files)}")
