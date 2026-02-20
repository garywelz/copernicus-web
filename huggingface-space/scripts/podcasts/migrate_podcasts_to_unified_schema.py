#!/usr/bin/env python3
"""
Migrate Podcast JSON to Unified Schema

Adds cross-modal linking fields (related_papers, related_videos, related_processes)
and ensures ID format matches unified schema requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import re

def extract_paper_id_from_reference(ref: Dict) -> str:
    """Extract paper ID from reference object."""
    # Check for DOI
    if "doi" in ref:
        doi = ref["doi"]
        if doi.startswith("10."):
            return f"crossref_{doi.replace('/', '_').replace('.', '_')}"
    # Check URL for arXiv or PubMed
    if "url" in ref:
        url = ref["url"]
        # Extract arXiv ID from URL
        arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', url)
        if arxiv_match:
            return f"arxiv_{arxiv_match.group(1)}"
        # Extract PubMed ID from URL
        pubmed_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        if pubmed_match:
            return f"pubmed_{pubmed_match.group(1)}"
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
    elif isinstance(podcast.get("References"), list):
        # Check for "References" with capital R
        for ref in podcast["References"]:
            paper_id = extract_paper_id_from_reference(ref)
            if paper_id:
                if "paper_id" not in ref:
                    ref["paper_id"] = paper_id
                related_papers.append(paper_id)
        # Normalize to lowercase
        podcast["references"] = podcast.pop("References", [])
    
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
    
    # Ensure category exists (should already be present)
    if "category" not in podcast:
        # Try to infer from guid or title
        if "guid" in podcast:
            if "bio" in podcast["guid"]:
                podcast["category"] = "biology"
            elif "chem" in podcast["guid"]:
                podcast["category"] = "chemistry"
            else:
                podcast["category"] = "interdisciplinary"
    
    # Add subcategories array if missing
    if "subcategories" not in podcast:
        podcast["subcategories"] = []
    
    # Add keywords array if missing (extract from tags if available)
    if "keywords" not in podcast:
        podcast["keywords"] = []
        # Could extract from description/tags if needed
    
    # Ensure year exists (extract from published date or current year)
    if "year" not in podcast:
        # Could extract from published_date if available
        podcast["year"] = datetime.now().strftime("%Y")
    
    return podcast

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate podcasts.json to unified schema")
    parser.add_argument("file", help="Path to podcasts.json file")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify file, just show what would change")
    parser.add_argument("--backup", action="store_true", help="Create backup file before modifying")
    args = parser.parse_args()
    
    podcasts_file = Path(args.file)
    if not podcasts_file.exists():
        print(f"Error: File not found: {podcasts_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(podcasts_file, 'r') as f:
            podcasts = json.load(f)
        
        if not isinstance(podcasts, list):
            print("Error: podcasts.json should be an array", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error loading podcasts file: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(podcasts)} podcasts")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
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
    print(f"Summary: {migrated_count}/{len(podcasts)} podcasts would be migrated")
    
    if not args.dry_run:
        # Create backup if requested
        if args.backup:
            backup_file = podcasts_file.with_suffix('.json.backup')
            with open(backup_file, 'w') as f:
                json.dump(podcasts, f, indent=2)
            print(f"Backup created: {backup_file}")
        
        # Write migrated version
        with open(podcasts_file, 'w') as f:
            json.dump(migrated_podcasts, f, indent=2, ensure_ascii=False)
        
        print(f"Migrated {len(podcasts)} podcasts to unified schema")

if __name__ == "__main__":
    main()
