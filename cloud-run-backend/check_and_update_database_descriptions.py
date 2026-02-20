#!/usr/bin/env python3
"""
Check if database descriptions match the fixed description.md files
and update them if they differ.
"""

import os
import sys
import requests
from google.cloud import storage, firestore
from typing import Dict, List, Optional
import argparse
from datetime import datetime

BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
DESC_PREFIX = "descriptions/"
PROJECT_ID = "regal-scholar-453620-r7"
DATABASE = "copernicusai"

def get_description_from_gcs(filename: str) -> Optional[str]:
    """Get description content from GCS"""
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"{DESC_PREFIX}{filename}")
        
        if not blob.exists():
            return None
        
        return blob.download_as_text()
    except Exception as e:
        print(f"   ❌ Error reading from GCS: {e}")
        return None

def get_episode_from_database(canonical_filename: str) -> Optional[Dict]:
    """Get episode data from Firestore"""
    try:
        db = firestore.Client(project=PROJECT_ID, database=DATABASE)
        
        # Try episodes collection first
        ep_doc = db.collection('episodes').document(canonical_filename).get()
        if ep_doc.exists:
            return {
                'collection': 'episodes',
                'data': ep_doc.to_dict(),
                'doc_id': canonical_filename
            }
        
        # Try podcast_jobs collection
        jobs_query = db.collection('podcast_jobs').where(
            'result.canonical_filename', '==', canonical_filename
        ).limit(1).stream()
        
        for job_doc in jobs_query:
            return {
                'collection': 'podcast_jobs',
                'data': job_doc.to_dict(),
                'doc_id': job_doc.id
            }
        
        return None
    except Exception as e:
        print(f"   ❌ Error reading from database: {e}")
        return None

def update_episode_description(episode_info: Dict, new_description: str, dry_run: bool = False) -> bool:
    """Update description in database"""
    try:
        db = firestore.Client(project=PROJECT_ID, database=DATABASE)
        collection = episode_info['collection']
        doc_id = episode_info['doc_id']
        doc_ref = db.collection(collection).document(doc_id)
        
        if collection == 'episodes':
            # Update episodes collection
            if dry_run:
                print(f"   [DRY RUN] Would update episodes/{doc_id}")
                return True
            
            # Convert markdown to HTML (simple conversion)
            from content_fixes import extract_itunes_summary
            from services.rss_service import RSSService
            
            description_html = RSSService._markdown_to_html(new_description)
            summary_text = extract_itunes_summary(new_description)
            
            doc_ref.update({
                'description_markdown': new_description,
                'description_html': description_html,
                'summary': summary_text,
                'updated_at': datetime.utcnow().isoformat()
            })
            return True
        
        elif collection == 'podcast_jobs':
            # Update podcast_jobs collection
            if dry_run:
                print(f"   [DRY RUN] Would update podcast_jobs/{doc_id}")
                return True
            
            doc_data = episode_info['data']
            result = doc_data.get('result', {})
            result['description'] = new_description
            result['description_markdown'] = new_description
            
            doc_ref.update({
                'result': result,
                'updated_at': datetime.utcnow().isoformat()
            })
            return True
        
        return False
    except Exception as e:
        print(f"   ❌ Error updating database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Check and update database descriptions')
    parser.add_argument('--dry-run', action='store_true', help='Check without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of files to check')
    parser.add_argument('--update', action='store_true', help='Actually update the database (default is just check)')
    args = parser.parse_args()
    
    if not args.update and not args.dry_run:
        print("⚠️  Running in check-only mode. Use --update to actually update, or --dry-run to simulate.")
        print()
    
    print("🔍 Checking database descriptions against fixed GCS files...")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    print()
    
    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    
    # List all description files
    blobs = list(bucket.list_blobs(prefix=DESC_PREFIX))
    description_files = [blob for blob in blobs if blob.name.endswith('.md')]
    
    if args.limit:
        description_files = description_files[:args.limit]
        print(f"Processing first {args.limit} files...")
        print()
    
    print(f"Found {len(description_files)} description files to check")
    print()
    
    # Statistics
    checked_count = 0
    matches_count = 0
    mismatches_count = 0
    updated_count = 0
    not_found_count = 0
    error_count = 0
    
    for blob in description_files:
        filename = blob.name.replace(DESC_PREFIX, '')
        canonical_filename = filename.replace('.md', '')
        
        try:
            # Get description from GCS
            gcs_description = get_description_from_gcs(filename)
            if not gcs_description:
                print(f"⚠️  {canonical_filename}: Not found in GCS")
                error_count += 1
                continue
            
            # Get episode from database
            episode_info = get_episode_from_database(canonical_filename)
            if not episode_info:
                print(f"⚠️  {canonical_filename}: Not found in database")
                not_found_count += 1
                continue
            
            checked_count += 1
            
            # Get database description
            db_data = episode_info['data']
            if episode_info['collection'] == 'episodes':
                db_description = db_data.get('description_markdown', '')
            else:  # podcast_jobs
                result = db_data.get('result', {})
                db_description = result.get('description', '') or result.get('description_markdown', '')
            
            # Compare
            gcs_clean = gcs_description.strip()
            db_clean = db_description.strip()
            
            if gcs_clean == db_clean:
                matches_count += 1
                if checked_count % 10 == 0:
                    print(f"✅ {canonical_filename}: Matches")
            else:
                mismatches_count += 1
                print(f"📝 {canonical_filename}: MISMATCH")
                print(f"   GCS length: {len(gcs_clean)} chars")
                print(f"   DB length: {len(db_clean)} chars")
                print(f"   Collection: {episode_info['collection']}")
                
                # Show first difference
                if gcs_clean[:100] != db_clean[:100]:
                    print(f"   GCS starts: {gcs_clean[:100]}...")
                    print(f"   DB starts:  {db_clean[:100]}...")
                
                # Update if requested
                if args.update or args.dry_run:
                    success = update_episode_description(episode_info, gcs_description, args.dry_run)
                    if success:
                        updated_count += 1
                        if not args.dry_run:
                            print(f"   ✅ Updated in database")
                print()
        
        except Exception as e:
            print(f"❌ Error processing {canonical_filename}: {e}")
            error_count += 1
            print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files checked: {checked_count}")
    print(f"Matches: {matches_count}")
    print(f"Mismatches: {mismatches_count}")
    print(f"Updated: {updated_count}")
    print(f"Not found in database: {not_found_count}")
    print(f"Errors: {error_count}")
    print()
    
    if args.dry_run:
        print("🔍 This was a DRY RUN - no changes were made")
        print("   Run with --update to actually update the database")
    elif args.update:
        print("✅ Database updates completed")
        print("   Note: RSS feed may need to be regenerated to reflect changes")
    else:
        print("ℹ️  Run with --update to update mismatched descriptions")
        print("   Or use --dry-run to simulate updates")

if __name__ == "__main__":
    main()


