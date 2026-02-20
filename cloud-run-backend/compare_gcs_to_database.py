#!/usr/bin/env python3
"""
Compare audio files in Google Cloud Storage with podcasts in database.
Find unused audio files that can be archived.
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import storage
from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME, RSS_BUCKET_NAME

print("="*80)
print("COMPARING GCS AUDIO FILES WITH DATABASE")
print("="*80)

# Initialize clients
storage_client = storage.Client()
bucket = storage_client.bucket(RSS_BUCKET_NAME)
db = firestore.Client(database='copernicusai')

print(f"Bucket: {RSS_BUCKET_NAME}")

# 1. Get all audio files from GCS
print("\n1. Listing all audio files in GCS...")
gcs_audio_files = set()
blobs = bucket.list_blobs(prefix="audio/")
for blob in blobs:
    if blob.name.endswith('.mp3'):
        # Extract canonical filename (remove "audio/" prefix and ".mp3" extension)
        filename = blob.name.replace("audio/", "").replace(".mp3", "")
        gcs_audio_files.add(filename)

print(f"   Found {len(gcs_audio_files)} audio files in GCS")

# 2. Get all canonical filenames from episodes collection
print("\n2. Getting all podcasts from episodes collection...")
database_podcasts = set()
episodes_query = db.collection(EPISODE_COLLECTION_NAME).stream()
for episode_doc in episodes_query:
    database_podcasts.add(episode_doc.id)

print(f"   Found {len(database_podcasts)} podcasts in database")

# 3. Get all canonical filenames from podcast_jobs
print("\n3. Getting all podcasts from podcast_jobs collection...")
jobs_podcasts = set()
jobs_query = db.collection('podcast_jobs').stream()
for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    if canonical:
        jobs_podcasts.add(canonical)

print(f"   Found {len(jobs_podcasts)} podcasts in podcast_jobs")

# 4. Union = all podcasts that exist
all_podcasts = database_podcasts | jobs_podcasts
print(f"\n   Total unique podcasts (union): {len(all_podcasts)}")

# 5. Find audio files NOT in database
print("\n4. Comparing GCS files with database...")
unused_audio = gcs_audio_files - all_podcasts
missing_audio = all_podcasts - gcs_audio_files

if unused_audio:
    print(f"\n⚠️  Found {len(unused_audio)} audio file(s) in GCS that are NOT in database:")
    print("   (These can be archived)")
    for filename in sorted(unused_audio)[:20]:  # Show first 20
        print(f"      - {filename}")
    if len(unused_audio) > 20:
        print(f"      ... and {len(unused_audio) - 20} more")
else:
    print("\n✅ All audio files in GCS are associated with podcasts")

if missing_audio:
    print(f"\n⚠️  Found {len(missing_audio)} podcast(s) in database without audio files:")
    for filename in sorted(missing_audio)[:10]:  # Show first 10
        print(f"      - {filename}")
    if len(missing_audio) > 10:
        print(f"      ... and {len(missing_audio) - 10} more")

# 6. Check gwelz@jjay.cuny.edu specifically
print("\n" + "="*80)
print("CHECKING gwelz@jjay.cuny.edu SPECIFICALLY")
print("="*80)

email = "gwelz@jjay.cuny.edu"
gwelz_id = None
for sub_doc in db.collection('subscribers').stream():
    if sub_doc.to_dict().get('email') == email:
        gwelz_id = sub_doc.id
        break

if gwelz_id:
    print(f"\nSubscriber ID: {gwelz_id}")
    
    # Get from podcast_jobs
    gwelz_jobs = set()
    for job_doc in db.collection('podcast_jobs').where('subscriber_id', '==', gwelz_id).stream():
        canonical = job_doc.to_dict().get('result', {}).get('canonical_filename')
        if canonical:
            gwelz_jobs.add(canonical)
    
    # Get from episodes
    gwelz_episodes = set()
    for ep_doc in db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', gwelz_id).stream():
        gwelz_episodes.add(ep_doc.id)
    
    # Union = all in gwelz account
    gwelz_all = gwelz_jobs | gwelz_episodes
    
    print(f"\nPodcasts in podcast_jobs: {len(gwelz_jobs)}")
    print(f"Podcasts in episodes: {len(gwelz_episodes)}")
    print(f"Total in account (union): {len(gwelz_all)}")
    
    # Find missing from database
    gwelz_missing_from_db = gwelz_all - database_podcasts
    
    if gwelz_missing_from_db:
        print(f"\n⚠️  Found {len(gwelz_missing_from_db)} podcast(s) in gwelz account but NOT in database:")
        for canonical in sorted(gwelz_missing_from_db):
            print(f"      - {canonical}")
            # Check if audio exists
            if canonical in gcs_audio_files:
                print(f"        (Audio file exists in GCS)")
            else:
                print(f"        (No audio file in GCS)")
    else:
        print(f"\n✅ All podcasts in gwelz account are in database")
    
    # List all gwelz podcasts with status
    print(f"\nAll podcasts in gwelz account ({len(gwelz_all)}):")
    for canonical in sorted(gwelz_all):
        in_db = "✓" if canonical in database_podcasts else "✗"
        in_gcs = "✓" if canonical in gcs_audio_files else "✗"
        print(f"   {in_db}DB {in_gcs}GCS {canonical}")

# 7. Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Audio files in GCS: {len(gcs_audio_files)}")
print(f"Podcasts in database (episodes): {len(database_podcasts)}")
print(f"Podcasts in podcast_jobs: {len(jobs_podcasts)}")
print(f"Total unique podcasts: {len(all_podcasts)}")
print(f"\nUnused audio files (can archive): {len(unused_audio)}")
print(f"Missing audio files: {len(missing_audio)}")




