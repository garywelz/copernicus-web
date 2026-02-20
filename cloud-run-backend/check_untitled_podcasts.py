#!/usr/bin/env python3
"""
Check which podcasts are showing as "Untitled" and why
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from google.cloud import firestore
from config.constants import EPISODE_COLLECTION_NAME
from utils.subscriber_helpers import get_subscriber_by_email

email = "gwelz@jjay.cuny.edu"

db = firestore.Client(database='copernicusai')

# Get subscriber
subscriber_doc = get_subscriber_by_email(email)
if not subscriber_doc:
    print(f"❌ Subscriber not found: {email}")
    sys.exit(1)

subscriber_id = subscriber_doc.id
print(f"✅ Found subscriber: {email} (ID: {subscriber_id})\n")

print("Checking podcasts that might show as 'Untitled'...\n")

# Check podcasts from podcast_jobs
print("="*70)
print("PODCASTS FROM PODCAST_JOBS:")
print("="*70)

jobs_query = db.collection('podcast_jobs').where('subscriber_id', '==', subscriber_id).stream()
job_podcasts = {}

for job_doc in jobs_query:
    job_data = job_doc.to_dict() or {}
    result = job_data.get('result', {})
    canonical = result.get('canonical_filename')
    
    if not canonical:
        continue
    
    title_from_result = result.get('title', '')
    title_from_request = job_data.get('request', {}).get('topic', '')
    
    job_podcasts[canonical] = {
        'title_from_result': title_from_result,
        'title_from_request': title_from_request,
        'has_episode': False
    }

# Check episodes
print("="*70)
print("PODCASTS FROM EPISODES:")
print("="*70)

episodes_query = db.collection(EPISODE_COLLECTION_NAME).where('subscriber_id', '==', subscriber_id).stream()
untitled_count = 0
has_title_count = 0

for episode_doc in episodes_query:
    episode_data = episode_doc.to_dict() or {}
    canonical = episode_doc.id
    title = episode_data.get('title', '')
    topic = episode_data.get('topic', '')
    
    if canonical in job_podcasts:
        job_podcasts[canonical]['has_episode'] = True
        job_podcasts[canonical]['episode_title'] = title
        job_podcasts[canonical]['episode_topic'] = topic
    
    if not title or title == 'Untitled' or title == 'Untitled Episode':
        untitled_count += 1
        print(f"  ❌ {canonical}: '{title}' (topic: '{topic[:50] if topic else 'N/A'}...')")
    else:
        has_title_count += 1

print(f"\n{'='*70}")
print(f"SUMMARY:")
print(f"  Episodes with titles: {has_title_count}")
print(f"  Episodes without titles: {untitled_count}")
print(f"{'='*70}\n")

# Show podcasts that might cause issues
print("="*70)
print("PODCASTS THAT MIGHT SHOW AS 'UNTITLED' IN DASHBOARD:")
print("="*70)

issues = []
for canonical, data in job_podcasts.items():
    episode_title = data.get('episode_title', '')
    title_from_result = data.get('title_from_result', '')
    title_from_request = data.get('title_from_request', '')
    
    # What title would the API return?
    api_title = episode_title or title_from_result or title_from_request or 'Untitled'
    
    if not episode_title or episode_title == 'Untitled':
        issues.append({
            'canonical': canonical,
            'episode_title': episode_title or '(missing)',
            'result_title': title_from_result or '(missing)',
            'request_topic': title_from_request or '(missing)',
            'api_would_return': api_title
        })

if issues:
    for issue in issues[:20]:  # Show first 20
        print(f"\n  {issue['canonical']}:")
        print(f"    Episode title: {issue['episode_title']}")
        print(f"    Result title: {issue['result_title']}")
        print(f"    Request topic: {issue['request_topic']}")
        print(f"    API would return: {issue['api_would_return'][:60]}...")
else:
    print("  ✅ No issues found - all podcasts have titles!")

print(f"\n{'='*70}")
print(f"Total issues: {len(issues)}")
print(f"{'='*70}")




