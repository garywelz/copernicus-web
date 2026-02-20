#!/usr/bin/env python3
"""
Review and update all episode descriptions to meet new standards:
1. Limited to 4000 characters (preserving References and Hashtags)
2. Reference URLs converted to clickable markdown links
3. References section always preserved
"""

import os
import sys
from google.cloud import firestore
from typing import Dict, List, Optional
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.constants import EPISODE_COLLECTION_NAME
from content_fixes import limit_description_length
from services.rss_service import RSSService
from services.episode_service import EpisodeService

def check_description_standards(description: str) -> Dict:
    """Check if description meets all standards"""
    issues = []
    
    if not description:
        return {"needs_fix": True, "issues": ["Description is empty"]}
    
    # Check 1: Length <= 4000
    if len(description) > 4000:
        issues.append(f"Exceeds 4000 chars ({len(description)} chars)")
    
    # Check 2: References section should have clickable links
    has_references = '## References' in description
    if has_references:
        # Check if references have markdown links
        ref_section_start = description.find('## References')
        if ref_section_start >= 0:
            # Get references section (until next section or end)
            ref_section = description[ref_section_start:]
            for marker in ['## Hashtags', '## Episode Details']:
                if marker in ref_section:
                    ref_section = ref_section.split(marker)[0]
                    break
            
            # Check for URLs that aren't in markdown link format
            import re
            url_pattern = r'(https?://[^\s\)\n]+|10\.\d{4}/[^\s\)\n]+)'
            # Find URLs that are NOT already in markdown link format
            urls_in_section = re.findall(url_pattern, ref_section)
            markdown_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', ref_section)
            linked_urls = {url for _, url in markdown_links}
            
            unlinked_urls = []
            for url in urls_in_section:
                # Check if this URL is already linked
                if not any(url in linked_url for linked_url in linked_urls):
                    # Check if it's part of "Available: URL" or "DOI: URL" pattern
                    url_pos = ref_section.find(url)
                    if url_pos >= 0:
                        context_before = ref_section[max(0, url_pos-20):url_pos]
                        if 'Available:' not in context_before and 'DOI:' not in context_before:
                            unlinked_urls.append(url)
                        elif not any(url in link for _, link in markdown_links):
                            # URL follows "Available:" or "DOI:" but isn't linked
                            unlinked_urls.append(url)
            
            if unlinked_urls:
                issues.append(f"References have {len(unlinked_urls)} unlinked URLs")
    
    return {
        "needs_fix": len(issues) > 0,
        "issues": issues,
        "length": len(description)
    }

def fix_description(description: str) -> str:
    """Apply all fixes to description"""
    if not description:
        return description
    
    # Step 1: Convert reference URLs to clickable markdown links
    description = RSSService._make_reference_links_clickable(description)
    
    # Step 2: Limit length to 4000 chars while preserving references
    description = limit_description_length(description, 4000)
    
    return description

def update_episode_description(episode_id: str, new_description: str, dry_run: bool = False) -> bool:
    """Update episode description in Firestore, GCS, and RSS feed"""
    try:
        db_client = firestore.Client(database="copernicusai")
        doc_ref = db_client.collection(EPISODE_COLLECTION_NAME).document(episode_id)
        
        # Check if document exists
        doc_snapshot = doc_ref.get()
        if not doc_snapshot.exists:
            print(f"   ⚠️  Episode {episode_id} not found in episodes collection")
            return False
        
        episode_data = doc_snapshot.to_dict()
        canonical_filename = episode_data.get('canonical_filename', episode_id)
        submitted_to_rss = episode_data.get('submitted_to_rss', False)
        
        if dry_run:
            print(f"   [DRY RUN] Would update:")
            print(f"      - Firestore: episodes/{episode_id}")
            print(f"      - GCS: descriptions/{canonical_filename}.md")
            if submitted_to_rss:
                print(f"      - RSS feed (episode is in RSS)")
            return True
        
        # Convert markdown to HTML and generate summary
        description_html = EpisodeService._markdown_to_html(new_description)
        from content_fixes import extract_itunes_summary
        summary_text = extract_itunes_summary(new_description)
        
        # Step 1: Update Firestore database
        doc_ref.update({
            'description_markdown': new_description,
            'description_html': description_html,
            'summary': summary_text,
            'updated_at': datetime.utcnow().isoformat()
        })
        print(f"   ✅ Updated Firestore")
        
        # Step 2: Upload to GCS descriptions folder
        try:
            from google.cloud import storage
            storage_client = storage.Client()
            bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
            description_filename = f"{canonical_filename}.md"
            blob = bucket.blob(f"descriptions/{description_filename}")
            blob.upload_from_string(new_description, content_type="text/markdown")
            blob.make_public()
            print(f"   ✅ Updated GCS: descriptions/{description_filename}")
        except Exception as e:
            print(f"   ⚠️  Warning: Failed to update GCS: {e}")
        
        # Step 3: Update RSS feed if episode is submitted to RSS
        if submitted_to_rss:
            try:
                from services.rss_service import RSSService
                # Get subscriber data if available
                subscriber_id = episode_data.get('subscriber_id')
                subscriber_data = None
                if subscriber_id:
                    subscriber_doc = db_client.collection('subscribers').document(subscriber_id).get()
                    if subscriber_doc.exists:
                        subscriber_data = subscriber_doc.to_dict()
                
                # Get attribution
                attribution_initials = episode_data.get('creator_attribution')
                
                # Create podcast_data structure for RSS update
                podcast_data = {
                    'result': {
                        **episode_data,
                        'description': new_description,
                    },
                    'request': episode_data.get('request', {})
                }
                
                # Update RSS feed (sync wrapper for async method)
                import asyncio
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
        print(f"   ❌ Error updating episode {episode_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Update all episode descriptions to meet new standards")
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of episodes to process')
    parser.add_argument('--fix-only', action='store_true', help='Only show episodes that need fixes')
    args = parser.parse_args()
    
    print("🔍 Reviewing all episode descriptions...")
    print()
    
    try:
        db_client = firestore.Client(database="copernicusai")
        
        # Query all episodes
        query = db_client.collection(EPISODE_COLLECTION_NAME).order_by('generated_at', direction=firestore.Query.DESCENDING)
        if args.limit:
            query = query.limit(args.limit)
        
        episodes = list(query.stream())
        print(f"Found {len(episodes)} episodes to review")
        print()
        
        needs_fix_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for doc in episodes:
            episode_id = doc.id
            episode_data = doc.to_dict() or {}
            description_markdown = episode_data.get('description_markdown', '') or episode_data.get('description', '')
            title = episode_data.get('title', 'Untitled')
            
            if not description_markdown:
                skipped_count += 1
                if not args.fix_only:
                    print(f"⏭️  {episode_id}: {title} - No description to process")
                continue
            
            # Check if description meets standards
            check_result = check_description_standards(description_markdown)
            
            if check_result['needs_fix']:
                needs_fix_count += 1
                print(f"🔧 {episode_id}: {title}")
                print(f"   Issues: {', '.join(check_result['issues'])}")
                print(f"   Current length: {check_result['length']} chars")
                
                # Fix description
                fixed_description = fix_description(description_markdown)
                new_check = check_description_standards(fixed_description)
                
                print(f"   Fixed length: {new_check['length']} chars")
                if new_check['needs_fix']:
                    print(f"   ⚠️  Still has issues after fix: {', '.join(new_check['issues'])}")
                
                # Update in database
                if update_episode_description(episode_id, fixed_description, dry_run=args.dry_run):
                    updated_count += 1
                    if not args.dry_run:
                        print(f"   ✅ Updated successfully")
                    else:
                        print(f"   [DRY RUN] Would update")
                else:
                    error_count += 1
                    print(f"   ❌ Failed to update")
                print()
            else:
                if not args.fix_only:
                    print(f"✅ {episode_id}: {title} - Already meets standards ({check_result['length']} chars)")
        
        # Summary
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total episodes reviewed: {len(episodes)}")
        print(f"Episodes needing fixes: {needs_fix_count}")
        print(f"Episodes updated: {updated_count}")
        print(f"Episodes skipped (no description): {skipped_count}")
        print(f"Errors: {error_count}")
        
        if args.dry_run:
            print()
            print("⚠️  DRY RUN MODE - No changes were made")
            print("   Run without --dry-run to apply updates")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

