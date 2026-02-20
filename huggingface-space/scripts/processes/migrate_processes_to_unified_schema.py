#!/usr/bin/env python3
"""
Migrate Process JSON Files to Unified Schema

Adds cross-modal linking fields (related_papers, related_videos, related_podcasts)
and ensures ID format matches unified schema requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import re

def extract_paper_id_from_source(source: Dict) -> str:
    """Extract paper ID from source object."""
    # Check for pubmed ID
    if "pubmed" in source and source["pubmed"]:
        return f"pubmed_{source['pubmed']}"
    # Check for DOI
    if "doi" in source and source["doi"]:
        doi = source["doi"]
        # Convert DOI to crossref ID format if possible
        if doi.startswith("10."):
            return f"crossref_{doi.replace('/', '_').replace('.', '_')}"
    # Check URL for arXiv or other identifiers
    if "url" in source and source["url"]:
        url = source["url"]
        # Extract arXiv ID from URL
        arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', url)
        if arxiv_match:
            return f"arxiv_{arxiv_match.group(1)}"
        # Extract PubMed ID from URL
        pubmed_match = re.search(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d+)', url)
        if pubmed_match:
            return f"pubmed_{pubmed_match.group(1)}"
    return None

def migrate_process(process: Dict) -> Dict:
    """
    Migrate a single process to unified schema format.
    Returns updated process dict.
    """
    # Ensure ID is in correct format
    if "id" in process and process["id"] is not None:
        process_id = process["id"]
        # Check if it already follows format: process_{category}_{name}
        if not process_id.startswith("process_"):
            # Convert to proper format
            category = process.get("category", "unknown")
            name = process.get("name", "unknown").lower().replace(" ", "-")
            process["id"] = f"process_{category}_{name}"
    else:
        # Generate ID if missing or None
        category = process.get("category", "unknown")
        name = process.get("name", "unknown").lower().replace(" ", "-")
        # Use filename pattern if name not available
        if name == "unknown":
            # Try to extract from other fields
            if "subcategory" in process and process["subcategory"]:
                name = process["subcategory"].lower().replace("_", "-")
        process["id"] = f"process_{category}_{name}"
    
    # Extract related papers from sources
    related_papers = []
    if "sources" in process and isinstance(process["sources"], list):
        for source in process["sources"]:
            # Add paper_id to source if we can extract it
            paper_id = extract_paper_id_from_source(source)
            if paper_id:
                source["paper_id"] = paper_id
                related_papers.append(paper_id)
    
    # Add related_papers array
    if "related_papers" not in process:
        process["related_papers"] = related_papers
    else:
        # Merge with existing
        existing = set(process["related_papers"])
        existing.update(related_papers)
        process["related_papers"] = list(existing)
    
    # Migrate relatedProcesses to related_processes (camelCase to snake_case)
    if "relatedProcesses" in process and "related_processes" not in process:
        process["related_processes"] = process["relatedProcesses"]
        # Don't delete relatedProcesses for backward compatibility
    
    # Ensure related_processes exists
    if "related_processes" not in process:
        process["related_processes"] = []
    
    # Add other cross-modal linking arrays if missing
    if "related_videos" not in process:
        process["related_videos"] = []
    if "related_podcasts" not in process:
        process["related_podcasts"] = []
    
    # Add acquired_date if missing
    if "acquired_date" not in process:
        # Use created date if available, otherwise use current date
        if "created" in process:
            try:
                # Convert created date to ISO format
                created = process["created"]
                if isinstance(created, str):
                    # Assume YYYY-MM-DD format
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', created):
                        process["acquired_date"] = f"{created}T00:00:00Z"
                    else:
                        process["acquired_date"] = datetime.now().isoformat() + "Z"
                else:
                    process["acquired_date"] = datetime.now().isoformat() + "Z"
            except:
                process["acquired_date"] = datetime.now().isoformat() + "Z"
        else:
            process["acquired_date"] = datetime.now().isoformat() + "Z"
    
    # Ensure source field exists
    if "source" not in process:
        # Determine source from category or default
        if "glmp" in process.get("id", "").lower() or "glmp" in process.get("subcategory", "").lower():
            process["source"] = "glmp"
        else:
            process["source"] = "programming_framework"
    
    # Add subcategories array if missing (from subcategory field)
    if "subcategories" not in process and "subcategory" in process:
        process["subcategories"] = [process["subcategory"]]
    
    return process

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate process JSON files to unified schema")
    parser.add_argument("directory", help="Directory containing process JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files, just show what would change")
    parser.add_argument("--backup", action="store_true", help="Create backup files before modifying")
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)
    
    # Find all JSON files
    json_files = list(directory.rglob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    migrated_count = 0
    skipped_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                process = json.load(f)
            
            original_process = json.dumps(process, indent=2, sort_keys=True)
            migrated_process = migrate_process(process.copy())
            migrated_json = json.dumps(migrated_process, indent=2, sort_keys=True)
            
            # Check if anything changed
            if original_process != migrated_json:
                print(f"Migrating: {json_file}")
                
                # Show changes
                if "related_papers" in migrated_process and migrated_process["related_papers"]:
                    print(f"  Added {len(migrated_process['related_papers'])} related papers")
                
                if not args.dry_run:
                    # Create backup if requested
                    if args.backup:
                        backup_file = json_file.with_suffix('.json.backup')
                        with open(backup_file, 'w') as f:
                            f.write(original_process)
                    
                    # Write migrated version
                    with open(json_file, 'w') as f:
                        f.write(migrated_json)
                
                migrated_count += 1
            else:
                skipped_count += 1
                
        except Exception as e:
            print(f"Error processing {json_file}: {e}", file=sys.stderr)
    
    print()
    print(f"Summary:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped (no changes): {skipped_count}")
    print(f"  Total: {len(json_files)}")

if __name__ == "__main__":
    main()
