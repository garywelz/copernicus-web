#!/usr/bin/env python3
"""
Generic Extraction Script for Programming Framework Processes

Extracts processes from Programming Framework HTML batch files
and converts them to JSON format. Handles multiple subjects and
different HTML title formats.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.request import urlopen
from html.parser import HTMLParser
import html

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MermaidExtractor(HTMLParser):
    """Extract Mermaid code from HTML - handles both title formats."""
    
    def __init__(self):
        super().__init__()
        self.mermaid_blocks = []
        self.in_mermaid = False
        self.in_title = False
        self.in_process_title = False
        self.current_mermaid = []
        self.current_title = None
        self.titles = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.in_title = True
        elif tag == 'div':
            # Check for process-title div (used in chemistry batches 8-14)
            for attr_name, attr_value in attrs:
                if attr_name == 'class' and 'process-title' in attr_value.lower():
                    self.in_process_title = True
                elif attr_name == 'class' and 'mermaid' in attr_value.lower():
                    self.in_mermaid = True
                    self.current_mermaid = []
        elif tag in ['pre', 'code']:
            # Check if this is a mermaid block
            for attr_name, attr_value in attrs:
                if attr_name == 'class' and 'mermaid' in attr_value.lower():
                    self.in_mermaid = True
                    self.current_mermaid = []
    
    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_title = False
        elif tag == 'div':
            if self.in_process_title:
                self.in_process_title = False
            elif self.in_mermaid:
                if self.current_mermaid:
                    mermaid_code = '\n'.join(self.current_mermaid).strip()
                    if mermaid_code:  # Only add if we have content
                        self.mermaid_blocks.append({
                            'title': self.current_title or f"Process {len(self.mermaid_blocks) + 1}",
                            'mermaid': mermaid_code
                        })
                    self.current_mermaid = []
                self.in_mermaid = False
        elif tag in ['pre', 'code'] and self.in_mermaid:
            if self.current_mermaid:
                mermaid_code = '\n'.join(self.current_mermaid).strip()
                if mermaid_code:
                    self.mermaid_blocks.append({
                        'title': self.current_title or f"Process {len(self.mermaid_blocks) + 1}",
                        'mermaid': mermaid_code
                    })
                self.current_mermaid = []
            self.in_mermaid = False
    
    def handle_data(self, data):
        if self.in_title:
            # Extract title (remove numbering like "1. " or "1:")
            title = re.sub(r'^\d+[\.:]\s*', '', data.strip())
            if title:
                self.current_title = title
                self.titles.append(title)
        elif self.in_process_title:
            # Extract title from process-title div (format: "Process 1: Title" or "Process 1 Title")
            title = re.sub(r'^Process\s+\d+[:\s]+', '', data.strip(), flags=re.IGNORECASE)
            if title:
                self.current_title = title
                self.titles.append(title)
        elif self.in_mermaid:
            self.current_mermaid.append(data)


def extract_entities_from_mermaid(mermaid: str) -> List[str]:
    """Extract entity names from Mermaid code."""
    entities = []
    
    # Pattern to match node definitions: A1[Label] or A1(Label) or A1{Label}
    node_pattern = r'[A-Za-z0-9_]+[\[\(\{]([^\]]+)[\]\)\}]'
    
    matches = re.findall(node_pattern, mermaid)
    for match in matches:
        entity = match.strip()
        # Clean up entity name
        if entity and entity not in entities:
            entities.append(entity)
    
    return entities[:50]  # Limit to 50 entities


def determine_subcategory(title: str, subject: str, batch_number: int, batch_title: str = "") -> str:
    """Determine subcategory from title, subject, batch number, and batch title."""
    title_lower = title.lower()
    batch_title_lower = batch_title.lower()
    
    if subject == "chemistry":
        # Use batch title to determine subcategory
        if "organic" in batch_title_lower:
            return "organic_chemistry"
        elif "physical" in batch_title_lower:
            return "physical_chemistry"
        elif "analytical" in batch_title_lower:
            return "analytical_chemistry"
        elif "inorganic" in batch_title_lower:
            return "inorganic_chemistry"
        elif "biochemistry" in batch_title_lower or "enzyme" in batch_title_lower:
            return "biochemistry"
        elif "materials" in batch_title_lower or "polymer" in batch_title_lower:
            return "materials_chemistry"
        elif "environmental" in batch_title_lower or "atmospheric" in batch_title_lower or "green" in batch_title_lower:
            return "environmental_chemistry"
        elif "electrochemical" in batch_title_lower or "battery" in batch_title_lower or "corrosion" in batch_title_lower:
            return "electrochemical_processes"
        elif "catalysis" in batch_title_lower or "surface" in batch_title_lower:
            return "surface_chemistry_catalysis"
        elif "thermodynamic" in batch_title_lower or "thermochemistry" in batch_title_lower or "entropy" in batch_title_lower:
            return "thermodynamic_processes"
        elif "kinetic" in batch_title_lower or "reaction mechanism" in batch_title_lower:
            return "kinetic_processes"
        elif "spectroscopy" in batch_title_lower or "spectrometry" in batch_title_lower or "chromatography" in batch_title_lower:
            return "spectroscopy_analysis"
        elif "quantum" in batch_title_lower or "molecular orbital" in batch_title_lower:
            return "quantum_chemistry"
        else:
            return "general_chemistry"
    
    elif subject == "physics":
        if "classical" in batch_title_lower or "mechanics" in batch_title_lower or "newtonian" in title_lower:
            return "classical_mechanics"
        elif "quantum" in batch_title_lower or "quantum" in title_lower:
            return "quantum_mechanics"
        elif "electromagnetic" in batch_title_lower or "electromagnetic" in title_lower:
            return "electromagnetism"
        elif "thermodynamic" in batch_title_lower or "thermodynamic" in title_lower:
            return "thermodynamics"
        else:
            return "general_physics"
    
    elif subject == "computer_science":
        if "algorithm" in batch_title_lower or "data structure" in batch_title_lower or "sorting" in title_lower:
            return "algorithms_data_structures"
        elif "software" in batch_title_lower or "design pattern" in batch_title_lower or "architecture" in title_lower:
            return "software_engineering"
        elif "artificial intelligence" in batch_title_lower or "machine learning" in batch_title_lower or "neural network" in title_lower:
            return "artificial_intelligence"
        elif "security" in batch_title_lower or "cryptography" in batch_title_lower:
            return "computer_security"
        elif "network" in batch_title_lower or "protocol" in batch_title_lower or "distributed" in title_lower:
            return "computer_networks"
        elif "database" in batch_title_lower or "query" in batch_title_lower:
            return "database_systems"
        elif "graphics" in batch_title_lower or "rendering" in batch_title_lower or "game" in title_lower:
            return "computer_graphics"
        else:
            return "general_computer_science"
    
    return "general"


def create_id_from_title(title: str) -> str:
    """Create a valid ID from title."""
    # Convert to lowercase, replace spaces with hyphens
    id_str = title.lower()
    id_str = re.sub(r'[^a-z0-9\s-]', '', id_str)
    id_str = re.sub(r'\s+', '-', id_str)
    id_str = re.sub(r'-+', '-', id_str)
    return id_str.strip('-')


def extract_batch_title(html_content: str) -> str:
    """Extract batch title from HTML (usually in h1 tag)."""
    h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content, re.IGNORECASE | re.DOTALL)
    if h1_match:
        title = h1_match.group(1).strip()
        # Remove HTML tags
        title = re.sub(r'<[^>]+>', '', title)
        return title
    return ""


def extract_processes_from_batch(
    batch_url: str,
    subject: str,
    batch_number: int
) -> List[Dict[str, Any]]:
    """Extract processes from a single batch HTML file."""
    
    print(f"📥 Fetching batch {batch_number} from: {batch_url}")
    try:
        with urlopen(batch_url) as response:
            html_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"❌ Error fetching {batch_url}: {e}")
        return []
    
    # Extract batch title
    batch_title = extract_batch_title(html_content)
    print(f"   Batch title: {batch_title}")
    
    # Parse HTML and extract Mermaid diagrams
    print("   🔍 Parsing HTML and extracting Mermaid diagrams...")
    parser = MermaidExtractor()
    parser.feed(html_content)
    
    processes = []
    for i, block in enumerate(parser.mermaid_blocks, 1):
        title = block['title']
        mermaid = block['mermaid']
        
        # Extract entities from Mermaid code
        entities = extract_entities_from_mermaid(mermaid)
        
        # Determine subcategory
        subcategory = determine_subcategory(title, subject, batch_number, batch_title)
        
        process = {
            "id": create_id_from_title(title),
            "title": title,
            "description": f"{subject.replace('_', ' ').title()} process: {title}",
            "category": subject,
            "subcategory": subcategory,
            "mermaid": mermaid,
            "entities": entities,
            "metadata": {
                "source": "programming_framework",
                "batch": f"batch_{batch_number:02d}",
                "batch_number": batch_number,
                "batch_title": batch_title,
                "color_scheme": "discipline_based",
                "node_count": len(entities),
                "complexity": "high" if len(entities) > 30 else "medium"
            }
        }
        
        processes.append(process)
        print(f"   ✅ Extracted: {title} ({len(entities)} entities, subcategory: {subcategory})")
    
    return processes


def extract_all_batches(
    subject: str,
    batch_urls: List[str],
    output_dir: Path
) -> Dict[str, Any]:
    """Extract processes from all batch URLs."""
    
    all_processes = []
    batch_stats = {}
    
    for batch_num, batch_url in enumerate(batch_urls, 1):
        processes = extract_processes_from_batch(batch_url, subject, batch_num)
        all_processes.extend(processes)
        batch_stats[f"batch_{batch_num:02d}"] = len(processes)
        print()
    
    # Save processes to JSON files organized by subcategory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"💾 Saving {len(all_processes)} processes to {output_dir}...")
    
    subcategory_counts = {}
    for process in all_processes:
        subcategory = process.get('subcategory', 'general')
        category_dir = output_dir / subcategory
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as JSON file
        filename = f"{process['id']}.json"
        filepath = category_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(process, f, indent=2, ensure_ascii=False)
        
        subcategory_counts[subcategory] = subcategory_counts.get(subcategory, 0) + 1
    
    # Save summary index
    index = {
        "subject": subject,
        "total_processes": len(all_processes),
        "total_batches": len(batch_urls),
        "batch_stats": batch_stats,
        "subcategories": subcategory_counts,
        "processes": [
            {
                "id": p["id"],
                "title": p["title"],
                "category": p["category"],
                "subcategory": p.get("subcategory"),
                "batch": p["metadata"]["batch"]
            }
            for p in all_processes
        ]
    }
    
    index_path = output_dir / "index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ Saved index: {index_path}")
    
    return {
        "total_processes": len(all_processes),
        "subcategories": subcategory_counts,
        "batch_stats": batch_stats
    }


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract processes from Programming Framework batch HTML files")
    parser.add_argument("--subject", required=True, choices=["chemistry", "physics", "computer_science"],
                       help="Subject category")
    parser.add_argument("--batch-urls", nargs="+", required=True,
                       help="List of batch HTML URLs")
    parser.add_argument("--output", type=Path, default=None,
                       help="Output directory (default: {subject}-processes)")
    
    args = parser.parse_args()
    
    # Set default output directory if not provided
    if args.output is None:
        args.output = Path(f"{args.subject}-processes")
    
    print("="*70)
    print(f"  EXTRACT {args.subject.upper().replace('_', ' ')} PROCESSES")
    print("="*70)
    print(f"\n📋 Processing {len(args.batch_urls)} batches...")
    print(f"   Output directory: {args.output}\n")
    
    try:
        stats = extract_all_batches(args.subject, args.batch_urls, args.output)
        
        print("\n" + "="*70)
        print("  EXTRACTION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Subject: {args.subject}")
        print(f"   Total processes: {stats['total_processes']}")
        print(f"   Subcategories: {len(stats['subcategories'])}")
        print(f"   Output directory: {args.output}")
        print(f"\n📋 Subcategories:")
        for subcat, count in sorted(stats['subcategories'].items()):
            print(f"   - {subcat}: {count} processes")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Review extracted processes in {args.output}")
        print(f"   2. Upload to GCS: gsutil -m cp -r {args.output}/* gs://regal-scholar-453620-r7-podcast-storage/{args.subject}-processes-database/")
        print(f"   3. Sync to Firestore using sync_{args.subject}_processes.py")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

