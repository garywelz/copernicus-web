#!/usr/bin/env python3
import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))

print("Starting fix script...", file=sys.stderr)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from datetime import datetime

PREFIX = 'Copernicus AI: Frontiers of Science - '
db = firestore.Client(database='copernicusai')

print("Connected to Firestore", file=sys.stderr)

# Fix titles
for canonical, expected in [('ever-chem-250017', 'AI-Designed Materials: A Paradigm Shift'), 
                            ('ever-phys-250032', 'Quantum Error Correction: The Dawn of Fault-Tolerant Quantum Computing')]:
    print(f"Fixing {canonical}...", file=sys.stderr)
    
    # Fix episodes
    ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(canonical)
    ep_doc = ep_ref.get()
    if ep_doc.exists:
        ep_data = ep_doc.to_dict() or {}
        title = ep_data.get('title', '')
        if title.startswith(PREFIX):
            new_title = title.replace(PREFIX, '', 1)
            ep_ref.update({'title': new_title, 'updated_at': datetime.utcnow().isoformat()})
            print(f"Fixed episodes: {canonical}", file=sys.stderr)
    
    # Fix podcast_jobs
    for job in db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream():
        job_data = job.to_dict() or {}
        result = job_data.get('result', {})
        title = result.get('title', '')
        if title.startswith(PREFIX):
            result['title'] = title.replace(PREFIX, '', 1)
            job.reference.update({'result': result, 'updated_at': datetime.utcnow().isoformat()})
            print(f"Fixed podcast_jobs: {canonical}", file=sys.stderr)

# Delete ever-chem-250021
canonical = 'ever-chem-250021'
print(f"Deleting {canonical}...", file=sys.stderr)

ep_ref = db.collection(EPISODE_COLLECTION_NAME).document(canonical)
if ep_ref.get().exists:
    ep_ref.delete()
    print(f"Deleted from episodes: {canonical}", file=sys.stderr)

for job in db.collection('podcast_jobs').where('result.canonical_filename', '==', canonical).stream():
    job.reference.delete()
    print(f"Deleted from podcast_jobs: {canonical}", file=sys.stderr)

print("Done!", file=sys.stderr)




