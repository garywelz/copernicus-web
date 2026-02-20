#!/usr/bin/env python3
"""
Extract Computer Science Flowcharts from HTML to JSON Format
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from collections import defaultdict
from typing import Dict, List, Tuple

# CS subcategory mapping
SUBCATEGORY_MAP = {
    "computer_science_batch_01": "algorithms_data_structures",
    "computer_science_batch_02": "machine_learning",
    "computer_science_batch_03": "networks",
    "computer_science_batch_04": "systems",
    "computer_science_batch_05": "security",
    "computer_science_batch_06": "software_engineering",
    "computer_science_batch_07": "theory"
}

SUBCATEGORY_NAMES = {
    "algorithms_data_structures": "Algorithms & Data Structures",
    "machine_learning": "Machine Learning",
    "networks": "Computer Networks",
    "systems": "Systems & Architecture",
    "security": "Security & Cryptography",
    "software_engineering": "Software Engineering",
    "theory": "Theoretical Computer Science"
}

COLOR_SCHEME = {
    "red": {"hex": "#ff6b6b", "category": "Triggers & Inputs"},
    "yellow": {"hex": "#ffd43b", "category": "Structures & Objects"},
    "green": {"hex": "#51cf66", "category": "Processing & Operations"},
    "blue": {"hex": "#74c0fc", "category": "Intermediates & States"},
    "violet": {"hex": "#b197fc", "category": "Products & Outputs"}
}

class CSHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.processes = []
        self.current_process = None
        self.in_mermaid = False
        self.in_h2 = False
        self.in_caption = False
        self.mermaid_content = []
        self.caption_content = []
        self.h2_content = []
        
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
                    elif 'figure-caption' in attr_value:
                        self.in_caption = True
                        self.caption_content = []
    
    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_h2 = False
            if self.h2_content:
                text = ''.join(self.h2_content).strip()
                match = re.match(r'(\d+)\.\s*(.+)', text)
                if match:
                    process_num, process_name = match.groups()
                    process_name = re.sub(r'\s+Process$', '', process_name)
                    self.current_process = {
                        'number': process_num,
                        'name': process_name,
                        'mermaid': '',
                        'description': ''
                    }
        elif tag == 'div':
            if self.in_mermaid:
                self.in_mermaid = False
                if self.current_process and self.mermaid_content:
                    mermaid = ''.join(self.mermaid_content).strip()
                    lines = []
                    for line in mermaid.split('\n'):
                        cleaned = re.sub(r'[ \t]+', ' ', line.strip())
                        if cleaned:
                            lines.append(cleaned)
                    
                    graph_lines = []
                    style_dict = {}
                    
                    for line in lines:
                        if line.strip().startswith('style '):
                            match = re.match(r'style\s+(\w+)', line)
                            if match:
                                node_name = match.group(1)
                                style_dict[node_name] = line
                        else:
                            graph_lines.append(line)
                    
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
                    caption = re.sub(r'^Figure\s+\d+\.\s*', '', caption)
                    caption = re.sub(r'<strong>|</strong>', '', caption)
                    self.current_process['description'] = caption
                    
                    if self.current_process.get('mermaid'):
                        self.processes.append(self.current_process.copy())
                    self.current_process = None
    
    def handle_data(self, data):
        if self.in_h2:
            self.h2_content.append(data)
        elif self.in_mermaid:
            self.mermaid_content.append(data)
        elif self.in_caption:
            self.caption_content.append(data)

def count_mermaid_elements(mermaid_code: str) -> Tuple[int, int, int, int, int]:
    nodes = set()
    edges = 0
    conditionals = 0
    or_gates = 0
    and_gates = 0
    lines = mermaid_code.split('\n')
    for line in lines:
        line = line.strip()
        if '-->' in line:
            edges += 1
            parts = re.findall(r'(\w+)\[.*?\]', line)
            for part in parts:
                nodes.add(part)
            if re.search(r'\{.*?\}', line):
                conditionals += 1
        if re.search(r'\{.*?OR.*?\}', line, re.IGNORECASE):
            or_gates += 1
        if re.search(r'\{.*?AND.*?\}', line, re.IGNORECASE):
            and_gates += 1
    return len(nodes), edges, conditionals, or_gates, and_gates

def slugify(text: str) -> str:
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

def extract_processes_from_html(html_file_path: str, batch_name: str) -> List[Dict]:
    parser = CSHTMLParser()
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    parser.feed(html_content)
    return parser.processes

def create_json_and_metadata(input_dir: str, output_dir: str):
    all_processes_metadata = []
    process_count_by_subcategory = defaultdict(int)
    total_nodes = 0
    total_edges = 0
    total_conditionals = 0
    total_or_gates = 0
    total_and_gates = 0

    os.makedirs(os.path.join(output_dir, 'processes'), exist_ok=True)

    batch_files = sorted([f for f in os.listdir(input_dir) if f.startswith('computer_science_batch_') and f.endswith('.html')])
    print(f"Found {len(batch_files)} computer science batch files")

    for batch_file in batch_files:
        batch_name = os.path.splitext(batch_file)[0]
        subcategory_slug = SUBCATEGORY_MAP.get(batch_name)
        
        if not subcategory_slug:
            print(f"WARNING: No subcategory mapping found for {batch_name}. Skipping.")
            continue

        subcategory_name = SUBCATEGORY_NAMES.get(subcategory_slug, subcategory_slug.replace('_', ' ').title())
        batch_processes = extract_processes_from_html(os.path.join(input_dir, batch_file), batch_name)
        
        if not batch_processes:
            print(f"Processing: {batch_file}\n  ERROR: No processes were extracted")
            continue

        print(f"Processing: {batch_file}")
        os.makedirs(os.path.join(output_dir, 'processes', subcategory_slug), exist_ok=True)

        for i, process_data in enumerate(batch_processes):
            process_name = process_data['name']
            mermaid_code = process_data['mermaid']
            description = process_data['description']
            
            nodes, edges, conditionals, or_gates, and_gates = count_mermaid_elements(mermaid_code)

            if nodes < 15:
                complexity_level = "low"
            elif nodes < 30:
                complexity_level = "medium"
            else:
                complexity_level = "high"

            process_id = f"{subcategory_slug}-{slugify(process_name)}"
            
            json_data = {
                "id": process_id,
                "name": process_name,
                "category": "computer_science",
                "subcategory": subcategory_slug,
                "subcategory_name": subcategory_name,
                "description": description,
                "complexity": {
                    "nodes": nodes,
                    "edges": edges,
                    "conditionals": conditionals,
                    "logicGates": {
                        "orGates": or_gates,
                        "andGates": and_gates,
                        "total": or_gates + and_gates
                    },
                    "level": complexity_level,
                    "detailLevel": complexity_level
                },
                "colorScheme": COLOR_SCHEME,
                "mermaid": mermaid_code,
                "sources": [],
                "keywords": list(set(slugify(process_name).split('-') + slugify(subcategory_name).split('-'))),
                "relatedProcesses": [],
                "created": "2026-01-08",
                "lastUpdated": "2026-01-08",
                "verified": False,
                "notes": f"Converted from computer science batch HTML. Process number: {process_data['number']}."
            }

            json_output_path = os.path.join(output_dir, 'processes', subcategory_slug, f"{process_id}.json")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"  ✓ Created: {json_output_path.replace(output_dir + os.sep, '')}")
            
            all_processes_metadata.append({
                "id": process_id,
                "name": process_name,
                "subcategory": subcategory_slug,
                "subcategory_name": subcategory_name,
                "complexity": complexity_level,
                "nodes": nodes,
                "edges": edges,
                "orGates": or_gates,
                "andGates": and_gates,
                "totalGates": or_gates + and_gates
            })
            process_count_by_subcategory[subcategory_slug] += 1
            total_nodes += nodes
            total_edges += edges
            total_conditionals += conditionals
            total_or_gates += or_gates
            total_and_gates += and_gates

    metadata_json = {
        "name": "Computer Science Processes Database",
        "version": "1.0.0",
        "created": "2026-01-08",
        "lastUpdated": "2026-01-08",
        "category": "computer_science",
        "colorScheme": "5-color",
        "description": "Computer Science processes visualized using the Programming Framework with 5-color scheme. Converted from HTML batch files.",
        "totalProcesses": len(all_processes_metadata),
        "subcategories": len(process_count_by_subcategory),
        "statistics": {
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
            "totalConditionals": total_conditionals,
            "totalOrGates": total_or_gates,
            "totalAndGates": total_and_gates,
            "totalGates": total_or_gates + total_and_gates
        },
        "subcategoryCounts": dict(process_count_by_subcategory),
        "processes": all_processes_metadata
    }

    metadata_output_path = os.path.join(output_dir, 'metadata.json')
    with open(metadata_output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_json, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Created metadata.json: {metadata_output_path.replace(output_dir + os.sep, '')}")
    print(f"  Total processes: {len(all_processes_metadata)}")
    print(f"  Total subcategories: {len(process_count_by_subcategory)}")
    print(f"  Total nodes: {total_nodes}")
    print(f"  Total edges: {total_edges}")
    print(f"  Total OR gates: {total_or_gates}")
    print(f"  Total AND gates: {total_and_gates}")
    print("\n============================================================")
    print("Conversion complete!")
    print("============================================================")

if __name__ == "__main__":
    input_html_dir = "/home/gdubs/progframe/programming_framework"
    output_json_dir = "/home/gdubs/copernicus-web-public/huggingface-space/computer-science-processes-database"
    
    print("============================================================")
    print("Computer Science HTML to JSON Converter")
    print("============================================================")
    print(f"Input directory: {input_html_dir}")
    print(f"Output directory: {output_json_dir}\n")
    
    create_json_and_metadata(input_html_dir, output_json_dir)
