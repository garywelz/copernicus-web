#!/usr/bin/env python3
"""
Add source citations to chemistry JSON files
"""

import json
import os
from pathlib import Path

# Default source for all chemistry processes
DEFAULT_SOURCE = {
    "title": "Programming Framework: A Universal Process Visualization Methodology",
    "authors": "Welz, G.",
    "journal": "CopernicusAI Knowledge Engine",
    "year": "2025",
    "url": "https://huggingface.co/spaces/garywelz/programming_framework",
    "doi": None,
    "notes": "Process visualization created using the Programming Framework methodology."
}

def add_sources_to_json(json_file_path: Path):
    """Add default source to a JSON file if sources are empty"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Only add if sources are empty
    if not data.get('sources') or len(data.get('sources', [])) == 0:
        data['sources'] = [DEFAULT_SOURCE.copy()]
        data['sources'][0]['notes'] = f"Chemistry process visualization: {data.get('name', 'Unknown process')}. Created using the Programming Framework methodology for process analysis and visualization."
        
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    return False

def main():
    """Add sources to all chemistry JSON files"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space/chemistry-processes-database/processes")
    
    json_files = list(base_dir.rglob("*.json"))
    print(f"Found {len(json_files)} JSON files")
    
    updated = 0
    for json_file in json_files:
        if add_sources_to_json(json_file):
            updated += 1
            print(f"  ✓ Added sources to: {json_file.name}")
    
    print(f"\nUpdated {updated} files with sources")

if __name__ == "__main__":
    main()
