#!/usr/bin/env python3
"""Check if thumbnails exist with canonical naming for the 8 episodes"""

from google.cloud import storage
from google.cloud import firestore
import requests
import json

GCP_PROJECT_ID = "regal-scholar-453620-r7"

# The 8 episodes
episodes = [
    'ever-bio-250040',
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    'ever-math-250036',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

print("🔍 Checking canonical filenames and existing thumbnails...\n")
print("="*80)

storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
db = firestore.Client(project=GCP_PROJECT_ID)

for guid in episodes:
    print(f"\n📋 GUID: {guid}")
    
    # Get canonical filename from Firestore
    canonical = None
    title = None
    
    # Check episodes collection
    episode_doc = db.collection('episodes').document(guid).get()
    if episode_doc.exists:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_data.get('canonical_filename') or guid
        title = episode_data.get('title', 'Unknown')
    else:
        # Check podcast_jobs
        podcast_jobs = db.collection('podcast_jobs').where('result.canonical_filename', '==', guid).limit(1).stream()
        for job_doc in podcast_jobs:
            job_data = job_doc.to_dict() or {}
            result = job_data.get('result', {})
            canonical = result.get('canonical_filename') or guid
            title = result.get('title') or job_data.get('request', {}).get('topic', 'Unknown')
            break
    
    if not canonical:
        canonical = guid
    
    print(f"  Title: {title[:60] if title else 'Unknown'}")
    print(f"  Canonical filename: {canonical}")
    
    # Check if thumbnail exists with canonical naming
    canonical_thumb_path = f"thumbnails/{canonical}-thumb.jpg"
    canonical_blob = bucket.blob(canonical_thumb_path)
    canonical_exists = canonical_blob.exists()
    
    # Check if thumbnail exists with GUID naming (what I just created)
    guid_thumb_path = f"thumbnails/{guid}-thumb.jpg"
    guid_blob = bucket.blob(guid_thumb_path)
    guid_exists = guid_blob.exists()
    
    print(f"  ✅ Canonical thumbnail exists: {canonical_exists} ({canonical_thumb_path})")
    print(f"  {'⚠️' if guid_exists else '❌'} GUID thumbnail exists: {guid_exists} ({guid_thumb_path})")
    
    if canonical_exists and canonical != guid:
        print(f"  ⚠️  ISSUE: Thumbnail exists with canonical name, but RSS feed may be using GUID!")
    elif not canonical_exists and guid_exists:
        print(f"  ⚠️  ISSUE: Created thumbnail with wrong name (GUID instead of canonical)!")

print("\n" + "="*80)

