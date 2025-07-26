import xml.etree.ElementTree as ET
import os

# Mapping from your canonical list
EPISODE_TITLES = {
    "ever-bio-250006": "CRISPR Chemistry: Molecular Editing",
    "ever-bio-250007": "CRISPR Epigenome: Beyond DNA", 
    "ever-bio-250014": "Minimal Cells: Life's Essentials",
    "ever-bio-250016": "Neural Optogenetics: Light-Controlled Brains",
    "ever-bio-250018": "Organoids: Miniature Organs",
    "ever-bio-250020": "Spatial Biology: Cell Mapping",
    "ever-bio-250028": "Synthetic Biology: Redesigning Life",
    "ever-chem-250002": "Catalysis Revolution: Transforming Reactions",
    "ever-chem-250005": "Computational Chemistry: Molecular Modeling",
    "ever-chem-250010": "Green Chemistry: Sustainable Synthesis", 
    "ever-chem-250015": "Molecular Machines: Nanoscale Engineering",
    "ever-compsci-250008": "Edge Computing: Intelligence at the Frontier",
    "ever-compsci-250017": "Neuromorphic Computing: Brain-Inspired Systems",
    "ever-compsci-250024": "Artificial General Intelligence: Promise & Challenges",
    "ever-math-250009": "Mathematical Logic: 2024 Breakthroughs",
    "ever-math-250011": "Gödel's Incompleteness: Truth's Limits", 
    "ever-math-250012": "Independence in Peano Arithmetic",
    "ever-math-250023": "Continuum Hypothesis: Set Theory's Mystery",
    "ever-math-250025": "Gödel's Incompleteness: Mathematical Truth",
    "ever-math-250029": "Poincaré Conjecture: Century-Long Journey",
    "ever-math-250031": "Independence in Peano Arithmetic",
    "ever-math-250032": "Mathematical Logic: Recent Breakthroughs",
    "ever-phys-250019": "Quantum Machine Learning: AI Meets Quantum",
    "ever-phys-250021": "String Theory: Theory of Everything",
    "ever-phys-250022": "Higgs Boson: Hunt for God Particle", 
    "ever-phys-250026": "Quantum Entanglement: Spooky Action",
    "ever-phys-250027": "Quantum Cryptography: Secure Communication",
    "ever-phys-250030": "Quantum Batteries: Future Energy Storage",
    "news-bio-250001": "Biology News 28032025",
    "news-chem-250003": "Chemistry News 28032025", 
    "news-compsci-250004": "Computer Science News 28032025",
    "news-math-250013": "Mathematics News 28032025",
    "news-phys-250014": "Physics News 28032025"
}

FEED = 'copernicus-final-rss-feed.xml'
tree = ET.parse(FEED)
root = tree.getroot()
channel = root.find('channel')

unmatched = []
for item in channel.findall('item'):
    enclosure = item.find('enclosure')
    audio_url = None
    slug = None
    if enclosure is not None and 'url' in enclosure.attrib:
        audio_url = enclosure.attrib['url']
        base = os.path.basename(audio_url)
        slug = base.split('.')[0]
    if not slug:
        guid_elem = item.find('guid')
        if guid_elem is not None and guid_elem.text:
            base = os.path.basename(guid_elem.text)
            slug = base.split('.')[0]
    if slug not in EPISODE_TITLES:
        title = item.find('title').text if item.find('title') is not None else '[No Title]'
        unmatched.append((title, audio_url if audio_url else '[No audio URL]'))

print("Unmatched episodes (not in mapping):")
for title, audio_url in unmatched:
    print(f"- Title: {title}\n  Audio file: {audio_url}")
