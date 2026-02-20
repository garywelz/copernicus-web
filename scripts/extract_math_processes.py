#!/usr/bin/env python3
"""
Extract Mathematics Processes from Programming Framework

Extracts mathematics processes from the Programming Framework HTML page
and converts them to JSON format similar to GLMP processes.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from urllib.request import urlopen
from html.parser import HTMLParser
import html

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MermaidExtractor(HTMLParser):
    """Extract Mermaid code from HTML."""
    
    def __init__(self):
        super().__init__()
        self.mermaid_blocks = []
        self.in_mermaid = False
        self.in_title = False
        self.current_mermaid = []
        self.current_title = None
        self.titles = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.in_title = True
        elif tag in ['pre', 'code', 'div']:
            # Check if this is a mermaid block
            for attr_name, attr_value in attrs:
                if attr_name == 'class' and 'mermaid' in attr_value.lower():
                    self.in_mermaid = True
                    self.current_mermaid = []
    
    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_title = False
        elif tag in ['pre', 'code', 'div'] and self.in_mermaid:
            if self.current_mermaid:
                mermaid_code = '\n'.join(self.current_mermaid).strip()
                if mermaid_code:  # Only add if we have content
                    self.mermaid_blocks.append({
                        'title': self.current_title or f"Process {len(self.mermaid_blocks) + 1}",
                        'mermaid': mermaid_code
                    })
                self.current_mermaid = []
            self.in_mermaid = False
    
    def handle_data(self, data):
        if self.in_title:
            # Extract title (remove numbering like "1. ")
            title = re.sub(r'^\d+\.\s*', '', data.strip())
            if title:
                self.current_title = title
                self.titles.append(title)
        elif self.in_mermaid:
            self.current_mermaid.append(data)


def extract_processes_from_html(html_url: str) -> List[Dict[str, Any]]:
    """Extract mathematics processes from HTML page."""
    
    print(f"📥 Fetching HTML from: {html_url}")
    with urlopen(html_url) as response:
        html_content = response.read().decode('utf-8')
    
    print("🔍 Parsing HTML and extracting Mermaid diagrams...")
    parser = MermaidExtractor()
    parser.feed(html_content)
    
    processes = []
    for i, block in enumerate(parser.mermaid_blocks):
        title = block['title']
        mermaid = block['mermaid']
        
        # Extract entities from Mermaid code (nodes)
        entities = extract_entities_from_mermaid(mermaid)
        
        # Determine category based on title
        category = determine_category(title)
        
        process = {
            "id": create_id_from_title(title),
            "title": title,
            "description": f"Mathematics process: {title}",
            "category": "mathematics",
            "subcategory": category,
            "mermaid": mermaid,
            "entities": entities,
            "metadata": {
                "source": "programming_framework",
                "color_scheme": "discipline_based",
                "node_count": len(entities),
                "complexity": "high" if len(entities) > 30 else "medium"
            }
        }
        
        processes.append(process)
        print(f"  ✅ Extracted: {title} ({len(entities)} entities)")
    
    return processes


def extract_entities_from_mermaid(mermaid: str) -> List[str]:
    """Extract entity names from Mermaid code."""
    entities = []
    
    # Pattern to match node definitions: A1[Label] or A1(Label)
    node_pattern = r'[A-Z]\d+\[([^\]]+)\]|[A-Z]\d+\(([^\)]+)\)'
    
    matches = re.findall(node_pattern, mermaid)
    for match in matches:
        entity = match[0] or match[1]
        # Clean up entity name
        entity = entity.strip()
        if entity and entity not in entities:
            entities.append(entity)
    
    return entities[:50]  # Limit to 50 entities


def determine_category(title: str) -> str:
    """Determine subcategory from title."""
    title_lower = title.lower()
    
    if 'induction' in title_lower or 'proof' in title_lower:
        return "proof_methods"
    elif 'algorithm' in title_lower or 'euclidean' in title_lower:
        return "algorithms"
    elif 'matrix' in title_lower or 'linear algebra' in title_lower:
        return "linear_algebra"
    elif 'calculus' in title_lower or 'integration' in title_lower:
        return "calculus"
    elif 'probability' in title_lower:
        return "probability"
    else:
        return "general"


def create_id_from_title(title: str) -> str:
    """Create a valid ID from title."""
    # Convert to lowercase, replace spaces with hyphens
    id_str = title.lower()
    id_str = re.sub(r'[^a-z0-9\s-]', '', id_str)
    id_str = re.sub(r'\s+', '-', id_str)
    id_str = re.sub(r'-+', '-', id_str)
    return id_str.strip('-')


def save_processes_to_json(processes: List[Dict[str, Any]], output_dir: Path):
    """Save processes as individual JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving {len(processes)} processes to {output_dir}...")
    
    for process in processes:
        # Create subdirectory based on category
        subcategory = process.get('subcategory', 'general')
        category_dir = output_dir / subcategory
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON file
        filename = f"{process['id']}.json"
        filepath = category_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(process, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Saved: {filepath}")
    
    # Also save a summary index
    index = {
        "total_processes": len(processes),
        "categories": {},
        "processes": [{"id": p["id"], "title": p["title"], "category": p["category"], "subcategory": p.get("subcategory")} for p in processes]
    }
    
    for process in processes:
        subcat = process.get('subcategory', 'general')
        if subcat not in index["categories"]:
            index["categories"][subcat] = 0
        index["categories"][subcat] += 1
    
    index_path = output_dir / "index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ Saved index: {index_path}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract mathematics processes from Programming Framework")
    parser.add_argument("--url", default="https://garywelz-programming-framework.static.hf.space/mathematics_processes.html",
                       help="URL to Programming Framework mathematics processes page")
    parser.add_argument("--output", type=Path, default=Path("math-processes"),
                       help="Output directory for JSON files")
    
    args = parser.parse_args()
    
    print("="*70)
    print("  EXTRACT MATHEMATICS PROCESSES FROM PROGRAMMING FRAMEWORK")
    print("="*70)
    print()
    
    try:
        # Extract processes
        processes = extract_processes_from_html(args.url)
        
        if not processes:
            print("❌ No processes extracted. Check the URL and HTML structure.")
            return 1
        
        print(f"\n✅ Successfully extracted {len(processes)} processes")
        
        # Save to JSON files
        save_processes_to_json(processes, args.output)
        
        print("\n" + "="*70)
        print("  EXTRACTION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Total processes: {len(processes)}")
        print(f"   Output directory: {args.output}")
        print(f"\n📋 Next steps:")
        print(f"   1. Review extracted processes in {args.output}")
        print(f"   2. Upload to GCS: gsutil -m cp -r {args.output}/* gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/")
        print(f"   3. Sync to Firestore using sync_math_processes.py (to be created)")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

