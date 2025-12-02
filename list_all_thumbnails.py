#!/usr/bin/env python3
"""List all thumbnails in the GCS bucket to see what actually exists"""

from google.cloud import storage

print("🔍 Listing all thumbnails in GCS bucket...\n")
print("="*80)

storage_client = storage.Client()
bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")

# List all blobs in thumbnails folder
blobs = bucket.list_blobs(prefix="thumbnails/")

thumbnail_files = []
for blob in blobs:
    if blob.name.endswith(('.jpg', '.jpeg', '.png', '.webp')):
        thumbnail_files.append(blob.name)

print(f"Found {len(thumbnail_files)} thumbnail files in GCS\n")

# Check if any match the 8 missing episodes
missing_guids = [
    'ever-bio-250040',
    '5d8db69e-cf58-4ecb-8c7f-58dd274e09b4',
    '4000f8f3-1fe4-4375-b73e-9408afbbf28e',
    'ever-math-250036',
    '85b0f041-75be-4e79-9175-f46498ba9d39',
    '977d7344-63f2-4aa7-80fc-9ea260b22806',
    '6ae0b6f7-85dd-4bb8-874e-51c549cdd4ba',
    'c28ba67b-5fc2-4f87-a53b-748430a57c86'
]

print("Checking for matches with missing episodes:\n")
for guid in missing_guids:
    # Try different patterns
    patterns = [
        f"thumbnails/{guid}-thumb.jpg",
        f"thumbnails/{guid}-thumb.webp",
        f"thumbnails/{guid}.jpg",
        f"thumbnails/{guid}.jpeg",
        f"thumbnails/{guid}-thumb.png",
    ]
    
    found_match = False
    for pattern in patterns:
        if any(blob_name == pattern for blob_name in thumbnail_files):
            print(f"✅ {guid}: Found at {pattern}")
            found_match = True
            break
    
    if not found_match:
        # Check for partial matches
        matches = [f for f in thumbnail_files if guid in f]
        if matches:
            print(f"⚠️  {guid}: Found similar files:")
            for match in matches[:3]:  # Show first 3
                print(f"      - {match}")
        else:
            print(f"❌ {guid}: Not found")

print("\n" + "="*80)
print(f"Total thumbnails in bucket: {len(thumbnail_files)}")
print("="*80)

