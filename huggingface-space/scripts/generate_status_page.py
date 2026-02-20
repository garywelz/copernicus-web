#!/usr/bin/env python3
"""
Generate Knowledge Engine Status Page with current counts.
Updates the HTML page and JSON metadata file.
"""

import json
import glob
from pathlib import Path
from datetime import datetime

def count_collection():
    """Count current collection items."""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    
    # Count papers
    papers = len(list((base_dir / "metadata-database" / "papers").rglob("*.json")))
    
    # Count processes (excluding backups)
    processes = len([
        f for f in (base_dir.glob("*-processes-database/processes/**/*.json"))
        if not f.name.endswith('.backup')
    ])
    
    # Count podcasts (from migration)
    podcasts = 79  # Could be updated from actual count
    
    # Count videos (from database - would need DB query)
    videos = 753  # From schema update
    
    return {
        'papers': papers,
        'processes': processes,
        'videos': videos,
        'podcasts': podcasts
    }

def generate_status_json():
    """Generate status JSON file."""
    counts = count_collection()
    
    status = {
        'last_updated': datetime.now().isoformat(),
        'papers': counts['papers'],
        'processes': counts['processes'],
        'videos': counts['videos'],
        'podcasts': counts['podcasts'],
        'targets': {
            'papers': 200000,
            'processes': 1000,
            'videos': 500,
            'podcasts': 200
        }
    }
    
    output_file = Path("/home/gdubs/copernicus-web-public/huggingface-space/knowledge-engine-status.json")
    with open(output_file, 'w') as f:
        json.dump(status, f, indent=2)
    
    print(f"✅ Status JSON updated: {output_file}")
    print(f"   Papers: {counts['papers']:,}")
    print(f"   Processes: {counts['processes']:,}")
    print(f"   Videos: {counts['videos']:,}")
    print(f"   Podcasts: {counts['podcasts']:,}")
    
    return status

if __name__ == '__main__':
    generate_status_json()
