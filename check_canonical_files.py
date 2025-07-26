import os
from google.cloud import storage

# Canonical mapping from episode ID to title
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

BUCKET = "regal-scholar-453620-r7-podcast-storage"
AUDIO_PREFIX = "audio/"
DESC_PREFIX = "descriptions/"
THUMB_PREFIX = "thumbnails/"

GCS_KEY = "/home/gdubs/copernicus-web-public/regal-scholar-453620-r7-b4a72581927b.json"

def main():
    client = storage.Client.from_service_account_json(GCS_KEY)
    bucket = client.bucket(BUCKET)
    missing_audio = []
    missing_desc = []
    missing_thumb = []
    for eid, title in EPISODE_TITLES.items():
        audio_blob = f"{AUDIO_PREFIX}{eid}.mp3"
        desc_blob = f"{DESC_PREFIX}{eid}.md"
        thumb_blob = f"{THUMB_PREFIX}{eid}-thumb.jpg"
        thumb_blob_webp = f"{THUMB_PREFIX}{eid}-thumb.webp"
        # Check audio
        if not bucket.blob(audio_blob).exists(client):
            missing_audio.append((eid, title, audio_blob))
        # Check description
        if not bucket.blob(desc_blob).exists(client):
            missing_desc.append((eid, title, desc_blob))
        # Check thumbnail (accept .jpg or .webp)
        if not (bucket.blob(thumb_blob).exists(client) or bucket.blob(thumb_blob_webp).exists(client)):
            missing_thumb.append((eid, title, thumb_blob + ' or ' + thumb_blob_webp))
    print("=== Missing Audio Files ===")
    for eid, title, fn in missing_audio:
        print(f"{eid}: {title} -> {fn}")
    print("=== Missing Description Files ===")
    for eid, title, fn in missing_desc:
        print(f"{eid}: {title} -> {fn}")
    print("=== Missing Thumbnail Files ===")
    for eid, title, fn in missing_thumb:
        print(f"{eid}: {title} -> {fn}")
    print("=== Summary ===")
    print(f"Total episodes: {len(EPISODE_TITLES)}")
    print(f"Ready for RSS (all files present): {len(EPISODE_TITLES) - len(set([e for e,_,_ in missing_audio+missing_desc+missing_thumb]))}")

if __name__ == "__main__":
    main()
