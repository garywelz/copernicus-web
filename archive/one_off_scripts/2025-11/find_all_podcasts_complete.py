#!/usr/bin/env python3
"""Find ALL podcasts by counting directly from Firestore to identify missing ones"""

import os
import sys
import requests
import json
import re
from google.cloud import secretmanager
from google.cloud import firestore

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def main():
    print("🔍 Finding ALL Podcasts - Complete Analysis")
    print("="*80)
    
    # Connect to Firestore
    db = firestore.Client(project=GCP_PROJECT_ID, database="copernicusai")
    
    print("\n📊 Counting ALL podcast_jobs entries...")
    all_job_docs = list(db.collection('podcast_jobs').stream())
    print(f"✅ Found {len(all_job_docs)} total podcast_jobs entries")
    
    print("\n📊 Counting ALL episodes entries...")
    all_episode_docs = list(db.collection('episodes').stream())
    print(f"✅ Found {len(all_episode_docs)} total episodes entries")
    
    # Get database count via API
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    print("\n📊 Fetching database endpoint count...")
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        db_data = response.json()
        db_count = db_data.get("total_count", 0)
        print(f"✅ Database endpoint reports: {db_count} podcasts")
    else:
        db_count = 0
        print(f"⚠️  Could not fetch database count (HTTP {response.status_code})")
    
    # Analyze podcast_jobs
    print("\n" + "="*80)
    print("ANALYZING PODCAST_JOBS COLLECTION")
    print("="*80)
    
    canonical_pattern = re.compile(r'^(ever|news)-(bio|chem|compsci|math|phys)-\d{6,8}(-\d{4})?$')
    
    with_canonical = []
    without_canonical = []
    by_status = {}
    
    for job_doc in all_job_docs:
        job_data = job_doc.to_dict() or {}
        result = job_data.get('result', {})
        canonical = result.get('canonical_filename', '')
        status = job_data.get('status', 'unknown')
        title = result.get('title') or job_data.get('request', {}).get('topic', 'Untitled')
        
        if status not in by_status:
            by_status[status] = []
        by_status[status].append({
            'job_id': job_doc.id,
            'canonical': canonical,
            'title': title
        })
        
        is_canonical = bool(canonical_pattern.match(canonical)) if canonical else False
        
        if is_canonical:
            with_canonical.append({
                'job_id': job_doc.id,
                'canonical': canonical,
                'title': title,
                'status': status
            })
        else:
            without_canonical.append({
                'job_id': job_doc.id,
                'canonical': canonical or 'None',
                'title': title,
                'status': status
            })
    
    print(f"\nPodcast Jobs with canonical filenames: {len(with_canonical)}")
    print(f"Podcast Jobs without canonical filenames: {len(without_canonical)}")
    
    print(f"\nPodcast Jobs by Status:")
    for status, items in sorted(by_status.items()):
        print(f"  {status}: {len(items)}")
    
    if without_canonical:
        print(f"\n⚠️  Podcasts WITHOUT Canonical Filenames ({len(without_canonical)}):")
        for i, item in enumerate(without_canonical[:10], 1):
            print(f"  {i}. {item['title'][:60]}")
            print(f"     Job ID: {item['job_id']}")
            print(f"     Canonical: {item['canonical']}")
            print(f"     Status: {item['status']}")
        if len(without_canonical) > 10:
            print(f"     ... and {len(without_canonical) - 10} more")
    
    # Analyze episodes
    print("\n" + "="*80)
    print("ANALYZING EPISODES COLLECTION")
    print("="*80)
    
    episodes_with_canonical = []
    episodes_without_canonical = []
    
    for episode_doc in all_episode_docs:
        episode_data = episode_doc.to_dict() or {}
        canonical = episode_doc.id  # Episode ID is canonical filename
        title = episode_data.get('title', 'Untitled')
        
        is_canonical = bool(canonical_pattern.match(canonical)) if canonical else False
        
        if is_canonical:
            episodes_with_canonical.append({
                'canonical': canonical,
                'title': title
            })
        else:
            episodes_without_canonical.append({
                'canonical': canonical,
                'title': title
            })
    
    print(f"\nEpisodes with canonical filenames: {len(episodes_with_canonical)}")
    print(f"Episodes without canonical filenames: {len(episodes_without_canonical)}")
    
    if episodes_without_canonical:
        print(f"\n⚠️  Episodes WITHOUT Canonical Filenames ({len(episodes_without_canonical)}):")
        for i, item in enumerate(episodes_without_canonical[:10], 1):
            print(f"  {i}. {item['title'][:60]}")
            print(f"     Canonical/ID: {item['canonical']}")
        if len(episodes_without_canonical) > 10:
            print(f"     ... and {len(episodes_without_canonical) - 10} more")
    
    # Summary
    print("\n" + "="*80)
    print("📊 COMPLETE SUMMARY")
    print("="*80)
    print(f"Total podcast_jobs entries: {len(all_job_docs)}")
    print(f"Total episodes entries: {len(all_episode_docs)}")
    print(f"Database endpoint count: {db_count}")
    print(f"\nExpected count: 64")
    print(f"Actual database count: {db_count}")
    print(f"Missing: {64 - db_count if db_count < 64 else 0}")
    
    # Find unique podcasts (avoid double counting)
    unique_canonicals = set()
    for item in with_canonical:
        unique_canonicals.add(item['canonical'])
    for item in episodes_with_canonical:
        unique_canonicals.add(item['canonical'])
    
    print(f"\nUnique canonical filenames found: {len(unique_canonicals)}")
    print(f"Podcasts without canonical: {len(without_canonical) + len(episodes_without_canonical)}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

