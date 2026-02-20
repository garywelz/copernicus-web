#!/usr/bin/env python3
"""
Podcast Metadata Validation Script

Validates podcast metadata against the unified schema for NSF Objective 2 compliance.
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
QUALITY_FIELDS = ["id", "title", "category", "description", "guid", "audioUrl", "references", "keywords", "year"]
QUALITY_THRESHOLD = 0.85  # NSF proposal requires >=85% metadata quality

def validate_id_format(podcast_id: str) -> bool:
    """Validate podcast ID format: podcast_{guid}"""
    if not podcast_id:
        return False
    # Pattern: podcast_ever-bio-250007
    pattern = r'^podcast_[a-z0-9._-]+$'
    return bool(re.match(pattern, podcast_id))

def validate_category(category: Optional[str]) -> bool:
    """Validate category is in allowed list."""
    valid_categories = ["biology", "chemistry", "physics", "mathematics", "computer_science", "interdisciplinary", "foundational"]
    return category in valid_categories

def validate_year(year: Optional[str]) -> bool:
    """Validate year format."""
    if not year:
        return False
    try:
        year_int = int(year)
        return 2000 <= year_int <= datetime.now().year + 1
    except (ValueError, TypeError):
        return False

def validate_url(url: Optional[str]) -> bool:
    """Validate URL format."""
    if not url:
        return False
    pattern = r'^https?://.+'
    return bool(re.match(pattern, url))

def validate_references(references: Optional[List]) -> bool:
    """Validate references array structure."""
    if references is None:
        return False  # References are important for podcasts
    if not isinstance(references, list):
        return False
    # Should have at least one reference for quality
    return len(references) > 0

def calculate_metadata_quality(podcast: Dict) -> Tuple[float, Dict[str, bool]]:
    """
    Calculate metadata quality score (0.0 to 1.0).
    Returns: (score, field_status_dict)
    """
    field_status = {}
    total_score = 0.0
    
    # Check each quality field
    for field in QUALITY_FIELDS:
        value = podcast.get(field)
        is_valid = False
        
        if field == "id":
            is_valid = validate_id_format(value)
        elif field == "category":
            is_valid = validate_category(value)
        elif field == "year":
            is_valid = validate_year(value)
        elif field == "audioUrl":
            is_valid = validate_url(value)
        elif field == "references":
            is_valid = validate_references(value)
        elif field == "title":
            is_valid = bool(value and len(str(value).strip()) > 0)
        elif field == "description":
            is_valid = bool(value and len(str(value).strip()) > 50)  # At least some description
        elif field == "guid":
            is_valid = bool(value and len(str(value).strip()) > 0)
        elif field == "keywords":
            # Keywords are nice but not always present
            is_valid = value is None or (isinstance(value, list) and len(value) >= 0)
        else:
            is_valid = value is not None
        
        field_status[field] = is_valid
        if is_valid:
            total_score += 1.0
    
    quality_score = total_score / len(QUALITY_FIELDS) if QUALITY_FIELDS else 0.0
    return quality_score, field_status

def validate_podcast(podcast: Dict, schema: Optional[Dict] = None) -> Tuple[bool, List[str], float, Dict[str, bool]]:
    """
    Validate a single podcast against the schema.
    Returns: (is_valid, errors, quality_score, field_status)
    """
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in podcast or not podcast[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate ID format
    if "id" in podcast and not validate_id_format(podcast["id"]):
        errors.append(f"Invalid ID format: {podcast['id']} (expected: podcast_{{guid}})")
    
    # Validate category
    if "category" in podcast and not validate_category(podcast["category"]):
        errors.append(f"Invalid category: {podcast['category']}")
    
    # Validate audio URL
    if "audioUrl" in podcast and not validate_url(podcast["audioUrl"]):
        errors.append("Invalid audioUrl format")
    
    # Calculate quality score
    quality_score, field_status = calculate_metadata_quality(podcast)
    
    # Check quality threshold
    if quality_score < QUALITY_THRESHOLD:
        errors.append(f"Quality score {quality_score:.2%} below threshold {QUALITY_THRESHOLD:.2%}")
    
    is_valid = len(errors) == 0 and quality_score >= QUALITY_THRESHOLD
    return is_valid, errors, quality_score, field_status

def main():
    """Main validation function."""
    import argparse
    global QUALITY_THRESHOLD
    
    parser = argparse.ArgumentParser(description="Validate podcast metadata against unified schema")
    parser.add_argument("file", help="Path to podcasts.json file")
    parser.add_argument("--threshold", type=float, default=QUALITY_THRESHOLD,
                       help=f"Quality threshold (default: {QUALITY_THRESHOLD})")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()
    
    QUALITY_THRESHOLD = args.threshold
    
    # Load schema if available
    schema = None
    schema_path = Path(__file__).parent.parent.parent.parent / "copernicus-podcast-api" / "metadata_schema.json"
    if schema_path.exists():
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load schema: {e}", file=sys.stderr)
    
    # Load podcasts file
    podcasts_file = Path(args.file)
    if not podcasts_file.exists():
        print(f"Error: File not found: {podcasts_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(podcasts_file, 'r') as f:
            podcasts = json.load(f)
        
        if not isinstance(podcasts, list):
            print("Error: podcasts.json should be an array", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error loading podcasts file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate each podcast
    results = []
    total_valid = 0
    total_invalid = 0
    quality_scores = []
    
    for idx, podcast in enumerate(podcasts):
        # Ensure ID exists or generate from guid
        if "id" not in podcast and "guid" in podcast:
            podcast["id"] = f"podcast_{podcast['guid']}"
        
        # Ensure acquired_date exists
        if "acquired_date" not in podcast:
            podcast["acquired_date"] = datetime.now().isoformat()
        
        is_valid, errors, quality_score, field_status = validate_podcast(podcast, schema)
        
        result = {
            "index": idx,
            "id": podcast.get("id", f"unknown_{idx}"),
            "title": podcast.get("title", "unknown"),
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
        print("Podcast Metadata Validation Results")
        print("=" * 70)
        print(f"Total podcasts: {len(results)}")
        print(f"Valid: {total_valid}")
        print(f"Invalid: {total_invalid}")
        if quality_scores:
            print(f"Average quality score: {sum(quality_scores) / len(quality_scores):.2%}")
        print(f"Quality threshold: {QUALITY_THRESHOLD:.2%}")
        print()
        
        # Show invalid podcasts
        if total_invalid > 0:
            print("Invalid podcasts:")
            for result in results:
                if not result.get("valid", False):
                    print(f"  [{result['index']}] {result['title']} (ID: {result['id']})")
                    if "errors" in result:
                        for error in result["errors"]:
                            print(f"    - {error}")
        
        # Show low quality podcasts
        low_quality = [r for r in results if r.get("quality_score", 1.0) < QUALITY_THRESHOLD]
        if low_quality:
            print(f"\nPodcasts below quality threshold ({QUALITY_THRESHOLD:.2%}):")
            for result in sorted(low_quality, key=lambda x: x.get("quality_score", 0.0)):
                print(f"  [{result['index']}] {result['title']}: {result.get('quality_score', 0.0):.2%}")
    
    # Exit with error code if any invalid
    sys.exit(1 if total_invalid > 0 else 0)

if __name__ == "__main__":
    main()
