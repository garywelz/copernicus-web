#!/usr/bin/env python3
"""
Analyze and fix process nodes according to AND/OR definitions and unique identifiers.

Rules:
1. AND node: 2+ incoming edges, 1 outgoing edge (top-down)
2. OR node: 1 incoming edge, 2+ outgoing edges (top-down)
3. Flag nodes with 2+ incoming AND 2+ outgoing edges as AND/OR nodes
4. Ensure each node has a unique identifier
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

def analyze_nodes(flowchart: Dict) -> Tuple[Dict, Dict, List[str]]:
    """
    Analyze nodes and edges to count AND/OR nodes and check for unique IDs.
    
    Returns:
        - node_stats: Dict mapping node_id to (incoming_count, outgoing_count)
        - node_ids: Dict mapping node_id to node data
        - issues: List of issue messages
    """
    nodes = flowchart.get('nodes', [])
    edges = flowchart.get('edges', [])
    
    # Build edge maps (top-down: source -> target)
    incoming_edges = defaultdict(int)  # node_id -> count of incoming edges
    outgoing_edges = defaultdict(int)  # node_id -> count of outgoing edges
    node_ids = {}
    issues = []
    
    # Collect all node IDs and check for duplicates
    node_id_counts = defaultdict(list)
    for node in nodes:
        node_id = node.get('id') or node.get('label')  # Try both id and label
        if not node_id:
            issues.append(f"Node missing identifier: {node.get('label', 'unknown')[:50]}")
            continue
            
        node_ids[node_id] = node
        node_id_counts[node_id].append(node.get('label', 'unknown'))
    
    # Check for duplicate IDs
    for node_id, labels in node_id_counts.items():
        if len(labels) > 1:
            issues.append(f"Duplicate node ID '{node_id}' found {len(labels)} times: {labels[:3]}")
    
    # Count edges (top-down: source -> target)
    for edge in edges:
        source = edge.get('source') or edge.get('from')
        target = edge.get('target') or edge.get('to')
        
        if source and target:
            outgoing_edges[source] += 1
            incoming_edges[target] += 1
    
    # Build node stats
    node_stats = {}
    all_node_ids = set(node_ids.keys()) | set(incoming_edges.keys()) | set(outgoing_edges.keys())
    
    for node_id in all_node_ids:
        incoming = incoming_edges.get(node_id, 0)
        outgoing = outgoing_edges.get(node_id, 0)
        node_stats[node_id] = (incoming, outgoing)
    
    return node_stats, node_ids, issues

def classify_and_count_nodes(node_stats: Dict, node_ids: Dict) -> Tuple[int, int, List[str]]:
    """
    Classify nodes as AND, OR, or AND/OR based on rules.
    
    Rules:
    - AND: 2+ incoming, 1 outgoing
    - OR: 1 incoming, 2+ outgoing
    - AND/OR: 2+ incoming AND 2+ outgoing (problematic)
    
    Returns:
        - and_count: Number of AND nodes
        - or_count: Number of OR nodes
        - problematic: List of AND/OR node IDs
    """
    and_count = 0
    or_count = 0
    problematic = []
    
    for node_id, (incoming, outgoing) in node_stats.items():
        if incoming >= 2 and outgoing == 1:
            and_count += 1
        elif incoming == 1 and outgoing >= 2:
            or_count += 1
        elif incoming >= 2 and outgoing >= 2:
            # Problematic: AND/OR node
            label = node_ids.get(node_id, {}).get('label', node_id)
            problematic.append(f"{node_id} (label: {label[:50]}) - {incoming} incoming, {outgoing} outgoing")
    
    return and_count, or_count, problematic

def fix_node_ids(flowchart: Dict) -> Tuple[Dict, List[str]]:
    """
    Ensure all nodes have unique identifiers.
    
    Returns:
        - Updated flowchart
        - List of changes made
    """
    nodes = flowchart.get('nodes', [])
    changes = []
    used_ids = set()
    
    for i, node in enumerate(nodes):
        node_id = node.get('id')
        label = node.get('label', f'node_{i}')
        
        # Generate ID if missing
        if not node_id:
            # Try to generate from label
            node_id = label.lower().replace(' ', '_').replace('-', '_')[:50]
            node['id'] = node_id
            changes.append(f"Added ID '{node_id}' to node: {label[:50]}")
        
        # Ensure uniqueness
        original_id = node_id
        counter = 1
        while node_id in used_ids:
            node_id = f"{original_id}_{counter}"
            counter += 1
        
        if node_id != original_id:
            node['id'] = node_id
            changes.append(f"Renamed ID from '{original_id}' to '{node_id}' for node: {label[:50]}")
        
        used_ids.add(node_id)
    
    flowchart['nodes'] = nodes
    return flowchart, changes

def update_complexity(flowchart: Dict, and_count: int, or_count: int) -> Dict:
    """
    Update complexity section with correct AND/OR counts.
    """
    complexity = flowchart.get('complexity', {})
    logic_gates = complexity.get('logicGates', {})
    
    logic_gates['orGates'] = or_count
    logic_gates['andGates'] = and_count
    logic_gates['total'] = and_count + or_count
    
    complexity['logicGates'] = logic_gates
    flowchart['complexity'] = complexity
    
    return flowchart

def process_file(file_path: Path, dry_run: bool = False) -> Dict:
    """
    Process a single JSON file.
    
    Returns:
        Dict with analysis results and fixes
    """
    result = {
        'file': str(file_path),
        'errors': [],
        'warnings': [],
        'fixes': [],
        'and_count': 0,
        'or_count': 0,
        'problematic_nodes': [],
        'id_changes': []
    }
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        flowchart = data.get('flowchart', {})
        if not flowchart:
            result['errors'].append("No flowchart section found")
            return result
        
        # Analyze nodes
        node_stats, node_ids, issues = analyze_nodes(flowchart)
        result['warnings'].extend(issues)
        
        # Classify AND/OR nodes
        and_count, or_count, problematic = classify_and_count_nodes(node_stats, node_ids)
        result['and_count'] = and_count
        result['or_count'] = or_count
        result['problematic_nodes'] = problematic
        
        # Get current counts for comparison
        current_complexity = data.get('complexity', {})
        current_logic_gates = current_complexity.get('logicGates', {})
        current_and = current_logic_gates.get('andGates', 0)
        current_or = current_logic_gates.get('orGates', 0)
        
        # Fix node IDs
        updated_flowchart, id_changes = fix_node_ids(flowchart)
        result['id_changes'] = id_changes
        
        # Update complexity if counts changed
        if and_count != current_and or or_count != current_or:
            if not dry_run:
                updated_flowchart = update_complexity(updated_flowchart, and_count, or_count)
                data['flowchart'] = updated_flowchart
                result['fixes'].append(f"Updated AND/OR counts: AND {current_and}→{and_count}, OR {current_or}→{or_count}")
            else:
                result['fixes'].append(f"Would update AND/OR counts: AND {current_and}→{and_count}, OR {current_or}→{or_count}")
        
        # Save if not dry run and changes made
        if not dry_run and (id_changes or result['fixes']):
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            result['fixes'].append("File updated")
        
    except Exception as e:
        result['errors'].append(f"Error processing file: {str(e)}")
    
    return result

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze and fix process nodes (AND/OR counting and unique IDs)")
    parser.add_argument('directories', nargs='+', help='Directories containing process JSON files')
    parser.add_argument('--dry-run', action='store_true', help='Analyze only, do not modify files')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    args = parser.parse_args()
    
    all_results = []
    
    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Error: Directory not found: {directory}", file=sys.stderr)
            continue
        
        json_files = list(dir_path.rglob('*.json'))
        json_files = [f for f in json_files if not f.name.endswith('.backup')]
        
        print(f"\nProcessing {len(json_files)} files in {directory}...")
        
        for json_file in json_files:
            result = process_file(json_file, dry_run=args.dry_run)
            all_results.append(result)
            
            if args.verbose or result['errors'] or result['problematic_nodes'] or result['fixes']:
                print(f"\n{json_file.name}:")
                if result['errors']:
                    for error in result['errors']:
                        print(f"  ERROR: {error}")
                if result['problematic_nodes']:
                    print(f"  WARNING: {len(result['problematic_nodes'])} AND/OR nodes (2+ in, 2+ out):")
                    for node in result['problematic_nodes'][:3]:  # Show first 3
                        print(f"    - {node}")
                if result['fixes']:
                    for fix in result['fixes']:
                        print(f"  FIX: {fix}")
                if result['id_changes']:
                    print(f"  ID Changes: {len(result['id_changes'])}")
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    total_files = len(all_results)
    files_with_errors = sum(1 for r in all_results if r['errors'])
    files_with_problematic = sum(1 for r in all_results if r['problematic_nodes'])
    files_fixed = sum(1 for r in all_results if r['fixes'])
    
    total_and = sum(r['and_count'] for r in all_results)
    total_or = sum(r['or_count'] for r in all_results)
    
    print(f"Total files processed: {total_files}")
    print(f"Files with errors: {files_with_errors}")
    print(f"Files with AND/OR nodes (2+ in, 2+ out): {files_with_problematic}")
    print(f"Files fixed: {files_fixed}")
    print(f"Total AND nodes: {total_and}")
    print(f"Total OR nodes: {total_or}")
    
    if files_with_problematic > 0:
        print(f"\n⚠️  {files_with_problematic} files have AND/OR nodes (2+ incoming AND 2+ outgoing edges)")
        print("   Review these manually and classify as either AND or OR")

if __name__ == '__main__':
    main()
