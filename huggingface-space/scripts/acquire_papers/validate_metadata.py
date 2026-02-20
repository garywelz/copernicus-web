#!/usr/bin/env python3
"""
Metadata Validation Script

Validates paper metadata against the unified schema for NSF Objective 2 compliance.
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
REQUIRED_FIELDS = ["id", "title", "source", "acquired_date"]
QUALITY_FIELDS = ["title", "authors", "journal", "year", "abstract", "doi", "url", "category"]
QUALITY_THRESHOLD = 0.85  # NSF proposal requires >=85% metadata quality

def validate_doi(doi: Optional[str]) -> bool:
    """Validate DOI format."""
    if not doi:
        return False
    # Basic DOI pattern: 10.xxxx/xxxxx
    pattern = r'^10\.\d{4,}/.+'
    return bool(re.match(pattern, doi))

def validate_year(year: Optional[str]) -> bool:
    """Validate year format."""
    if not year:
        return False
    try:
        year_int = int(year)
        return 1800 <= year_int <= datetime.now().year + 1
    except (ValueError, TypeError):
        return False

def validate_url(url: Optional[str]) -> bool:
    """Validate URL format."""
    if not url:
        return False
    # Basic URL validation
    pattern = r'^https?://.+'
    return bool(re.match(pattern, url))

def calculate_metadata_quality(paper: Dict) -> Tuple[float, Dict[str, bool]]:
    """
    Calculate metadata quality score (0.0 to 1.0).
    Returns: (quality_score, field_status)
    """
    field_status = {}
    filled_count = 0
    valid_count = 0
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        has_field = field in paper and paper[field] is not None
        field_status[f"required_{field}"] = has_field
        if has_field:
            filled_count += 1
            valid_count += 1
    
    # Check quality fields
    for field in QUALITY_FIELDS:
        has_field = field in paper and paper[field] is not None and paper[field] != ""
        field_status[f"has_{field}"] = has_field
        
        if has_field:
            filled_count += 1
            
            # Validate field content
            if field == "doi":
                is_valid = validate_doi(paper[field])
            elif field == "year":
                is_valid = validate_year(paper[field])
            elif field == "url":
                is_valid = validate_url(paper[field])
            elif field == "authors":
                is_valid = isinstance(paper[field], list) and len(paper[field]) > 0
            elif field == "abstract":
                is_valid = len(str(paper[field])) > 50  # Minimum abstract length
            else:
                is_valid = True  # Other fields just need to exist
            
            field_status[f"valid_{field}"] = is_valid
            if is_valid:
                valid_count += 1
        else:
            field_status[f"valid_{field}"] = False
    
    # Calculate quality score
    total_fields = len(REQUIRED_FIELDS) + len(QUALITY_FIELDS)
    quality_score = valid_count / total_fields if total_fields > 0 else 0.0
    
    return quality_score, field_status

def validate_paper(paper: Dict, schema: Optional[Dict] = None) -> Tuple[bool, List[str], float]:
    """
    Validate a single paper against schema and quality requirements.
    Returns: (is_valid, errors, quality_score)
    """
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in paper or paper[field] is None or paper[field] == "":
            errors.append(f"Missing required field: {field}")
    
    # Validate ID format
    if "id" in paper and paper["id"]:
        id_parts = paper["id"].split("_", 1)
        if len(id_parts) != 2:
            errors.append(f"Invalid ID format: {paper['id']} (expected: source_identifier)")
        elif "source" in paper and id_parts[0] != paper["source"]:
            errors.append(f"ID source mismatch: ID starts with '{id_parts[0]}' but source is '{paper['source']}'")
    
    # Validate source
    valid_sources = ["pubmed", "arxiv", "nasa_ads", "crossref"]
    if "source" in paper and paper["source"] not in valid_sources:
        errors.append(f"Invalid source: {paper['source']} (must be one of: {', '.join(valid_sources)})")
    
    # Validate category
    valid_categories = ["biology", "chemistry", "physics", "mathematics", "computer_science", "interdisciplinary", "foundational"]
    if "category" in paper and paper["category"] not in valid_categories:
        errors.append(f"Invalid category: {paper['category']} (must be one of: {', '.join(valid_categories)})")
    
    # Validate DOI format
    if "doi" in paper and paper["doi"]:
        if not validate_doi(paper["doi"]):
            errors.append(f"Invalid DOI format: {paper['doi']}")
    
    # Validate year
    if "year" in paper and paper["year"]:
        if not validate_year(paper["year"]):
            errors.append(f"Invalid year: {paper['year']}")
    
    # Validate URL
    if "url" in paper and paper["url"]:
        if not validate_url(paper["url"]):
            errors.append(f"Invalid URL format: {paper['url']}")
    
    # Validate acquired_date format
    if "acquired_date" in paper and paper["acquired_date"]:
        try:
            datetime.fromisoformat(paper["acquired_date"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            errors.append(f"Invalid acquired_date format: {paper['acquired_date']} (expected ISO 8601)")
    
    # Calculate quality score
    quality_score, field_status = calculate_metadata_quality(paper)
    
    # Check quality threshold (NSF requirement: >=85%)
    if quality_score < QUALITY_THRESHOLD:
        errors.append(f"Metadata quality below threshold: {quality_score:.1%} < {QUALITY_THRESHOLD:.1%}")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors, quality_score

def validate_file(filepath: Path, schema: Optional[Dict] = None) -> Dict:
    """Validate a single JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            paper = json.load(f)
        
        is_valid, errors, quality_score = validate_paper(paper, schema)
        
        return {
            "file": str(filepath),
            "valid": is_valid,
            "quality_score": quality_score,
            "errors": errors,
            "passes_quality_threshold": quality_score >= QUALITY_THRESHOLD
        }
    except json.JSONDecodeError as e:
        return {
            "file": str(filepath),
            "valid": False,
            "quality_score": 0.0,
            "errors": [f"JSON decode error: {e}"],
            "passes_quality_threshold": False
        }
    except Exception as e:
        return {
            "file": str(filepath),
            "valid": False,
            "quality_score": 0.0,
            "errors": [f"Error reading file: {e}"],
            "passes_quality_threshold": False
        }

def validate_directory(directory: Path, recursive: bool = True) -> Dict:
    """Validate all JSON files in a directory."""
    results = {
        "directory": str(directory),
        "total_files": 0,
        "valid_files": 0,
        "invalid_files": 0,
        "avg_quality_score": 0.0,
        "files_above_threshold": 0,
        "files_below_threshold": 0,
        "results": []
    }
    
    json_files = list(directory.rglob("*.json")) if recursive else list(directory.glob("*.json"))
    results["total_files"] = len(json_files)
    
    if not json_files:
        return results
    
    quality_scores = []
    
    for json_file in json_files:
        result = validate_file(json_file)
        results["results"].append(result)
        
        if result["valid"]:
            results["valid_files"] += 1
        else:
            results["invalid_files"] += 1
        
        quality_scores.append(result["quality_score"])
        
        if result["passes_quality_threshold"]:
            results["files_above_threshold"] += 1
        else:
            results["files_below_threshold"] += 1
    
    results["avg_quality_score"] = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    return results

def main():
    """Main function to run validation."""
    import argparse
    global QUALITY_THRESHOLD
    
    parser = argparse.ArgumentParser(description="Validate paper metadata against unified schema")
    parser.add_argument("path", type=str, help="File or directory path to validate")
    parser.add_argument("--schema", type=str, help="Path to schema file (default: metadata_schema.json)")
    parser.add_argument("--recursive", action="store_true", default=True, help="Recurse into subdirectories")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--threshold", type=float, default=QUALITY_THRESHOLD, help="Quality threshold (default: 0.85)")
    args = parser.parse_args()
    
    QUALITY_THRESHOLD = args.threshold
    
    path = Path(args.path)
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        sys.exit(1)
    
    # Load schema if provided
    schema = None
    if args.schema:
        schema_path = Path(args.schema)
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = json.load(f)
    
    # Validate
    if path.is_file():
        result = validate_file(path, schema)
        results = {
            "validation": result,
            "threshold": QUALITY_THRESHOLD
        }
    else:
        results = validate_directory(path, args.recursive)
        results["threshold"] = QUALITY_THRESHOLD
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        if path.is_file():
            result = results["validation"]
            print(f"File: {result['file']}")
            print(f"Valid: {'✅' if result['valid'] else '❌'}")
            print(f"Quality Score: {result['quality_score']:.1%}")
            print(f"Passes Threshold ({QUALITY_THRESHOLD:.1%}): {'✅' if result['passes_quality_threshold'] else '❌'}")
            if result['errors']:
                print("\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")
        else:
            print(f"Directory: {results['directory']}")
            print(f"Total Files: {results['total_files']}")
            print(f"Valid Files: {results['valid_files']} ({results['valid_files']/results['total_files']*100:.1f}%)")
            print(f"Invalid Files: {results['invalid_files']} ({results['invalid_files']/results['total_files']*100:.1f}%)")
            print(f"Average Quality Score: {results['avg_quality_score']:.1%}")
            print(f"Files Above Threshold ({QUALITY_THRESHOLD:.1%}): {results['files_above_threshold']} ({results['files_above_threshold']/results['total_files']*100:.1f}%)")
            print(f"Files Below Threshold: {results['files_below_threshold']} ({results['files_below_threshold']/results['total_files']*100:.1f}%)")
            
            # Show files below threshold
            if results['files_below_threshold'] > 0:
                print("\nFiles Below Quality Threshold:")
                for result in results['results']:
                    if not result['passes_quality_threshold']:
                        print(f"  - {result['file']}: {result['quality_score']:.1%} (errors: {len(result['errors'])})")

if __name__ == "__main__":
    main()
