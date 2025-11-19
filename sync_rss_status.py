#!/usr/bin/env python3
"""
Sync Firestore episode catalog with RSS feed status.

This script:
1. Reads the RSS feed from Google Cloud Storage
2. Extracts all episode GUIDs from the RSS feed
3. Updates Firestore podcast_jobs collection to set submitted_to_rss: true
   for all episodes that appear in the RSS feed

Usage:
    python3 sync_rss_status.py              # Run sync
    python3 sync_rss_status.py --dry-run    # Preview changes without updating

Requirements:
    - GCP authentication (via gcloud auth application-default login or service account)
    - Environment variables:
      - GOOGLE_CLOUD_PROJECT (default: regal-scholar-453620-r7)
      - GCP_AUDIO_BUCKET (default: regal-scholar-453620-r7-podcast-storage)
    - Python packages: google-cloud-firestore, google-cloud-storage

The script will:
    - Fetch RSS feed from GCS public URL
    - Parse all episode GUIDs from RSS items
    - Update Firestore documents where document ID matches RSS GUID
    - Report statistics on what was updated
"""

import os
import sys
import xml.etree.ElementTree as ET
from typing import Set, List
from datetime import datetime
import urllib.request
import urllib.error

# Google Cloud imports
try:
    from google.cloud import firestore
    from google.cloud import storage
except ImportError as e:
    print(f"❌ Error importing Google Cloud libraries: {e}")
    print("Install with: pip install google-cloud-firestore google-cloud-storage")
    sys.exit(1)

# Configuration
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "regal-scholar-453620-r7")
GCS_BUCKET = os.getenv("GCP_AUDIO_BUCKET", "regal-scholar-453620-r7-podcast-storage")
RSS_FEED_PATH = "feeds/copernicus-mvp-rss-feed.xml"
FIRESTORE_DATABASE = "copernicusai"

# RSS feed URL (public)
RSS_FEED_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/{RSS_FEED_PATH}"


def fetch_rss_feed() -> str:
    """Fetch RSS feed from GCS (using public URL)"""
    print(f"📡 Fetching RSS feed from: {RSS_FEED_URL}")
    try:
        with urllib.request.urlopen(RSS_FEED_URL, timeout=30) as response:
            content = response.read().decode('utf-8')
            print(f"✅ Successfully fetched RSS feed ({len(content)} bytes)")
            return content
    except urllib.error.URLError as e:
        print(f"❌ Error fetching RSS feed: {e}")
        # Try alternative: read directly from GCS
        print("🔄 Attempting to read directly from GCS...")
        try:
            storage_client = storage.Client(project=GCP_PROJECT_ID)
            bucket = storage_client.bucket(GCS_BUCKET)
            blob = bucket.blob(RSS_FEED_PATH)
            if not blob.exists():
                raise FileNotFoundError(f"RSS feed not found at gs://{GCS_BUCKET}/{RSS_FEED_PATH}")
            content = blob.download_as_text()
            print(f"✅ Successfully read RSS feed from GCS ({len(content)} bytes)")
            return content
        except Exception as gcs_error:
            print(f"❌ Error reading from GCS: {gcs_error}")
            raise


def extract_guids_from_rss(rss_content: str) -> Set[str]:
    """Extract all GUIDs from RSS feed"""
    print("🔍 Parsing RSS feed to extract episode GUIDs...")
    guids = set()
    
    try:
        # Parse XML
        root = ET.fromstring(rss_content)
        
        # Find all <item> elements
        items = root.findall(".//item")
        print(f"📋 Found {len(items)} items in RSS feed")
        
        for item in items:
            guid_elem = item.find("guid")
            if guid_elem is not None:
                guid_text = guid_elem.text
                if guid_text:
                    guids.add(guid_text.strip())
                    print(f"  ✓ Found GUID: {guid_text.strip()}")
        
        print(f"✅ Extracted {len(guids)} unique GUIDs from RSS feed")
        return guids
        
    except ET.ParseError as e:
        print(f"❌ Error parsing RSS XML: {e}")
        raise
    except Exception as e:
        print(f"❌ Error extracting GUIDs: {e}")
        raise


def sync_firestore_with_rss(rss_guids: Set[str], dry_run: bool = False) -> dict:
    """Update Firestore to match RSS feed status"""
    print(f"\n🔄 {'[DRY RUN] ' if dry_run else ''}Syncing Firestore with RSS feed...")
    
    try:
        # Initialize Firestore client
        print(f"🔌 Connecting to Firestore (project: {GCP_PROJECT_ID}, database: {FIRESTORE_DATABASE})...")
        db = firestore.Client(project=GCP_PROJECT_ID, database=FIRESTORE_DATABASE)
        print("✅ Firestore client initialized")
        
        # Get all podcast_jobs documents
        print("📚 Fetching all podcast_jobs from Firestore...")
        podcast_jobs_ref = db.collection('podcast_jobs')
        all_podcasts = list(podcast_jobs_ref.stream())
        print(f"📊 Found {len(all_podcasts)} total podcast jobs in Firestore")
        
        # Track statistics
        stats = {
            'total_in_firestore': len(all_podcasts),
            'total_in_rss': len(rss_guids),
            'matched_and_updated': 0,
            'matched_already_true': 0,
            'not_in_rss_but_marked_true': 0,
            'errors': []
        }
        
        # Update documents that are in RSS feed
        print(f"\n📝 Updating documents that appear in RSS feed ({len(rss_guids)} episodes)...")
        for podcast_doc in all_podcasts:
            doc_id = podcast_doc.id
            doc_data = podcast_doc.to_dict()
            current_status = doc_data.get('submitted_to_rss', False)
            
            if doc_id in rss_guids:
                # This episode is in RSS feed
                if current_status is True:
                    stats['matched_already_true'] += 1
                    print(f"  ✓ {doc_id}: Already marked as submitted_to_rss=true")
                else:
                    stats['matched_and_updated'] += 1
                    if not dry_run:
                        try:
                            podcast_doc.reference.update({
                                'submitted_to_rss': True,
                                'rss_synced_at': datetime.utcnow().isoformat()
                            })
                            print(f"  ✅ {doc_id}: Updated submitted_to_rss=true")
                        except Exception as e:
                            error_msg = f"Error updating {doc_id}: {e}"
                            stats['errors'].append(error_msg)
                            print(f"  ❌ {error_msg}")
                    else:
                        print(f"  [DRY RUN] Would update {doc_id}: submitted_to_rss=false -> true")
            else:
                # This episode is NOT in RSS feed
                if current_status is True:
                    stats['not_in_rss_but_marked_true'] += 1
                    print(f"  ⚠️  {doc_id}: Marked as submitted_to_rss=true but NOT in RSS feed")
                    # Optionally set to false - uncomment if desired
                    # if not dry_run:
                    #     podcast_doc.reference.update({'submitted_to_rss': False})
        
        # Check for RSS GUIDs that don't exist in Firestore
        print(f"\n🔍 Checking for RSS GUIDs not found in Firestore...")
        firestore_doc_ids = {doc.id for doc in all_podcasts}
        missing_in_firestore = rss_guids - firestore_doc_ids
        if missing_in_firestore:
            print(f"  ⚠️  Found {len(missing_in_firestore)} GUIDs in RSS feed that don't exist in Firestore:")
            for guid in sorted(missing_in_firestore):
                print(f"    - {guid}")
        else:
            print(f"  ✅ All RSS GUIDs found in Firestore")
        
        return stats
        
    except Exception as e:
        print(f"❌ Error syncing Firestore: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main execution function"""
    print("=" * 70)
    print("🔄 RSS Feed to Firestore Sync Script")
    print("=" * 70)
    print(f"Project: {GCP_PROJECT_ID}")
    print(f"Database: {FIRESTORE_DATABASE}")
    print(f"RSS Feed: {RSS_FEED_URL}")
    print("=" * 70)
    print()
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made to Firestore\n")
    
    try:
        # Step 1: Fetch RSS feed
        rss_content = fetch_rss_feed()
        
        # Step 2: Extract GUIDs
        rss_guids = extract_guids_from_rss(rss_content)
        
        if not rss_guids:
            print("⚠️  No GUIDs found in RSS feed. Exiting.")
            return
        
        # Step 3: Sync Firestore
        stats = sync_firestore_with_rss(rss_guids, dry_run=dry_run)
        
        # Step 4: Print summary
        print("\n" + "=" * 70)
        print("📊 SYNC SUMMARY")
        print("=" * 70)
        print(f"Total episodes in RSS feed: {stats['total_in_rss']}")
        print(f"Total podcast jobs in Firestore: {stats['total_in_firestore']}")
        print(f"Episodes updated to submitted_to_rss=true: {stats['matched_and_updated']}")
        print(f"Episodes already marked as submitted_to_rss=true: {stats['matched_already_true']}")
        print(f"Episodes in Firestore but NOT in RSS (marked true): {stats['not_in_rss_but_marked_true']}")
        if stats['errors']:
            print(f"\n❌ Errors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        print("=" * 70)
        
        if dry_run:
            print("\n⚠️  This was a DRY RUN. Run without --dry-run to apply changes.")
        else:
            print("\n✅ Sync completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
