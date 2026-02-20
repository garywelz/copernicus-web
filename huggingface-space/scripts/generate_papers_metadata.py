#!/usr/bin/env python3
"""
Generate papers-metadata.json for the Research Paper Database front end.
This creates a consolidated metadata file that the HTML viewer can load.
"""

import json
import glob
from pathlib import Path
from datetime import datetime
from typing import List, Dict

def load_all_papers(base_dir: Path) -> List[Dict]:
    """Load all paper JSON files and return as list."""
    papers = []
    paper_files = list((base_dir / "metadata-database" / "papers").rglob("*.json"))
    
    print(f"Found {len(paper_files)} paper files...")
    
    for i, paper_file in enumerate(paper_files):
        if i % 1000 == 0:
            print(f"  Loading papers: {i}/{len(paper_files)}...")
        
        try:
            with open(paper_file, 'r') as f:
                paper = json.load(f)
                papers.append(paper)
        except Exception as e:
            print(f"  Error loading {paper_file}: {e}")
            continue
    
    return papers

def generate_metadata_file():
    """Generate papers-metadata.json file."""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    
    print("Loading all papers...")
    papers = load_all_papers(base_dir)
    
    print(f"\nLoaded {len(papers)} papers")
    
    # Create metadata structure
    metadata = {
        'last_updated': datetime.now().isoformat(),
        'total_papers': len(papers),
        'papers': papers,
        'statistics': {
            'by_source': {},
            'by_category': {},
            'by_year': {}
        }
    }
    
    # Calculate statistics
    for paper in papers:
        source = paper.get('source', 'unknown')
        category = paper.get('category', 'unknown')
        year = paper.get('year', 'unknown')
        
        metadata['statistics']['by_source'][source] = metadata['statistics']['by_source'].get(source, 0) + 1
        metadata['statistics']['by_category'][category] = metadata['statistics']['by_category'].get(category, 0) + 1
        metadata['statistics']['by_year'][year] = metadata['statistics']['by_year'].get(year, 0) + 1
    
    # Save metadata file
    output_file = base_dir / "papers-metadata.json"
    print(f"\nSaving metadata to {output_file}...")
    print(f"  This may take a while for {len(papers)} papers...")
    
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    file_size = output_file.stat().st_size / (1024 * 1024)  # MB
    print(f"\n✅ Metadata file created: {file_size:.2f} MB")
    print(f"   Total papers: {len(papers):,}")
    print(f"   By source: {metadata['statistics']['by_source']}")
    print(f"   By category: {metadata['statistics']['by_category']}")
    
    return output_file

if __name__ == '__main__':
    generate_metadata_file()
