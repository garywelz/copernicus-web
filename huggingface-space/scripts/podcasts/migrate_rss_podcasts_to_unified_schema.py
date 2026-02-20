#!/usr/bin/env python3
"""
Migrate RSS Feed Podcasts to Unified Schema

Extracts podcasts from RSS feed and migrates to unified schema format.
Source: Google Cloud Storage RSS feed, not local files.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import re

# Import RSS extraction
from extract_podcasts_from_rss import parse_rss_feed, extract_references, extract_keywords
import requests

# RSS feed URL
RSS_FEED_URL = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/feeds/copernicus-mvp-rss-feed.xml"

def extract_paper_id_from_reference(ref: Dict) -> str:
    """Extract paper ID from reference object."""
    # Check for paper_id directly
    if "paper_id" in ref:
        return ref["paper_id"]
    
    # Check for DOI
    if "doi" in ref:
        doi = ref["doi"]
        if doi.startswith("10."):
            return f"crossref_{doi.replace('/', '_').replace('.', '_')}"
    
    # Check for PMID
    if "pmid" in ref:
        return f"pubmed_{ref['pmid']}"
    
    # Check for arXiv ID
    if "arxiv_id" in ref:
        return f"arxiv_{ref['arxiv_id']}"
    
    return None

def migrate_podcast(podcast: Dict) -> Dict:
    """
    Migrate a single podcast to unified schema format.
    Returns updated podcast dict.
    """
    # Ensure ID is in correct format
    if "id" not in podcast:
        # Generate from guid if available
        if "guid" in podcast:
            podcast["id"] = f"podcast_{podcast['guid']}"
        else:
            # Generate from title (fallback)
            title_slug = re.sub(r'[^a-z0-9]+', '-', podcast.get("title", "unknown").lower())
            podcast["id"] = f"podcast_{title_slug}"
    else:
        # Ensure ID follows format
        podcast_id = podcast["id"]
        if not podcast_id.startswith("podcast_"):
            podcast["id"] = f"podcast_{podcast_id}"
    
    # Extract related papers from references
    related_papers = []
    if "references" in podcast and isinstance(podcast["references"], list):
        for ref in podcast["references"]:
            # Add paper_id to reference if we can extract it
            paper_id = extract_paper_id_from_reference(ref)
            if paper_id:
                ref["paper_id"] = paper_id
                related_papers.append(paper_id)
    
    # Add related_papers array
    if "related_papers" not in podcast:
        podcast["related_papers"] = related_papers
    else:
        # Merge with existing
        existing = set(podcast["related_papers"])
        existing.update(related_papers)
        podcast["related_papers"] = list(existing)
    
    # Add other cross-modal linking arrays if missing
    if "related_videos" not in podcast:
        podcast["related_videos"] = []
    if "related_processes" not in podcast:
        podcast["related_processes"] = []
    if "related_podcasts" not in podcast:
        podcast["related_podcasts"] = []
    
    # Add acquired_date if missing
    if "acquired_date" not in podcast:
        podcast["acquired_date"] = datetime.now().isoformat() + "Z"
    
    # Ensure source field exists
    if "source" not in podcast:
        podcast["source"] = "copernicus_ai"
    
    # Ensure category exists (should already be set)
    if "category" not in podcast:
        # Try to infer from guid or title
        guid_lower = podcast.get("guid", "").lower()
        if "bio" in guid_lower:
            podcast["category"] = "biology"
        elif "chem" in guid_lower:
            podcast["category"] = "chemistry"
        elif "phys" in guid_lower:
            podcast["category"] = "physics"
        elif "math" in guid_lower:
            podcast["category"] = "mathematics"
        elif "compsci" in guid_lower or "cs" in guid_lower:
            podcast["category"] = "computer_science"
        else:
            podcast["category"] = "interdisciplinary"
    
    # Add subcategories array if missing
    if "subcategories" not in podcast:
        podcast["subcategories"] = []
    
    # Add keywords array if missing (already extracted)
    if "keywords" not in podcast:
        podcast["keywords"] = []
    
    # Ensure year exists (extract from published date)
    # Already extracted in RSS parser if available
    
    return podcast

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate RSS feed podcasts to unified schema")
    parser.add_argument("--rss-url", default=RSS_FEED_URL, help="RSS feed URL")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--dry-run", action="store_true", help="Don't write file, just show what would change")
    args = parser.parse_args()
    
    print("=" * 70)
    print("Migrate RSS Feed Podcasts to Unified Schema")
    print("=" * 70)
    print(f"RSS Feed: {args.rss_url}")
    print(f"Output: {args.output}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    try:
        # Fetch RSS feed
        print("📥 Fetching RSS feed...")
        response = requests.get(args.rss_url, timeout=30)
        response.raise_for_status()
        rss_content = response.text
        print(f"✅ Fetched RSS feed ({len(rss_content)} bytes)")
        print()
        
        # Parse RSS feed
        print("📝 Parsing RSS feed...")
        podcasts = parse_rss_feed(rss_content)
        print(f"✅ Found {len(podcasts)} podcasts")
        print()
        
        # Migrate each podcast
        print("🔄 Migrating podcasts to unified schema...")
        migrated_podcasts = []
        migrated_count = 0
        
        for idx, podcast in enumerate(podcasts):
            migrated_podcast = migrate_podcast(podcast.copy())
            migrated_podcasts.append(migrated_podcast)
            
            # Check if anything changed
            changes = []
            if "related_papers" in migrated_podcast and migrated_podcast["related_papers"]:
                changes.append(f"Added {len(migrated_podcast['related_papers'])} related papers")
            if "id" not in podcast and "id" in migrated_podcast:
                changes.append(f"Generated ID: {migrated_podcast['id']}")
            if "acquired_date" not in podcast:
                changes.append("Added acquired_date")
            
            if changes:
                print(f"[{idx}] {podcast.get('title', 'Unknown')}: {', '.join(changes)}")
                migrated_count += 1
        
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total Podcasts: {len(migrated_podcasts)}")
        print(f"Migrated: {migrated_count}")
        print()
        
        # Count by category
        categories = {}
        for podcast in migrated_podcasts:
            cat = podcast.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        print("By Category:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
        
        print()
        
        # Count podcasts with related papers
        with_papers = sum(1 for p in migrated_podcasts if p.get("related_papers"))
        print(f"Podcasts with Related Papers: {with_papers}/{len(migrated_podcasts)}")
        
        if not args.dry_run:
            # Write migrated podcasts
            print()
            print(f"💾 Saving to {args.output}...")
            with open(args.output, 'w') as f:
                json.dump(migrated_podcasts, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(migrated_podcasts)} migrated podcasts to {args.output}")
        else:
            print()
            print("💡 Dry run complete - use without --dry-run to save")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
