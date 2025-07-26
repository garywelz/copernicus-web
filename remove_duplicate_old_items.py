import xml.etree.ElementTree as ET

FEED = 'copernicus-final-rss-feed.xml'
OUTPUT = 'copernicus-final-rss-feed-cleaned.xml'

# Old slugs to remove (the ones causing duplicate GUIDs)
OLD_GUIDS = [
    'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/crispr-epigenome-audio.mp3',
    'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/neural-optogenetics-audio.mp3',
    'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/minimal-cells-audio.mp3',
]

# Parse RSS
ET.register_namespace('itunes', "http://www.itunes.com/dtds/podcast-1.0.dtd")
tree = ET.parse(FEED)
root = tree.getroot()
channel = root.find('channel')

items_to_remove = []
for item in channel.findall('item'):
    guid_elem = item.find('guid')
    guid = guid_elem.text if guid_elem is not None else ''
    if guid in OLD_GUIDS:
        # Mark for removal if there is more than one with this GUID
        items_to_remove.append(item)

# Remove all but one occurrence of each old GUID
removed = set()
for guid in OLD_GUIDS:
    count = 0
    for item in items_to_remove:
        guid_elem = item.find('guid')
        if guid_elem is not None and guid_elem.text == guid:
            count += 1
            if count > 1:
                channel.remove(item)
                removed.add(guid)

# Save cleaned feed
with open(OUTPUT, 'wb') as f:
    tree.write(f, encoding='utf-8', xml_declaration=True)

print(f"Removed duplicates for: {removed if removed else 'none'}\nCleaned feed saved as {OUTPUT}")
