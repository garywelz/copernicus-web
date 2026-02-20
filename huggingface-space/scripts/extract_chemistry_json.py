#!/usr/bin/env python3
"""
Extract Chemistry Flowcharts from HTML to JSON Format

Converts chemistry batch HTML files to JSON format modeled on GLMP structure,
but using the 5-color scheme (not 8-color).
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Chemistry subcategory mapping
SUBCATEGORY_MAP = {
    "chemistry_batch_01": "organic_chemistry",
    "chemistry_batch_02": "physical_chemistry",
    "chemistry_batch_03": "analytical_chemistry",
    "chemistry_batch_04": "inorganic_chemistry",
    "chemistry_batch_05": "biochemistry",
    "chemistry_batch_06": "materials_chemistry",
    "chemistry_batch_07": "environmental_chemistry",
    "chemistry_batch_08": "electrochemistry",
    "chemistry_batch_09": "surface_chemistry",
    "chemistry_batch_10": "thermodynamics",
    "chemistry_batch_11": "kinetics",
    "chemistry_batch_12": "spectroscopy_advanced",
    "chemistry_batch_13": "quantum_chemistry",
    "chemistry_batch_14": "materials_science"
}

SUBCATEGORY_NAMES = {
    "organic_chemistry": "Organic Chemistry",
    "physical_chemistry": "Physical Chemistry",
    "analytical_chemistry": "Analytical Chemistry",
    "inorganic_chemistry": "Inorganic Chemistry",
    "biochemistry": "Biochemistry",
    "materials_chemistry": "Materials Chemistry",
    "environmental_chemistry": "Environmental Chemistry",
    "electrochemistry": "Electrochemistry",
    "surface_chemistry": "Surface Chemistry & Catalysis",
    "thermodynamics": "Thermodynamic Processes",
    "kinetics": "Kinetic Processes",
    "spectroscopy_advanced": "Advanced Spectroscopy & Analysis",
    "quantum_chemistry": "Quantum Chemistry",
    "materials_science": "Advanced Materials Science"
}

# 5-color scheme (not 8-color like GLMP)
COLOR_SCHEME = {
    "red": {
        "hex": "#ff6b6b",
        "category": "Triggers & Inputs"
    },
    "yellow": {
        "hex": "#ffd43b",
        "category": "Structures & Objects"
    },
    "green": {
        "hex": "#51cf66",
        "category": "Processing & Operations"
    },
    "blue": {
        "hex": "#74c0fc",
        "category": "Intermediates & States"
    },
    "violet": {
        "hex": "#b197fc",
        "category": "Products & Outputs"
    }
}


class ChemistryHTMLParser(HTMLParser):
    """Parser to extract process information from chemistry HTML files"""
    
    def __init__(self):
        super().__init__()
        self.processes = []
        self.current_process = None
        self.in_mermaid = False
        self.in_h2 = False
        self.in_process_title = False
        self.in_caption = False
        self.mermaid_content = []
        self.caption_content = []
        self.h2_content = []
        self.process_title_content = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'h2':
            self.in_h2 = True
            self.h2_content = []
        elif tag == 'div':
            for attr_name, attr_value in attrs:
                if attr_name == 'class':
                    if 'mermaid' in attr_value:
                        self.in_mermaid = True
                        self.mermaid_content = []
                    elif 'process-title' in attr_value:
                        self.in_process_title = True
                        self.process_title_content = []
                    elif 'figure-caption' in attr_value:
                        self.in_caption = True
                        self.caption_content = []
    
    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_h2 = False
            if self.h2_content:
                # Extract process number and name from h2 format: "1. Process Name"
                text = ''.join(self.h2_content).strip()
                match = re.match(r'(\d+)\.\s*(.+)', text)
                if match:
                    process_num, process_name = match.groups()
                    # Remove "Process" suffix if present
                    process_name = re.sub(r'\s+Process$', '', process_name)
                    self.current_process = {
                        'number': process_num,
                        'name': process_name,
                        'mermaid': '',
                        'description': ''
                    }
        elif tag == 'div':
            if self.in_process_title:
                self.in_process_title = False
                if self.process_title_content:
                    # Extract process number and name from div format: "Process 1: Process Name"
                    text = ''.join(self.process_title_content).strip()
                    match = re.match(r'Process\s+(\d+):\s*(.+)', text)
                    if match:
                        process_num, process_name = match.groups()
                        # Remove "Process" suffix if present
                        process_name = re.sub(r'\s+Process$', '', process_name)
                        self.current_process = {
                            'number': process_num,
                            'name': process_name,
                            'mermaid': '',
                            'description': ''
                        }
            elif self.in_mermaid:
                self.in_mermaid = False
                if self.current_process and self.mermaid_content:
                    # Join all content, preserving newlines that are in the original
                    mermaid = ''.join(self.mermaid_content).strip()
                    # Clean up: normalize whitespace but preserve line structure
                    # Replace multiple spaces with single space (but keep newlines)
                    lines = []
                    for line in mermaid.split('\n'):
                        # Clean each line: remove leading/trailing whitespace, normalize internal spaces
                        cleaned = re.sub(r'[ \t]+', ' ', line.strip())
                        if cleaned:  # Only add non-empty lines
                            lines.append(cleaned)
                    
                    # Remove duplicate style statements - keep only the last one for each node
                    graph_lines = []
                    style_lines = []
                    style_dict = {}  # Track last style for each node
                    
                    for line in lines:
                        if line.strip().startswith('style '):
                            # Extract node name from style statement
                            match = re.match(r'style\s+(\w+)', line)
                            if match:
                                node_name = match.group(1)
                                style_dict[node_name] = line
                        else:
                            graph_lines.append(line)
                    
                    # Add styles after graph definition, keeping only last style per node
                    if graph_lines:
                        mermaid = '\n'.join(graph_lines)
                        if style_dict:
                            mermaid += '\n\n    ' + '\n    '.join(style_dict.values())
                    else:
                        mermaid = '\n'.join(lines)
                    
                    self.current_process['mermaid'] = mermaid
            elif self.in_caption:
                self.in_caption = False
                if self.current_process and self.caption_content:
                    caption = ''.join(self.caption_content).strip()
                    # Extract description (remove "Figure X." prefix)
                    caption = re.sub(r'^Figure\s+\d+\.\s*', '', caption)
                    # Remove bold formatting
                    caption = re.sub(r'<strong>|</strong>', '', caption)
                    self.current_process['description'] = caption
                    # Save process
                    if self.current_process.get('mermaid'):
                        self.processes.append(self.current_process.copy())
                    self.current_process = None
    
    def handle_data(self, data):
        if self.in_h2:
            self.h2_content.append(data)
        elif self.in_process_title:
            self.process_title_content.append(data)
        elif self.in_mermaid:
            # Preserve the data as-is, including newlines
            self.mermaid_content.append(data)
        elif self.in_caption:
            self.caption_content.append(data)


def analyze_mermaid_flowchart(mermaid_text: str) -> Dict:
    """Analyze Mermaid flowchart to extract statistics"""
    
    # Extract nodes
    node_pattern = r'(\w+)\[([^\]]+)\]'
    nodes = re.findall(node_pattern, mermaid_text)
    
    # Extract edges (arrows)
    edge_pattern = r'-->'
    edges = len(re.findall(edge_pattern, mermaid_text))
    
    # Extract conditionals (diamond shapes)
    conditional_pattern = r'(\w+)\{([^\}]+)\}'
    conditionals = re.findall(conditional_pattern, mermaid_text)
    
    # Extract OR gates (orange color in style or "OR" in text)
    or_gates = 0
    or_pattern = r'OR|or|OR\s+Gate'
    or_gates += len(re.findall(or_pattern, mermaid_text, re.IGNORECASE))
    # Also check for orange color (#ff9f43) which GLMP uses for OR gates
    or_gates += len(re.findall(r'#ff9f43', mermaid_text))
    
    # Extract AND gates (lavender color or "AND" in gate names)
    and_gates = 0
    and_pattern = r'ANDGATE|AND\s+Gate|and\s+gate'
    and_gates += len(re.findall(and_pattern, mermaid_text, re.IGNORECASE))
    # Check for lavender color (#b4b4dc) which GLMP uses for AND gates
    and_gates += len(re.findall(r'#b4b4dc', mermaid_text))
    
    # Count unique nodes
    unique_nodes = len(set(node[0] for node in nodes))
    
    # Determine complexity level
    total_nodes = unique_nodes + len(conditionals)
    if total_nodes < 15:
        complexity_level = "low"
    elif total_nodes < 30:
        complexity_level = "medium"
    elif total_nodes < 50:
        complexity_level = "detailed"
    else:
        complexity_level = "high"
    
    return {
        'nodes': unique_nodes,
        'total_nodes': total_nodes,
        'edges': edges,
        'conditionals': len(conditionals),
        'or_gates': or_gates,
        'and_gates': and_gates,
        'total_gates': or_gates + and_gates,
        'complexity_level': complexity_level
    }


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def extract_sources(html_content: str) -> List[Dict]:
    """Extract source citations from HTML if present"""
    # Look for citations, references, or source sections
    sources = []
    
    # Pattern for DOI
    doi_pattern = r'doi[:\s]+([^\s]+)'
    dois = re.findall(doi_pattern, html_content, re.IGNORECASE)
    
    # Pattern for URLs
    url_pattern = r'https?://[^\s<>"\'\)]+'
    urls = re.findall(url_pattern, html_content)
    
    # Pattern for citations (author et al., year)
    citation_pattern = r'([A-Z][a-z]+(?:\s+et\s+al\.)?)[,\.\s]+(\d{4})'
    citations = re.findall(citation_pattern, html_content)
    
    # Try to extract from figure captions or reference sections
    # This is a basic implementation - may need refinement
    
    return sources


def create_json_file(process: Dict, subcategory: str, output_dir: Path) -> str:
    """Create JSON file for a process"""
    
    # Generate ID
    process_id = f"{subcategory}-{slugify(process['name'])}"
    
    # Analyze flowchart
    analysis = analyze_mermaid_flowchart(process['mermaid'])
    
    # Create JSON structure
    json_data = {
        "id": process_id,
        "name": process['name'],
        "category": "chemistry",
        "subcategory": subcategory,
        "description": process.get('description', 'Chemistry process visualization using the Programming Framework.'),
        "complexity": {
            "nodes": analysis['nodes'],
            "edges": analysis['edges'],
            "conditionals": analysis['conditionals'],
            "logicGates": {
                "orGates": analysis['or_gates'],
                "andGates": analysis['and_gates'],
                "total": analysis['total_gates']
            },
            "level": analysis['complexity_level'],
            "detailLevel": analysis['complexity_level']
        },
        "colorScheme": COLOR_SCHEME,
        "mermaid": process['mermaid'],
        "sources": process.get('sources', []),
        "keywords": extract_keywords(process['name'], process.get('description', '')),
        "relatedProcesses": [],
        "created": datetime.now().strftime("%Y-%m-%d"),
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "verified": False,
        "notes": f"Converted from chemistry batch HTML. Process number: {process['number']}."
    }
    
    # Create subcategory directory
    subcategory_dir = output_dir / subcategory
    subcategory_dir.mkdir(parents=True, exist_ok=True)
    
    # Write JSON file
    json_file = subcategory_dir / f"{process_id}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return str(json_file)


def extract_keywords(name: str, description: str) -> List[str]:
    """Extract keywords from process name and description"""
    keywords = []
    
    # Add words from name
    words = re.findall(r'\b\w+\b', name.lower())
    keywords.extend([w for w in words if len(w) > 3])
    
    # Add chemistry-specific terms
    chemistry_terms = ['reaction', 'mechanism', 'synthesis', 'catalyst', 'molecule', 
                      'compound', 'organic', 'inorganic', 'physical', 'analytical',
                      'biochemistry', 'polymer', 'electrochemistry', 'surface', 'nuclear']
    
    for term in chemistry_terms:
        if term in name.lower() or term in description.lower():
            keywords.append(term)
    
    return list(set(keywords[:10]))  # Limit to 10 keywords


def process_chemistry_batch(html_file: Path, output_dir: Path) -> List[Dict]:
    """Process a single chemistry batch HTML file"""
    
    print(f"Processing: {html_file.name}")
    
    # Parse HTML
    parser = ChemistryHTMLParser()
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    parser.feed(html_content)
    
    # Extract sources from HTML
    sources = extract_sources(html_content)
    
    # Get subcategory
    batch_name = html_file.stem  # e.g., "chemistry_batch_01"
    subcategory = SUBCATEGORY_MAP.get(batch_name, "general_chemistry")
    
    # Create JSON files for each process
    json_files = []
    process_metadata = []
    
    for process in parser.processes:
        process['sources'] = sources
        json_file = create_json_file(process, subcategory, output_dir)
        json_files.append(json_file)
        
        # Collect metadata
        analysis = analyze_mermaid_flowchart(process['mermaid'])
        process_metadata.append({
            "id": f"{subcategory}-{slugify(process['name'])}",
            "name": process['name'],
            "subcategory": subcategory,
            "subcategory_name": SUBCATEGORY_NAMES.get(subcategory, subcategory),
            "complexity": analysis['complexity_level'],
            "nodes": analysis['nodes'],
            "edges": analysis['edges'],
            "orGates": analysis['or_gates'],
            "andGates": analysis['and_gates'],
            "totalGates": analysis['total_gates'],
            "json_file": json_file
        })
        
        print(f"  ✓ Created: {Path(json_file).name}")
    
    return process_metadata


def create_metadata_json(all_processes: List[Dict], output_dir: Path):
    """Create metadata.json file with all process information"""
    
    # Organize by subcategory
    by_subcategory = defaultdict(list)
    for process in all_processes:
        by_subcategory[process['subcategory']].append(process)
    
    # Calculate statistics
    total_processes = len(all_processes)
    total_nodes = sum(p['nodes'] for p in all_processes)
    total_edges = sum(p['edges'] for p in all_processes)
    total_or_gates = sum(p['orGates'] for p in all_processes)
    total_and_gates = sum(p['andGates'] for p in all_processes)
    
    metadata = {
        "name": "Chemistry Processes Database",
        "version": "1.0.0",
        "created": datetime.now().strftime("%Y-%m-%d"),
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "category": "chemistry",
        "colorScheme": "5-color",
        "description": "Chemistry processes visualized using the Programming Framework with 5-color scheme. Converted from HTML batch files.",
        "totalProcesses": total_processes,
        "subcategories": len(by_subcategory),
        "statistics": {
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
            "totalOrGates": total_or_gates,
            "totalAndGates": total_and_gates,
            "totalGates": total_or_gates + total_and_gates
        },
        "processes": []
    }
    
    # Add processes organized by subcategory
    for subcategory, processes in sorted(by_subcategory.items()):
        for process in processes:
            metadata["processes"].append({
                "id": process["id"],
                "name": process["name"],
                "subcategory": process["subcategory"],
                "subcategory_name": process["subcategory_name"],
                "complexity": process["complexity"],
                "nodes": process["nodes"],
                "edges": process["edges"],
                "orGates": process["orGates"],
                "andGates": process["andGates"],
                "totalGates": process["totalGates"]
            })
    
    # Write metadata.json
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Created metadata.json: {metadata_file}")
    print(f"  Total processes: {total_processes}")
    print(f"  Total subcategories: {len(by_subcategory)}")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Total edges: {total_edges}")
    
    return metadata_file


def main():
    """Main execution function"""
    
    # Paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    html_dir = Path("/home/gdubs/progframe/programming_framework")
    output_dir = project_root / "chemistry-processes-database"
    
    # Create output directory structure
    processes_dir = output_dir / "processes"
    processes_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Chemistry HTML to JSON Converter")
    print("=" * 60)
    print(f"Input directory: {html_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Find all chemistry batch HTML files
    chemistry_files = sorted(html_dir.glob("chemistry_batch_*.html"))
    
    if not chemistry_files:
        print(f"ERROR: No chemistry batch files found in {html_dir}")
        return
    
    print(f"Found {len(chemistry_files)} chemistry batch files\n")
    
    # Process each batch file
    all_processes = []
    for html_file in chemistry_files:
        try:
            processes = process_chemistry_batch(html_file, processes_dir)
            all_processes.extend(processes)
        except Exception as e:
            print(f"  ✗ Error processing {html_file.name}: {e}")
            import traceback
            traceback.print_exc()
        print()
    
    # Create metadata.json
    if all_processes:
        create_metadata_json(all_processes, output_dir)
        print("\n" + "=" * 60)
        print("Conversion complete!")
        print("=" * 60)
    else:
        print("ERROR: No processes were extracted")


if __name__ == "__main__":
    main()
