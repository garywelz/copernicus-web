#!/usr/bin/env python3
"""
GLMP Database Analyzer
Creates a summary table of all GLMP processes with statistical analysis
"""

import json
import requests

def fetch_glmp_metadata():
    """Fetch GLMP metadata from Google Cloud Storage"""
    url = "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/data/metadata.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None

def print_table_row(data, width=15):
    """Print a formatted table row"""
    formatted = []
    for item in data:
        if isinstance(item, str):
            formatted.append(str(item)[:width-1].ljust(width))
        else:
            formatted.append(str(item).ljust(width))
    return "|".join(formatted)

def analyze_processes(data):
    """Analyze GLMP processes and create summary statistics"""
    if not data or 'processes' not in data:
        return None
    
    processes = data['processes']
    
    # Initialize totals
    total_nodes = 0
    total_or_gates = 0
    total_and_gates = 0
    total_gates = 0
    complexity_counts = {}
    category_counts = {}
    organism_counts = {}
    
    print("\n" + "="*140)
    print("🧬 GLMP DATABASE SUMMARY TABLE")
    print("="*140)
    
    # Table headers
    headers = ["Process Name", "Organism", "Category", "Complexity", "Nodes", "OR Gates", "AND Gates", "Total Gates"]
    print(print_table_row(headers, 17))
    print("-" * 140)
    
    # Process each entry
    for process in processes:
        # Extract data
        name = process.get('name', 'Unknown')[:16]  # Truncate long names
        organism = process.get('organism', 'Unknown')[:16]
        category = process.get('category', 'Unknown')[:16]
        complexity = process.get('complexity', 'Unknown')[:16]
        nodes = process.get('nodes', 0)
        logic_gates = process.get('logicGates', {})
        or_gates = logic_gates.get('or', 0)
        and_gates = logic_gates.get('and', 0)
        total_process_gates = logic_gates.get('total', 0)
        
        # Print row
        row_data = [name, organism, category, complexity, nodes, or_gates, and_gates, total_process_gates]
        print(print_table_row(row_data, 17))
        
        # Update totals
        total_nodes += nodes
        total_or_gates += or_gates
        total_and_gates += and_gates
        total_gates += total_process_gates
        
        # Count categories
        complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        organism_counts[organism] = organism_counts.get(organism, 0) + 1
    
    print("-" * 140)
    
    # Summary statistics
    print(f"\n📊 TOTALS:")
    print(f"   Total Processes: {len(processes)}")
    print(f"   Total Nodes: {total_nodes}")
    print(f"   Total OR Gates: {total_or_gates}")
    print(f"   Total AND Gates: {total_and_gates}")
    print(f"   Total Logic Gates: {total_gates}")
    
    # Complexity breakdown
    print(f"\n🎯 COMPLEXITY BREAKDOWN:")
    for complexity, count in sorted(complexity_counts.items()):
        print(f"   {complexity.capitalize()}: {count} processes")
    
    # Category breakdown
    print(f"\n📂 CATEGORY BREAKDOWN:")
    for category, count in sorted(category_counts.items()):
        print(f"   {category}: {count} processes")
    
    # Organism breakdown
    print(f"\n🧬 ORGANISM BREAKDOWN:")
    for organism, count in sorted(organism_counts.items()):
        print(f"   {organism}: {count} processes")
    
    # Averages
    avg_nodes = total_nodes / len(processes) if len(processes) > 0 else 0
    avg_gates = total_gates / len(processes) if len(processes) > 0 else 0
    
    print(f"\n📈 AVERAGES:")
    print(f"   Average Nodes per Process: {avg_nodes:.1f}")
    print(f"   Average Gates per Process: {avg_gates:.1f}")
    
    print("\n" + "="*140)
    
    return True

def main():
    print("🔍 Fetching GLMP database metadata...")
    data = fetch_glmp_metadata()
    
    if data:
        print(f"✅ Found {data.get('totalProcesses', 0)} processes")
        print("📊 Analyzing process data...")
        
        success = analyze_processes(data)
        if not success:
            print("❌ Failed to analyze process data")
    else:
        print("❌ Failed to fetch GLMP metadata")

if __name__ == "__main__":
    main()