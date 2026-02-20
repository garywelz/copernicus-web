#!/usr/bin/env python3
"""
Re-apply description updates to GCS and RSS for episodes that were previously
updated in Firestore but may not have had GCS/RSS updates.

This script will:
1. Find episodes that need description fixes
2. Update Firestore, GCS, and RSS feed
"""

import os
import sys
from google.cloud import firestore, storage
from typing import Dict
import argparse
from datetime import datetime
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.constants import EPISODE_COLLECTION_NAME
from content_fixes import limit_description_length
from services.rss_service import RSSService
from services.episode_service import EpisodeService

def fix_description(description: str) -> str:
    """Apply all fixes to description"""
    if not description:
        return description
    
    # Step 1: Convert reference URLs to clickable markdown links
    description = RSSService._make_reference_links_clickable(description)
    
    # Step 2: Limit length to 4000 chars while preserving references
    description = limit_description_length(description, 4000)
    
    return description

def update_all_locations(episode_id: str, episode_data: Dict, new_description: str, dry_run: bool = False) -> bool:
    """Update description in Firestore, GCS, and RSS feed"""
    try:
        # Use canonical_filename if available, otherwise use episode_id
        canonical_filename = episode_data.get('canonical_filename') or episode_id
        # Ensure we use the episode_id as the document ID, not canonical_filename
        print(f"   Episode ID: {episode_id}, Canonical: {canonical_filename}")
        submitted_to_rss = episode_data.get('submitted_to_rss', False)
        
        if dry_run:
            print(f"   [DRY RUN] Would update:")
            print(f"      - Firestore: episodes/{episode_id}")
            print(f"      - GCS: descriptions/{canonical_filename}.md")
            if submitted_to_rss:
                print(f"      - RSS feed (episode is in RSS)")
            return True
        
        db_client = firestore.Client(database="copernicusai")
        
        # Step 1: Update Firestore
        doc_ref = db_client.collection(EPISODE_COLLECTION_NAME).document(episode_id)
        description_html = EpisodeService._markdown_to_html(new_description)
        from content_fixes import extract_itunes_summary
        summary_text = extract_itunes_summary(new_description)
        
        doc_ref.update({
            'description_markdown': new_description,
            'description_html': description_html,
            'summary': summary_text,
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"   ✅ Updated Firestore")
        
        # Step 2: Update GCS
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            description_filename = f"{canonical_filename}.md"
            blob = bucket.blob(f"descriptions/{description_filename}")
            blob.upload_from_string(new_description, content_type="text/markdown")
            blob.make_public()
            print(f"   ✅ Updated GCS: descriptions/{description_filename}")
        except Exception as e:
            print(f"   ⚠️  Warning: Failed to update GCS: {e}")
        
        # Step 3: Update RSS feed if submitted
        if submitted_to_rss:
            try:
                subscriber_id = episode_data.get('subscriber_id')
                subscriber_data = None
                if subscriber_id:
                    subscriber_doc = db_client.collection('subscribers').document(subscriber_id).get()
                    if subscriber_doc.exists:
                        subscriber_data = subscriber_doc.to_dict()
                
                attribution_initials = episode_data.get('creator_attribution')
                
                podcast_data = {
                    'result': {
                        **episode_data,
                        'description': new_description,
                    },
                    'request': episode_data.get('request', {})
                }
                
                # Update RSS feed (async)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(RSSService.update_rss_feed(
                        podcast_data,
                        subscriber_data,
                        submit_to_rss=True,
                        attribution_initials=attribution_initials
                    ))
                    print(f"   ✅ Updated RSS feed")
                finally:
                    loop.close()
            except Exception as e:
                print(f"   ⚠️  Warning: Failed to update RSS feed: {e}")
                import traceback
                traceback.print_exc()
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Re-apply description updates to GCS and RSS")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of episodes')
    parser.add_argument('--all', action='store_true', help='Update all episodes (not just those needing fixes)')
    args = parser.parse_args()
    
    print("🔄 Re-applying description updates to GCS and RSS...")
    print()
    
    try:
        db_client = firestore.Client(database="copernicusai")
        query = db_client.collection(EPISODE_COLLECTION_NAME).order_by('generated_at', direction=firestore.Query.DESCENDING)
        if args.limit:
            query = query.limit(args.limit)
        
        episodes = list(query.stream())
        print(f"Found {len(episodes)} episodes to process")
        print()
        
        updated_count = 0
        
        for doc in episodes:
            episode_id = doc.id
            episode_data = doc.to_dict() or {}
            description_markdown = episode_data.get('description_markdown', '') or episode_data.get('description', '')
            title = episode_data.get('title', 'Untitled')
            
            if not description_markdown:
                continue
            
            # Fix description
            fixed_description = fix_description(description_markdown)
            
            # Check if we need to update (if description changed or --all flag)
            if args.all or fixed_description != description_markdown:
                print(f"🔄 {episode_id}: {title}")
                if update_all_locations(episode_id, episode_data, fixed_description, dry_run=args.dry_run):
                    updated_count += 1
                print()
        
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total episodes processed: {len(episodes)}")
        print(f"Episodes updated: {updated_count}")
        
        if args.dry_run:
            print()
            print("⚠️  DRY RUN MODE - No changes were made")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
