#!/usr/bin/env python3
"""Check if thumbnails actually exist in GCS for the 8 missing episodes"""

from google.cloud import storage
import requests

# The 8 episodes from the diagnosis
episodes = [
    {
        'guid': 'ever-bio-250040',
        'title': 'Revolutionizing COVID-19 Treatment: Emerging Strategies and Paradigm Shifts'
    },
    {
        'guid': '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
        'title': 'Quantum Computing Advances'
    },
    {
        'guid': '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
        'title': 'Silicon compounds'
    },
    {
        'guid': 'ever-math-250036',
        'title': 'Mathematics Meets Biology: Unlocking New Frontiers in Personalized Medicine and Beyond'
    },
    {
        'guid': '85b0f041-75be-4e79-9175-f46498ba9d39',
        'title': 'Quantum Computing chip advances'
    },
    {
        'guid': '977d7344-63f2-4aa7-80fc-9ea260b22806',
        'title': 'Prime Number Theory update'
    },
    {
        'guid': '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
        'title': 'New materials created using AI'
    },
    {
        'guid': 'c28ba67b-5fc2-4f87-a53b-748430a57c86',
        'title': 'Matrix Multiplication advances'
    }
]

print("🔍 Checking if thumbnails exist in GCS...\n")
print("="*80)

storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")

found = []
not_found = []

for episode in episodes:
    guid = episode['guid']
    title = episode['title']
    
    # Check expected location
    expected_blob_name = f"thumbnails/{guid}-thumb.jpg"
    blob = bucket.blob(expected_blob_name)
    
    exists = blob.exists()
    accessible = False
    url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{expected_blob_name}"
    
    if exists:
        # Check if publicly accessible
        try:
            response = requests.head(url, timeout=5)
            accessible = response.status_code == 200
        except:
            pass
    
    # Also check for alternative naming patterns
    alternatives = [
        f"thumbnails/{guid}-thumb.webp",
        f"thumbnails/{guid}.jpg",
        f"thumbnails/{guid}-thumb.png",
    ]
    
    alt_found = None
    for alt_path in alternatives:
        alt_blob = bucket.blob(alt_path)
        if alt_blob.exists():
            alt_found = alt_path
            break
    
    result = {
        'guid': guid,
        'title': title,
        'expected_path': expected_blob_name,
        'exists': exists,
        'accessible': accessible,
        'url': url,
        'alternative_found': alt_found
    }
    
    if exists or alt_found:
        found.append(result)
    else:
        not_found.append(result)

print(f"\n✅ FOUND THUMBNAILS: {len(found)}")
print("="*80)
for item in found:
    print(f"\n✓ {item['title'][:60]}")
    print(f"  GUID: {item['guid']}")
    if item['exists']:
        print(f"  Location: {item['expected_path']}")
        print(f"  Accessible: {item['accessible']}")
        print(f"  URL: {item['url']}")
    else:
        print(f"  Found at alternative: {item['alternative_found']}")

print(f"\n❌ NOT FOUND: {len(not_found)}")
print("="*80)
for item in not_found:
    print(f"\n✗ {item['title'][:60]}")
    print(f"  GUID: {item['guid']}")
    print(f"  Expected: {item['expected_path']}")
    print(f"  URL: {item['url']}")

print("\n" + "="*80)
print(f"SUMMARY: {len(found)} found, {len(not_found)} not found")
print("="*80)

