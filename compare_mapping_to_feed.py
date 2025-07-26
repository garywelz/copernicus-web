import xml.etree.ElementTree as ET

# The mapping as provided
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
    # News Series (5 episodes)
    "news-bio-250001": "Biology News 28032025",
    "news-chem-250003": "Chemistry News 28032025", 
    "news-compsci-250004": "Computer Science News 28032025",
    "news-math-250013": "Mathematics News 28032025",
    "news-phys-250014": "Physics News 28032025"
}

MAPPING_TITLES = set(EPISODE_TITLES.values())

FEED = 'copernicus-final-rss-feed-cleaned.xml'
tree = ET.parse(FEED)
root = tree.getroot()
channel = root.find('channel')

feed_titles = set()
for item in channel.findall('item'):
    title = item.find('title').text if item.find('title') is not None else '[No Title]'
    feed_titles.add(title)

print(f"Titles in mapping but missing from feed:")
missing = MAPPING_TITLES - feed_titles
for title in sorted(missing):
    print(f"  - {title}")

print(f"\nTitles in feed but not in mapping:")
extra = feed_titles - MAPPING_TITLES
for title in sorted(extra):
    print(f"  - {title}")

print(f"\nTotal in mapping: {len(MAPPING_TITLES)}")
print(f"Total in feed: {len(feed_titles)}")
