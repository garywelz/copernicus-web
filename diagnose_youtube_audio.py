#!/usr/bin/env python3
"""Diagnose YouTube audio corruption for the 6 failed podcasts"""

import os
import sys
import requests
import json
from google.cloud import secretmanager
from google.cloud import storage
from urllib.parse import urlparse

GCP_PROJECT_ID = "regal-scholar-453620-r7"
API_BASE_URL = "https://copernicus-podcast-api-204731194849.us-central1.run.app"
BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"

def get_admin_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()

def check_audio_file(audio_url):
    """Check if audio file exists and is accessible"""
    if not audio_url:
        return {'exists': False, 'accessible': False, 'error': 'No audio URL'}
    
    try:
        # Check if it's a GCS URL
        parsed = urlparse(audio_url)
        if 'storage.googleapis.com' in parsed.netloc:
            # Extract blob path
            path_parts = parsed.path.lstrip('/').split('/')
            if path_parts[0] == BUCKET_NAME:
                blob_path = '/'.join(path_parts[1:])
            else:
                blob_path = parsed.path.lstrip('/')
            
            # Check if blob exists
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(blob_path)
            
            exists = blob.exists()
            if exists:
                blob.reload()
                size = blob.size
                # Check if size is reasonable (> 100KB)
                is_valid_size = size > 100 * 1024
                
                # Try to download first few bytes to check integrity
                try:
                    chunk = blob.download_as_bytes(start=0, end=min(1024, size-1))
                    has_data = len(chunk) > 0
                    # Check for MP3 header (starts with ID3 or FF FB/FF F3 for MPEG)
                    is_mp3 = (chunk[:3] == b'ID3' or 
                             (chunk[0] == 0xFF and chunk[1] in [0xFB, 0xF3, 0xFA, 0xF2]))
                except Exception as e:
                    has_data = False
                    is_mp3 = False
                
                return {
                    'exists': True,
                    'accessible': True,
                    'size': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'valid_size': is_valid_size,
                    'has_data': has_data,
                    'is_mp3': is_mp3,
                    'path': blob_path
                }
            else:
                return {'exists': False, 'accessible': False, 'error': f'Blob not found: {blob_path}'}
        else:
            # External URL - check with HEAD request
            try:
                response = requests.head(audio_url, timeout=10, allow_redirects=True)
                accessible = response.status_code == 200
                size = int(response.headers.get('Content-Length', 0))
                return {
                    'exists': True,
                    'accessible': accessible,
                    'size': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'http_status': response.status_code
                }
            except Exception as e:
                return {'exists': False, 'accessible': False, 'error': str(e)}
    except Exception as e:
        return {'exists': False, 'accessible': False, 'error': str(e)}

def main():
    print("🔍 Diagnosing YouTube Audio Corruption Issues")
    print("="*80)
    
    # Failed podcast titles from YouTube
    failed_titles = [
        "Quantum Computing Advances",
        "Silicon compounds",
        "Quantum Computing chip advances",
        "Prime Number Theory update",
        "New materials created using AI",
        "Matrix Multiplication advances"
    ]
    
    admin_key = get_admin_api_key()
    headers = {
        "X-Admin-API-Key": admin_key,
        "Content-Type": "application/json"
    }
    
    print(f"\n📋 Searching for {len(failed_titles)} failed podcasts...")
    
    # Get all podcasts from database
    url = f"{API_BASE_URL}/api/admin/podcasts/database"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error fetching database: HTTP {response.status_code}")
        print(response.text)
        return
    
    db_data = response.json()
    all_podcasts = db_data.get("podcasts", [])
    
    print(f"✅ Found {len(all_podcasts)} total podcasts in database")
    
    # Find matching podcasts
    found_podcasts = []
    for failed_title in failed_titles:
        # Try exact match first
        match = None
        for podcast in all_podcasts:
            title = podcast.get('title', '')
            # Check for exact match or partial match
            if title.lower() == failed_title.lower() or failed_title.lower() in title.lower():
                match = podcast
                break
        
        if match:
            found_podcasts.append({
                'search_title': failed_title,
                'found_title': match.get('title'),
                'podcast': match
            })
        else:
            found_podcasts.append({
                'search_title': failed_title,
                'found_title': None,
                'podcast': None
            })
    
    print("\n" + "="*80)
    print("DIAGNOSIS RESULTS")
    print("="*80)
    
    found_count = sum(1 for f in found_podcasts if f['podcast'])
    not_found_count = len(found_podcasts) - found_count
    
    print(f"\n✅ Found: {found_count}/{len(failed_titles)}")
    print(f"❌ Not Found: {not_found_count}/{len(failed_titles)}")
    
    # Diagnose each found podcast
    for item in found_podcasts:
        print("\n" + "-"*80)
        search_title = item['search_title']
        podcast = item['podcast']
        
        if not podcast:
            print(f"❌ NOT FOUND: {search_title}")
            print("   Podcast not found in database")
            continue
        
        found_title = item['found_title']
        canonical = podcast.get('canonical_filename', 'Unknown')
        audio_url = podcast.get('audio_url') or ''
        
        print(f"📻 {found_title}")
        print(f"   Canonical: {canonical}")
        if audio_url:
            print(f"   Audio URL: {audio_url[:80]}..." if len(audio_url) > 80 else f"   Audio URL: {audio_url}")
        else:
            print(f"   Audio URL: (missing)")
        
        # Check audio file
        print(f"   Checking audio file...")
        audio_check = check_audio_file(audio_url)
        
        if audio_check.get('exists'):
            print(f"   ✅ File exists")
            print(f"   📦 Size: {audio_check.get('size_mb', 0)} MB ({audio_check.get('size', 0)} bytes)")
            
            if audio_check.get('valid_size'):
                print(f"   ✅ Size is valid (>100KB)")
            else:
                print(f"   ⚠️  Size is suspiciously small")
            
            if audio_check.get('is_mp3'):
                print(f"   ✅ Has valid MP3 header")
            else:
                print(f"   ⚠️  MP3 header not detected")
            
            if not audio_check.get('has_data'):
                print(f"   ❌ File appears to be empty or corrupt")
        else:
            print(f"   ❌ File does NOT exist or is not accessible")
            if audio_check.get('error'):
                print(f"   Error: {audio_check.get('error')}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    issues_found = []
    for item in found_podcasts:
        if item['podcast']:
            audio_url = item['podcast'].get('audio_url', '')
            audio_check = check_audio_file(audio_url)
            if not audio_check.get('exists') or not audio_check.get('is_mp3'):
                issues_found.append({
                    'title': item['found_title'],
                    'canonical': item['podcast'].get('canonical_filename'),
                    'issue': 'Missing' if not audio_check.get('exists') else 'Invalid MP3'
                })
    
    if issues_found:
        print(f"\n⚠️  Found {len(issues_found)} podcasts with audio issues:")
        for issue in issues_found:
            print(f"  - {issue['title']} ({issue['canonical']}): {issue['issue']}")
    else:
        print(f"\n✅ All found podcasts have valid audio files")
    
    if not_found_count > 0:
        print(f"\n⚠️  {not_found_count} podcasts not found in database:")
        for item in found_podcasts:
            if not item['podcast']:
                print(f"  - {item['search_title']}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

