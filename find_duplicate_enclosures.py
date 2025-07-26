import xml.etree.ElementTree as ET

tree = ET.parse('copernicus-final-rss-feed.xml')
root = tree.getroot()
channel = root.find('channel')
guid_map = {}

for item in channel.findall('item'):
    enclosure = item.find('enclosure')
    title = item.find('title').text if item.find('title') is not None else '[No Title]'
    if enclosure is not None and 'url' in enclosure.attrib:
        url = enclosure.attrib['url']
        if url not in guid_map:
            guid_map[url] = []
        guid_map[url].append(title)

for url, titles in guid_map.items():
    if len(titles) > 1:
        print(f'DUPLICATE: {url}\n  Titles:')
        for t in titles:
            print(f'    - {t}')
