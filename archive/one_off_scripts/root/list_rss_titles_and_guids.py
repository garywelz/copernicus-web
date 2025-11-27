import xml.etree.ElementTree as ET

# Download the latest RSS feed if needed, or use local file
FEED = 'copernicus-final-rss-feed.xml'

tree = ET.parse(FEED)
root = tree.getroot()
channel = root.find('channel')

guid_count = {}
title_to_guid = {}
print("Episode Titles and GUIDs in Feed:\n")
for item in channel.findall('item'):
    title = item.find('title').text if item.find('title') is not None else '[No Title]'
    guid_elem = item.find('guid')
    guid = guid_elem.text if guid_elem is not None else '[No GUID]'
    print(f"Title: {title}\nGUID: {guid}\n")
    title_to_guid[title] = guid
    if guid not in guid_count:
        guid_count[guid] = []
    guid_count[guid].append(title)

print("\n--- Duplicate GUIDs ---")
duplicates = False
for guid, titles in guid_count.items():
    if len(titles) > 1:
        duplicates = True
        print(f"GUID: {guid}")
        for t in titles:
            print(f"  - {t}")
if not duplicates:
    print("No duplicate GUIDs found.")

print("\n--- Titles not in mapping (manual check required) ---")
# You can paste your mapping here to cross-check
