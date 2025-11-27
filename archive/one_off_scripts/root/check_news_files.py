import os
from google.cloud import storage

# News episodes with canonical IDs and titles
NEWS_EPISODES = {
    "news-bio-28032025": "Biology News 28032025",
    "news-chem-28032025": "Chemistry News 28032025",
    "news-compsci-28032025": "Computer Science News 28032025",
    "news-math-28032025": "Mathematics News 28032025",
    "news-phys-28032025": "Physics News 28032025"
}

BUCKET = "regal-scholar-453620-r7-podcast-storage"
AUDIO_PREFIX = "audio/"
DESC_PREFIX = "descriptions/"
THUMB_PREFIX = "thumbnails/"
GCS_KEY = "/home/gdubs/copernicus-web-public/regal-scholar-453620-r7-b4a72581927b.json"

def main():
    client = storage.Client.from_service_account_json(GCS_KEY)
    bucket = client.bucket(BUCKET)
    for eid, title in NEWS_EPISODES.items():
        print(f"\nChecking {eid}: {title}")
        audio_blob = f"{AUDIO_PREFIX}{eid}.mp3"
        desc_blob = f"{DESC_PREFIX}{eid}.md"
        thumb_blob = f"{THUMB_PREFIX}{eid}-thumb.jpg"
        thumb_blob_webp = f"{THUMB_PREFIX}{eid}-thumb.webp"
        missing = []
        if not bucket.blob(audio_blob).exists(client):
            missing.append(audio_blob)
        if not bucket.blob(desc_blob).exists(client):
            missing.append(desc_blob)
        if not (bucket.blob(thumb_blob).exists(client) or bucket.blob(thumb_blob_webp).exists(client)):
            missing.append(f"{thumb_blob} or {thumb_blob_webp}")
        if missing:
            print("  MISSING:")
            for f in missing:
                print(f"    - {f}")
        else:
            print("  ALL FILES PRESENT!")

if __name__ == "__main__":
    main()
