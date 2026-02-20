#!/usr/bin/env python3
"""
Process Metadata Validation Script

Validates process metadata against the unified schema for NSF Objective 2 compliance.
Ensures metadata quality >=85% (NSF proposal success criteria).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

# Configuration
SCHEMA_FILE = Path(__file__).parent / "metadata_schema.json"
REQUIRED_FIELDS = ["id", "name", "category", "source", "acquired_date"]
QUALITY_FIELDS = ["id", "name", "category", "description", "mermaid", "sources", "keywords", "complexity"]
QUALITY_THRESHOLD = 0.85  # NSF proposal requires >=85% metadata quality

def validate_id_format(process_id: str) -> bool:
    """Validate process ID format: process_{category}_{subcategory}-{name}"""
    if not process_id:
        return False
    # Pattern: process_biology_dna-replication or process_chemistry_glycolysis
    pattern = r'^process_[a-z]+_[a-z0-9._-]+$'
    return bool(re.match(pattern, process_id))

def validate_category(category: Optional[str]) -> bool:
    """Validate category is in allowed list."""
    valid_categories = ["biology", "chemistry", "physics", "mathematics", "computer_science", "interdisciplinary", "foundational"]
    return category in valid_categories

def validate_mermaid(mermaid: Optional[str]) -> bool:
    """Basic validation that mermaid code exists."""
    if not mermaid:
        return False
    # Basic check: contains graph/node syntax
    return bool(re.search(r'graph|flowchart|node|-->', mermaid, re.IGNORECASE))

def validate_sources(sources: Optional[List]) -> bool:
    """Validate sources array structure."""
    if not sources:
        return False
    if not isinstance(sources, list):
        return False
    # Should have at least one source
    return len(sources) > 0

def calculate_metadata_quality(process: Dict) -> Tuple[float, Dict[str, bool]]:
    """
    Calculate metadata quality score (0.0 to 1.0).
    Returns: (score, field_status_dict)
    """
    field_status = {}
    total_score = 0.0
    
    # Check each quality field
    for field in QUALITY_FIELDS:
        value = process.get(field)
        is_valid = False
        
        if field == "id":
            is_valid = validate_id_format(value)
        elif field == "category":
            is_valid = validate_category(value)
        elif field == "mermaid":
            is_valid = validate_mermaid(value)
        elif field == "sources":
            is_valid = validate_sources(value)
        elif field == "name":
            is_valid = bool(value and len(str(value).strip()) > 0)
        elif field == "description":
            is_valid = bool(value and len(str(value).strip()) > 10)  # At least some description
        elif field == "keywords":
            is_valid = bool(value and isinstance(value, list) and len(value) > 0)
        elif field == "complexity":
            is_valid = bool(value and isinstance(value, dict) and "nodes" in value)
        else:
            is_valid = value is not None
        
        field_status[field] = is_valid
        if is_valid:
            total_score += 1.0
    
    quality_score = total_score / len(QUALITY_FIELDS) if QUALITY_FIELDS else 0.0
    return quality_score, field_status

def validate_process(process: Dict, schema: Optional[Dict] = None) -> Tuple[bool, List[str], float, Dict[str, bool]]:
    """
    Validate a single process against the schema.
    Returns: (is_valid, errors, quality_score, field_status)
    """
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in process or not process[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate ID format
    if "id" in process and not validate_id_format(process["id"]):
        errors.append(f"Invalid ID format: {process['id']} (expected: process_{{category}}_{{subcategory}}-{{name}})")
    
    # Validate category
    if "category" in process and not validate_category(process["category"]):
        errors.append(f"Invalid category: {process['category']}")
    
    # Validate mermaid exists
    if "mermaid" in process and not validate_mermaid(process["mermaid"]):
        errors.append("Invalid or missing mermaid flowchart syntax")
    
    # Calculate quality score
    quality_score, field_status = calculate_metadata_quality(process)
    
    # Check quality threshold
    if quality_score < QUALITY_THRESHOLD:
        errors.append(f"Quality score {quality_score:.2%} below threshold {QUALITY_THRESHOLD:.2%}")
    
    is_valid = len(errors) == 0 and quality_score >= QUALITY_THRESHOLD
    return is_valid, errors, quality_score, field_status

def main():
    """Main validation function."""
    import argparse
    global QUALITY_THRESHOLD
    
    parser = argparse.ArgumentParser(description="Validate process metadata against unified schema")
    parser.add_argument("paths", nargs="+", help="Paths to process JSON files or directories")
    parser.add_argument("--threshold", type=float, default=QUALITY_THRESHOLD,
                       help=f"Quality threshold (default: {QUALITY_THRESHOLD})")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()
    
    QUALITY_THRESHOLD = args.threshold
    
    # Load schema if available
    schema = None
    if SCHEMA_FILE.exists():
        try:
            with open(SCHEMA_FILE, 'r') as f:
                schema = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load schema: {e}", file=sys.stderr)
    
    # Collect all JSON files
    json_files = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == '.json':
            json_files.append(path)
        elif path.is_dir():
            json_files.extend(path.rglob("*.json"))
    
    if not json_files:
        print("No JSON files found", file=sys.stderr)
        sys.exit(1)
    
    # Validate each file
    results = []
    total_valid = 0
    total_invalid = 0
    quality_scores = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                process = json.load(f)
            
            is_valid, errors, quality_score, field_status = validate_process(process, schema)
            
            result = {
                "file": str(json_file),
                "id": process.get("id", "unknown"),
                "name": process.get("name", "unknown"),
                "valid": is_valid,
                "quality_score": quality_score,
                "errors": errors,
                "field_status": field_status
            }
            results.append(result)
            
            if is_valid:
                total_valid += 1
            else:
                total_invalid += 1
            quality_scores.append(quality_score)
            
        except Exception as e:
            result = {
                "file": str(json_file),
                "valid": False,
                "error": str(e)
            }
            results.append(result)
            total_invalid += 1
    
    # Output results
    if args.json:
        output = {
            "summary": {
                "total": len(results),
                "valid": total_valid,
                "invalid": total_invalid,
                "avg_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
                "threshold": QUALITY_THRESHOLD
            },
            "results": results
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("Process Metadata Validation Results")
        print("=" * 70)
        print(f"Total files: {len(results)}")
        print(f"Valid: {total_valid}")
        print(f"Invalid: {total_invalid}")
        if quality_scores:
            print(f"Average quality score: {sum(quality_scores) / len(quality_scores):.2%}")
        print(f"Quality threshold: {QUALITY_THRESHOLD:.2%}")
        print()
        
        # Show invalid files
        if total_invalid > 0:
            print("Invalid files:")
            for result in results:
                if not result.get("valid", False):
                    print(f"  {result['file']}")
                    if "errors" in result:
                        for error in result["errors"]:
                            print(f"    - {error}")
                    if "error" in result:
                        print(f"    - {result['error']}")
        
        # Show low quality files
        low_quality = [r for r in results if r.get("quality_score", 1.0) < QUALITY_THRESHOLD]
        if low_quality:
            print(f"\nFiles below quality threshold ({QUALITY_THRESHOLD:.2%}):")
            for result in sorted(low_quality, key=lambda x: x.get("quality_score", 0.0)):
                print(f"  {result['file']}: {result.get('quality_score', 0.0):.2%}")
    
    # Exit with error code if any invalid
    sys.exit(1 if total_invalid > 0 else 0)

if __name__ == "__main__":
    main()
