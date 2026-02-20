#!/usr/bin/env python3
"""
Generate metadata.json for Mathematics Processes Database

Reads all mathematics process JSON files and generates a comprehensive metadata file
for use in the database table display.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

def count_mermaid_nodes(mermaid_code: str) -> int:
    """Count nodes in Mermaid diagram by counting unique node IDs."""
    if not mermaid_code:
        return 0
    
    # Extract node IDs from Mermaid syntax (e.g., A1[...], B2[...])
    import re
    # Pattern matches node definitions like "A1[...]" or "NodeName[...]"
    node_pattern = r'([A-Z][A-Z0-9]+)\['
    nodes = set(re.findall(node_pattern, mermaid_code))
    return len(nodes)

def analyze_mermaid_gates(mermaid_code: str) -> Dict[str, int]:
    """Analyze Mermaid diagram to count AND and OR gates.
    
    AND gate: Node with 2 or more incoming edges
    OR gate: Node with 1 incoming edge and 2 or more outgoing edges
    
    Returns:
        Dict with 'and_gates' and 'or_gates' counts
    """
    if not mermaid_code:
        return {'and_gates': 0, 'or_gates': 0}
    
    import re
    
    # Extract all edges (connections)
    # Pattern matches: "A1 --> B1" or "A1 -->|label| B1"
    edge_pattern = r'([A-Z][A-Z0-9]+)\s*-->\s*(?:[|][^|]+[|]\s*)?([A-Z][A-Z0-9]+)'
    edges = re.findall(edge_pattern, mermaid_code)
    
    # Count incoming and outgoing edges for each node
    incoming = {}
    outgoing = {}
    
    for source, target in edges:
        # Count outgoing edges
        outgoing[source] = outgoing.get(source, 0) + 1
        # Count incoming edges
        incoming[target] = incoming.get(target, 0) + 1
    
    # AND gates: nodes with 2+ incoming edges
    and_gates = sum(1 for count in incoming.values() if count >= 2)
    
    # OR gates: nodes with 1 incoming edge and 2+ outgoing edges
    or_gates = sum(1 for node in outgoing.keys() 
                   if incoming.get(node, 0) == 1 and outgoing[node] >= 2)
    
    return {'and_gates': and_gates, 'or_gates': or_gates}

def load_process_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a single process JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def scan_processes(base_dir: Path) -> List[Dict[str, Any]]:
    """Scan all subdirectories for process JSON files."""
    processes = []
    
    # Get all subdirectories
    subdirs = [d for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    for subdir in subdirs:
        json_files = list(subdir.glob('*.json'))
        for json_file in json_files:
            try:
                process_data = load_process_file(json_file)
                
                # Calculate node count and gate analysis from Mermaid code
                mermaid_code = process_data.get('mermaid', '')
                node_count = count_mermaid_nodes(mermaid_code)
                gate_analysis = analyze_mermaid_gates(mermaid_code)
                
                # Build process metadata (no entity count)
                process_metadata = {
                    'id': process_data.get('id', json_file.stem),
                    'name': process_data.get('title', process_data.get('id', 'Unknown')),
                    'category': process_data.get('category', 'mathematics'),
                    'subcategory': process_data.get('subcategory', 'general'),
                    'description': process_data.get('description', ''),
                    'complexity': process_data.get('metadata', {}).get('complexity', 'medium'),
                    'node_count': node_count,
                    'and_gates': gate_analysis['and_gates'],
                    'or_gates': gate_analysis['or_gates'],
                    'file_path': str(json_file.relative_to(base_dir)),
                    'source': process_data.get('metadata', {}).get('source', 'programming_framework'),
                    'sources': process_data.get('sources', []),
                    'source_text': process_data.get('source_text', '')
                }
                
                processes.append(process_metadata)
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
    
    return processes

def generate_metadata(base_dir: Path) -> Dict[str, Any]:
    """Generate complete metadata structure."""
    processes = scan_processes(base_dir)
    
    # Calculate statistics (no entity counts)
    total_nodes = sum(p['node_count'] for p in processes)
    avg_nodes = total_nodes / len(processes) if processes else 0
    
    # Count by subcategory
    subcategory_counts = {}
    for process in processes:
        subcat = process['subcategory']
        subcategory_counts[subcat] = subcategory_counts.get(subcat, 0) + 1
    
    # Count by complexity
    complexity_counts = {}
    for process in processes:
        complexity = process['complexity']
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
    
    metadata = {
        'totalProcesses': len(processes),
        'totalNodes': total_nodes,
        'averageNodes': round(avg_nodes, 1),
        'subcategoryCounts': subcategory_counts,
        'complexityCounts': complexity_counts,
        'processes': sorted(processes, key=lambda x: x['name'])
    }
    
    return metadata

def main():
    """Main function to generate metadata.json."""
    script_dir = Path(__file__).parent
    base_dir = script_dir
    
    print(f"Scanning mathematics processes in: {base_dir}")
    
    metadata = generate_metadata(base_dir)
    
    output_file = base_dir / 'metadata.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Generated metadata.json")
    print(f"   Total processes: {metadata['totalProcesses']}")
    print(f"   Total nodes: {metadata['totalNodes']}")
    print(f"   Average nodes: {metadata['averageNodes']}")
    print(f"\n   Subcategories: {list(metadata['subcategoryCounts'].keys())}")
    print(f"   Complexity levels: {list(metadata['complexityCounts'].keys())}")
    print(f"\n   Output file: {output_file}")

if __name__ == '__main__':
    main()

