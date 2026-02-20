#!/usr/bin/env python3
"""
Create Database Table HTML files for discipline databases
"""

import json
from pathlib import Path

DISCIPLINE_CONFIG = {
    "chemistry": {
        "name": "Chemistry",
        "emoji": "⚗️",
        "color": "#e74c3c",
        "gcs_path": "chemistry-processes-database",
        "database_table": "chemistry-database-table.html"
    },
    "physics": {
        "name": "Physics",
        "emoji": "⚛️",
        "color": "#3498db",
        "gcs_path": "physics-processes-database",
        "database_table": "physics-database-table.html"
    },
    "computer_science": {
        "name": "Computer Science",
        "emoji": "💻",
        "color": "#9b59b6",
        "gcs_path": "computer-science-processes-database",
        "database_table": "computer-science-database-table.html"
    },
    "mathematics": {
        "name": "Mathematics",
        "emoji": "🔢",
        "color": "#e67e22",
        "gcs_path": "mathematics-processes-database",
        "database_table": "mathematics-database-table.html"
    },
    "biology": {
        "name": "Biology",
        "emoji": "🧬",
        "color": "#27ae60",
        "gcs_path": "biology-processes-database",
        "database_table": "biology-database-table.html"
    }
}

def create_database_table(discipline: str, metadata_path: Path, output_path: Path):
    """Create a database table HTML file from metadata.json"""
    
    config = DISCIPLINE_CONFIG.get(discipline)
    if not config:
        raise ValueError(f"Unknown discipline: {discipline}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Read the chemistry template and adapt it
    template_path = Path("/home/gdubs/copernicus-web-public/huggingface-space/chemistry-processes-database/chemistry-database-table.html")
    with open(template_path, 'r') as f:
        html = f.read()
    
    # Replace discipline-specific content
    html = html.replace('⚗️ Chemistry', f'{config["emoji"]} {config["name"]}')
    html = html.replace('chemistry', discipline)
    html = html.replace('Chemistry', config["name"])
    html = html.replace('#e74c3c', config["color"])
    html = html.replace('#c0392b', config["color"])
    html = html.replace('chemistry-processes-database', config["gcs_path"])
    html = html.replace('chemistry-database-table.html', config["database_table"])
    
    # Update metadata URL logic
    metadata_url_section = f'''const METADATA_URL = window.location.hostname.includes('storage.googleapis.com') 
            ? 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{config["gcs_path"]}/metadata.json'
            : (window.location.hostname.includes('huggingface.co'))
            ? './{config["gcs_path"].replace("-processes-database", "-processes-database")}/metadata.json'
            : './metadata.json';'''
    
    # Replace the metadata URL section
    import re
    html = re.sub(
        r'const METADATA_URL = .*?;\s*',
        metadata_url_section + '\n        ',
        html,
        flags=re.DOTALL
    )
    
    # Update viewer URL logic in the table population
    viewer_url_logic = f'''const isGCS = window.location.hostname.includes('storage.googleapis.com');
                const isHF = window.location.hostname.includes('huggingface.co');
                const viewerUrl = isGCS 
                    ? `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/{config["gcs_path"]}/processes/${{process.subcategory}}/${{process.id}}.html`
                    : (isHF)
                    ? `./{config["gcs_path"]}/processes/${{process.subcategory}}/${{process.id}}.html`
                    : `./processes/${{process.subcategory}}/${{process.id}}.html`;'''
    
    # Find and replace the viewer URL assignment
    html = re.sub(
        r'const viewerUrl = .*?;',
        viewer_url_logic,
        html,
        flags=re.DOTALL
    )
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"✓ Created: {output_path}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python create_database_table.py <discipline>")
        print("Example: python create_database_table.py physics")
        return
    
    discipline = sys.argv[1]
    # Handle directory naming variations
    dir_map = {
        "computer_science": "computer-science-processes-database",
        "mathematics": "mathematics-processes-database",
        "physics": "physics-processes-database",
        "chemistry": "chemistry-processes-database",
        "biology": "biology-processes-database"
    }
    dir_name = dir_map.get(discipline, f"{discipline}-processes-database")
    base_dir = Path(f"/home/gdubs/copernicus-web-public/huggingface-space/{dir_name}")
    metadata_path = base_dir / "metadata.json"
    config = DISCIPLINE_CONFIG.get(discipline)
    
    if not metadata_path.exists():
        print(f"ERROR: metadata.json not found at {metadata_path}")
        return
    
    output_path = base_dir / config["database_table"]
    create_database_table(discipline, metadata_path, output_path)

if __name__ == "__main__":
    main()
