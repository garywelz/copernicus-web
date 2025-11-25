#!/usr/bin/env python3
from google.cloud import firestore

db = firestore.Client(database='copernicusai')
episodes = db.collection('episodes').stream()

print('Firestore slugs:')
for ep in episodes:
    data = ep.to_dict()
    slug = data.get('slug') or data.get('episode_id') or ep.id
    print(f"  {slug}")

