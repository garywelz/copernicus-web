#!/usr/bin/env python3
"""
Quality Audit Script for Process Databases
Checks for common issues: broken links, incorrect references, missing sources, etc.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

ISSUES = {
    "critical": [],
    "high": [],
    "medium": [],
    "low": []
}

DISCIPLINES = {
    "biology": {
        "dir": "biology-processes-database",
        "category": "biology",
        "name": "Biology Processes Database",
        "description": "Biology processes visualized using the Programming Framework with 5-color scheme."
    },
    "chemistry": {
        "dir": "chemistry-processes-database",
        "category": "chemistry",
        "name": "Chemistry Processes Database",
        "description": "Chemistry processes visualized using the Programming Framework with 5-color scheme."
    },
    "physics": {
        "dir": "physics-processes-database",
        "category": "physics",
        "name": "Physics Processes Database",
        "description": "Physics processes visualized using the Programming Framework with 5-color scheme."
    },
    "mathematics": {
        "dir": "mathematics-processes-database",
        "category": "mathematics",
        "name": "Mathematics Processes Database",
        "description": "Mathematics processes visualized using the Programming Framework with 5-color scheme."
    },
    "computer_science": {
        "dir": "computer-science-processes-database",
        "category": "computer_science",
        "name": "Computer Science Processes Database",
        "description": "Computer Science processes visualized using the Programming Framework with 5-color scheme."
    }
}

def check_biology_links():
    """Check biology process viewers for incorrect chemistry references"""
    biology_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space/biology-processes-database/processes")
    issues = []
    
    for html_file in biology_dir.rglob("*.html"):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for chemistry references
        if 'chemistry' in content.lower() and 'biology' not in content.lower():
            if 'Back to Chemistry Database' in content:
                issues.append(f"CRITICAL: {html_file.name} links to Chemistry Database")
            if 'chemistry-processes-database' in content:
                issues.append(f"CRITICAL: {html_file.name} has chemistry path in back link")
            if 'Chemistry Process' in content:
                issues.append(f"HIGH: {html_file.name} has 'Chemistry Process' in title")
    
    return issues

def check_source_references():
    """Check if processes have actual paper references (not just methodology)"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    issues = []
    
    disciplines = ["biology", "chemistry", "physics", "computer-science", "mathematics"]
    
    for discipline in disciplines:
        db_dir = base_dir / f"{discipline}-processes-database"
        if not db_dir.exists():
            continue
            
        for json_file in (db_dir / "processes").rglob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            sources = data.get('sources', [])
            if not sources:
                issues.append(f"HIGH: {json_file.name} has no sources")
            else:
                # Check if sources are just methodology references
                has_paper = False
                for source in sources:
                    if source.get('doi') or (source.get('journal') and source.get('journal') != 'CopernicusAI Knowledge Engine'):
                        has_paper = True
                        break
                
                if not has_paper:
                    issues.append(f"HIGH: {json_file.name} only has methodology reference, no actual papers")
    
    return issues

def check_mermaid_syntax():
    """Check for common Mermaid syntax issues"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    issues = []
    
    disciplines = ["biology", "chemistry", "physics", "computer-science", "mathematics"]
    
    for discipline in disciplines:
        db_dir = base_dir / f"{discipline}-processes-database"
        if not db_dir.exists():
            continue
            
        for json_file in (db_dir / "processes").rglob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mermaid = data.get('mermaid', '')
            
            # Check for duplicate style statements
            style_lines = [line for line in mermaid.split('\n') if line.strip().startswith('style ')]
            node_styles = {}
            for line in style_lines:
                match = re.match(r'style\s+(\w+)', line)
                if match:
                    node = match.group(1)
                    if node in node_styles:
                        issues.append(f"MEDIUM: {json_file.name} has duplicate style for node {node}")
                    node_styles[node] = line
            
            # Check for unclosed brackets
            if mermaid.count('[') != mermaid.count(']'):
                issues.append(f"HIGH: {json_file.name} has unclosed brackets in Mermaid")
            if mermaid.count('{') != mermaid.count('}'):
                issues.append(f"HIGH: {json_file.name} has unclosed braces in Mermaid")
    
    return issues

def check_metadata_accuracy():
    """Check if metadata.json matches actual file counts"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    issues = []
    
    disciplines = ["biology", "chemistry", "physics", "computer-science", "mathematics"]
    
    for discipline in disciplines:
        db_dir = base_dir / f"{discipline}-processes-database"
        if not db_dir.exists():
            continue
        
        metadata_file = db_dir / "metadata.json"
        if not metadata_file.exists():
            issues.append(f"CRITICAL: {discipline} missing metadata.json")
            continue
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Count actual JSON files
        actual_count = len(list((db_dir / "processes").rglob("*.json")))
        stated_count = metadata.get('totalProcesses', 0)
        
        if actual_count != stated_count:
            issues.append(f"HIGH: {discipline} metadata says {stated_count} processes but found {actual_count}")
        
        # Check subcategory counts
        subcat_counts = metadata.get('subcategoryCounts', {})
        for subcat, stated_count in subcat_counts.items():
            subcat_dir = db_dir / "processes" / subcat
            if subcat_dir.exists():
                actual_count = len(list(subcat_dir.glob("*.json")))
                if actual_count != stated_count:
                    issues.append(f"MEDIUM: {discipline}/{subcat} metadata says {stated_count} but found {actual_count}")
    
    return issues

def _iter_process_json_files(processes_dir: Path) -> List[Path]:
    """Return process JSON files excluding backups and metadata.json."""
    files: List[Path] = []
    for p in processes_dir.rglob("*.json"):
        if p.name == "metadata.json":
            continue
        # Exclude "*.json.backup" files
        if p.name.endswith(".backup") or p.suffix == ".backup":
            continue
        files.append(p)
    return files

def rebuild_metadata_from_processes(db_dir: Path, discipline_key: str, *, dry_run: bool = False) -> Tuple[Dict, int]:
    """
    Rebuild `metadata.json` from the process JSONs on disk, using the per-process
    `complexity.logicGates` counts (which match the individual viewer pages).
    """
    config = DISCIPLINES[discipline_key]
    processes_dir = db_dir / "processes"
    if not processes_dir.exists():
        raise FileNotFoundError(f"Missing processes directory: {processes_dir}")

    json_files = _iter_process_json_files(processes_dir)
    processes: List[Dict] = []

    totals = {
        "totalNodes": 0,
        "totalEdges": 0,
        "totalConditionals": 0,
        "totalOrGates": 0,
        "totalAndGates": 0,
        "totalGates": 0,
    }
    subcat_counts: Dict[str, int] = {}

    for json_path in json_files:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # IMPORTANT: metadata entries (and viewer URLs) use the filename stem, not the JSON's internal `id`.
        file_id = json_path.stem

        subcat = data.get("subcategory") or json_path.parent.name
        subcat_name = data.get("subcategory_name") or subcat.replace("_", " ").title()
        complexity = data.get("complexity") or {}
        logic = complexity.get("logicGates") or {}

        nodes = int(complexity.get("nodes") or 0)
        edges = int(complexity.get("edges") or 0)
        conditionals = int(complexity.get("conditionals") or 0)
        or_gates = int(logic.get("orGates") or 0)
        and_gates = int(logic.get("andGates") or 0)

        processes.append(
            {
                "id": file_id,
                "name": data.get("name", file_id),
                "subcategory": subcat,
                "subcategory_name": subcat_name,
                "complexity": complexity.get("level") or complexity.get("detailLevel") or "unknown",
                "nodes": nodes,
                "edges": edges,
                "orGates": or_gates,
                "andGates": and_gates,
                "totalGates": or_gates + and_gates,
            }
        )

        totals["totalNodes"] += nodes
        totals["totalEdges"] += edges
        totals["totalConditionals"] += conditionals
        totals["totalOrGates"] += or_gates
        totals["totalAndGates"] += and_gates
        subcat_counts[subcat] = subcat_counts.get(subcat, 0) + 1

    totals["totalGates"] = totals["totalOrGates"] + totals["totalAndGates"]

    # Sort processes for stable output (subcategory then name)
    processes.sort(key=lambda p: (p.get("subcategory", ""), p.get("name", "")))

    metadata_path = db_dir / "metadata.json"
    existing: Optional[Dict] = None
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = None

    today = datetime.utcnow().strftime("%Y-%m-%d")
    metadata = {
        "name": (existing or {}).get("name", config["name"]),
        "version": (existing or {}).get("version", "1.0.0"),
        "created": (existing or {}).get("created", today),
        "lastUpdated": today,
        "category": (existing or {}).get("category", config["category"]),
        "colorScheme": (existing or {}).get("colorScheme", "5-color"),
        "description": (existing or {}).get("description", config["description"]),
        "totalProcesses": len(processes),
        "subcategories": len(subcat_counts),
        "statistics": totals,
        "subcategoryCounts": subcat_counts,
        "processes": processes,
    }

    if not dry_run:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata, len(processes)

def check_back_links():
    """Check if all process viewers have correct back links"""
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    issues = []
    
    discipline_map = {
        "biology": "biology",
        "chemistry": "chemistry",
        "physics": "physics",
        "computer-science": "computer_science",
        "mathematics": "mathematics"
    }
    
    for discipline_dir, discipline_name in discipline_map.items():
        db_dir = base_dir / f"{discipline_dir}-processes-database"
        if not db_dir.exists():
            continue
        
        for html_file in (db_dir / "processes").rglob("*.html"):
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if back link references correct discipline
            expected_db = f"{discipline_name}-database-table.html"
            if expected_db not in content:
                # Check for wrong discipline references
                for other_discipline in ["chemistry", "physics", "computer_science", "mathematics", "biology"]:
                    if other_discipline != discipline_name:
                        wrong_db = f"{other_discipline}-database-table.html"
                        if wrong_db in content:
                            issues.append(f"CRITICAL: {html_file.name} links to {other_discipline} instead of {discipline_name}")
    
    return issues

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Quality audit for process databases")
    parser.add_argument("--fix-metadata", action="store_true", help="Rebuild metadata.json from process JSONs")
    parser.add_argument("--dry-run", action="store_true", help="With --fix-metadata, do not write files")
    parser.add_argument(
        "--disciplines",
        nargs="*",
        choices=list(DISCIPLINES.keys()),
        help="Subset of disciplines to process (default: all supported disciplines)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Quality Audit for Process Databases")
    print("=" * 60)
    print()

    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")

    if args.fix_metadata:
        selected = args.disciplines or list(DISCIPLINES.keys())
        print(f"Rebuilding metadata.json from process JSONs ({', '.join(selected)})")
        for discipline_key in selected:
            db_dir = base_dir / DISCIPLINES[discipline_key]["dir"]
            if not db_dir.exists():
                print(f"  - Skipping {discipline_key}: directory not found ({db_dir})")
                continue
            metadata, count = rebuild_metadata_from_processes(db_dir, discipline_key, dry_run=args.dry_run)
            print(f"  - {discipline_key}: {count} processes, totalAndGates={metadata['statistics']['totalAndGates']}, totalOrGates={metadata['statistics']['totalOrGates']}")
        print()
    
    all_issues = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }
    
    print("1. Checking biology links...")
    issues = check_biology_links()
    for issue in issues:
        if "CRITICAL" in issue:
            all_issues["critical"].append(issue)
        elif "HIGH" in issue:
            all_issues["high"].append(issue)
        else:
            all_issues["medium"].append(issue)
    
    print("2. Checking source references...")
    issues = check_source_references()
    all_issues["high"].extend(issues)
    
    print("3. Checking Mermaid syntax...")
    issues = check_mermaid_syntax()
    for issue in issues:
        if "HIGH" in issue:
            all_issues["high"].append(issue)
        else:
            all_issues["medium"].append(issue)
    
    print("4. Checking metadata accuracy...")
    issues = check_metadata_accuracy()
    for issue in issues:
        if "CRITICAL" in issue:
            all_issues["critical"].append(issue)
        elif "HIGH" in issue:
            all_issues["high"].append(issue)
        else:
            all_issues["medium"].append(issue)
    
    print("5. Checking back links...")
    issues = check_back_links()
    all_issues["critical"].extend(issues)
    
    print()
    print("=" * 60)
    print("QUALITY AUDIT RESULTS")
    print("=" * 60)
    print()
    
    for severity in ["critical", "high", "medium", "low"]:
        if all_issues[severity]:
            print(f"\n{severity.upper()} ISSUES ({len(all_issues[severity])}):")
            for issue in all_issues[severity][:20]:  # Show first 20
                print(f"  - {issue}")
            if len(all_issues[severity]) > 20:
                print(f"  ... and {len(all_issues[severity]) - 20} more")
    
    print()
    print("=" * 60)
    total = sum(len(issues) for issues in all_issues.values())
    print(f"Total Issues Found: {total}")
    print("=" * 60)

if __name__ == "__main__":
    main()
