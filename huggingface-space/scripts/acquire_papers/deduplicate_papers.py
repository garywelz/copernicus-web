#!/usr/bin/env python3
"""
Paper Deduplication Script

Performs cross-database deduplication of papers from multiple sources.
Handles DOI matching, title similarity, and author matching for comprehensive deduplication.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
import sys

try:
    from difflib import SequenceMatcher
    DIFFLIB_AVAILABLE = True
except ImportError:
    DIFFLIB_AVAILABLE = False

# Configuration
BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
PAPERS_DIR = BASE_DIR / "metadata-database" / "papers"
OUTPUT_DIR = BASE_DIR / "metadata-database" / "papers_deduplicated"
TITLE_SIMILARITY_THRESHOLD = 0.85  # 85% similarity for title matching
AUTHOR_OVERLAP_THRESHOLD = 0.5  # 50% author overlap for matching

def load_paper(filepath: Path) -> Optional[Dict]:
    """Load a paper from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error loading {filepath}: {e}")
        return None

def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove punctuation, etc.)."""
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def normalize_doi(doi: str) -> Optional[str]:
    """Normalize DOI for comparison."""
    if not doi:
        return None
    # Remove common prefixes
    doi = doi.strip().lower()
    doi = re.sub(r'^(doi:|https?://(dx\.)?doi\.org/)', '', doi)
    doi = doi.strip()
    return doi if doi else None

def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles (0.0 to 1.0)."""
    if not title1 or not title2:
        return 0.0
    
    norm1 = normalize_text(title1)
    norm2 = normalize_text(title2)
    
    if not norm1 or not norm2:
        return 0.0
    
    if DIFFLIB_AVAILABLE:
        return SequenceMatcher(None, norm1, norm2).ratio()
    else:
        # Simple word overlap calculation
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

def author_overlap(authors1: List[str], authors2: List[str]) -> float:
    """Calculate overlap between two author lists (0.0 to 1.0)."""
    if not authors1 or not authors2:
        return 0.0
    
    # Normalize author names (just last names for matching)
    def extract_last_name(author: str) -> str:
        # Handle "LastName, FirstName" or "FirstName LastName" formats
        if ',' in author:
            return author.split(',')[0].strip().lower()
        else:
            parts = author.split()
            return parts[-1].lower() if parts else ""
    
    lastnames1 = set(extract_last_name(a) for a in authors1 if a)
    lastnames2 = set(extract_last_name(a) for a in authors2 if a)
    
    if not lastnames1 or not lastnames2:
        return 0.0
    
    intersection = len(lastnames1 & lastnames2)
    union = len(lastnames1 | lastnames2)
    return intersection / union if union > 0 else 0.0

def extract_paper_id(paper: Dict) -> str:
    """Extract a unique identifier for a paper."""
    # Try DOI first
    doi = paper.get("doi") or paper.get("DOI")
    if doi:
        normalized = normalize_doi(doi)
        if normalized:
            return f"doi:{normalized}"
    
    # Try arXiv ID
    arxiv_id = paper.get("arxiv_id") or paper.get("arXiv", {}).get("id")
    if arxiv_id:
        return f"arxiv:{arxiv_id.lower()}"
    
    # Try PubMed ID
    pmid = paper.get("pmid") or paper.get("pubmed")
    if pmid:
        return f"pubmed:{pmid}"
    
    # Try NASA ADS bibcode
    bibcode = paper.get("bibcode")
    if bibcode:
        return f"bibcode:{bibcode}"
    
    # Fallback to title hash
    title = paper.get("title", "")
    if title:
        normalized = normalize_text(title)
        return f"title_hash:{hash(normalized)}"
    
    return f"unknown:{hash(str(paper))}"

def are_duplicates(paper1: Dict, paper2: Dict) -> Tuple[bool, str, float]:
    """
    Check if two papers are duplicates.
    Returns: (is_duplicate, reason, confidence)
    """
    # Method 1: Exact DOI match (highest confidence)
    doi1 = normalize_doi(paper1.get("doi") or paper1.get("DOI"))
    doi2 = normalize_doi(paper2.get("doi") or paper2.get("DOI"))
    if doi1 and doi2 and doi1 == doi2:
        return True, "exact_doi_match", 1.0
    
    # Method 2: Exact arXiv ID match
    arxiv1 = (paper1.get("arxiv_id") or "").lower()
    arxiv2 = (paper2.get("arxiv_id") or "").lower()
    if arxiv1 and arxiv2 and arxiv1 == arxiv2:
        return True, "exact_arxiv_match", 0.95
    
    # Method 3: Exact PubMed ID match
    pmid1 = str(paper1.get("pmid") or paper1.get("pubmed") or "")
    pmid2 = str(paper2.get("pmid") or paper2.get("pubmed") or "")
    if pmid1 and pmid2 and pmid1 == pmid2:
        return True, "exact_pmid_match", 0.95
    
    # Method 4: Exact NASA ADS bibcode match
    bibcode1 = paper1.get("bibcode")
    bibcode2 = paper2.get("bibcode")
    if bibcode1 and bibcode2 and bibcode1 == bibcode2:
        return True, "exact_bibcode_match", 0.95
    
    # Method 5: Title similarity + author overlap (lower confidence)
    title1 = paper1.get("title", "")
    title2 = paper2.get("title", "")
    authors1 = paper1.get("authors", [])
    authors2 = paper2.get("authors", [])
    
    if title1 and title2:
        title_sim = title_similarity(title1, title2)
        author_overlap_score = author_overlap(authors1, authors2) if authors1 and authors2 else 0.0
        
        # Both title similarity AND author overlap must be high
        if title_sim >= TITLE_SIMILARITY_THRESHOLD and author_overlap_score >= AUTHOR_OVERLAP_THRESHOLD:
            confidence = (title_sim + author_overlap_score) / 2
            return True, "title_author_match", confidence
    
    return False, "no_match", 0.0

def load_all_papers(source_dirs: List[Path]) -> Dict[str, Dict]:
    """
    Load all papers from source directories.
    Returns: Dictionary mapping paper_id -> paper_dict
    """
    all_papers = {}
    source_map = {}  # Track which source each paper came from
    
    print("Loading papers from source directories...")
    
    for source_dir in source_dirs:
        if not source_dir.exists():
            print(f"  ⚠️  Skipping non-existent directory: {source_dir}")
            continue
        
        print(f"  Scanning: {source_dir}")
        json_files = list(source_dir.rglob("*.json"))
        
        for json_file in json_files:
            paper = load_paper(json_file)
            if not paper:
                continue
            
            paper_id = extract_paper_id(paper)
            
            # If we already have this paper, merge metadata
            if paper_id in all_papers:
                existing = all_papers[paper_id]
                # Merge sources
                existing_sources = existing.get("sources", [])
                new_source = source_dir.name
                if new_source not in existing_sources:
                    existing_sources.append(new_source)
                existing["sources"] = existing_sources
                # Prefer paper with more metadata
                if len(str(paper)) > len(str(existing)):
                    all_papers[paper_id] = paper
                    paper["sources"] = existing_sources
            else:
                paper["sources"] = [source_dir.name]
                all_papers[paper_id] = paper
                source_map[paper_id] = json_file
    
    print(f"  ✅ Loaded {len(all_papers)} unique papers (by primary ID)")
    return all_papers

def find_duplicates(papers: Dict[str, Dict]) -> Dict[str, List[Tuple[str, str, float]]]:
    """
    Find duplicate papers.
    Returns: Dictionary mapping paper_id -> list of (duplicate_id, reason, confidence)
    """
    print("\nFinding duplicates...")
    duplicates = defaultdict(list)
    paper_ids = list(papers.keys())
    checked = 0
    
    for i, paper_id1 in enumerate(paper_ids):
        paper1 = papers[paper_id1]
        
        for j, paper_id2 in enumerate(paper_ids[i+1:], start=i+1):
            is_dup, reason, confidence = are_duplicates(paper1, papers[paper_id2])
            
            if is_dup:
                # Only record if confidence is reasonably high
                if confidence >= 0.8:
                    duplicates[paper_id1].append((paper_id2, reason, confidence))
                    duplicates[paper_id2].append((paper_id1, reason, confidence))
        
        checked += 1
        if checked % 100 == 0:
            print(f"  Checked {checked}/{len(paper_ids)} papers...")
    
    print(f"  ✅ Found {len(duplicates)} papers with potential duplicates")
    return duplicates

def merge_papers(primary: Dict, secondary: Dict) -> Dict:
    """Merge two paper records, keeping the best metadata from each."""
    merged = primary.copy()
    
    # Prefer non-empty fields from secondary
    for key, value in secondary.items():
        if key in ["sources", "id"]:  # Handle these specially
            continue
        
        if not merged.get(key) and value:
            merged[key] = value
        elif isinstance(merged.get(key), list) and isinstance(value, list):
            # Merge lists, removing duplicates
            existing = merged[key]
            merged[key] = list(set(existing + value))
        elif isinstance(merged.get(key), dict) and isinstance(value, dict):
            # Merge dictionaries
            merged[key].update(value)
    
    # Merge sources
    sources = set(merged.get("sources", []) + secondary.get("sources", []))
    merged["sources"] = sorted(list(sources))
    
    # Update metadata
    merged["merged_date"] = datetime.now().isoformat()
    merged["original_ids"] = [primary.get("id"), secondary.get("id")]
    
    return merged

def deduplicate_papers(papers: Dict[str, Dict], duplicates: Dict[str, List[Tuple[str, str, float]]]) -> Dict[str, Dict]:
    """
    Create deduplicated paper set.
    Returns: Dictionary of deduplicated papers
    """
    print("\nCreating deduplicated set...")
    
    deduplicated = {}
    processed = set()
    
    for paper_id, dup_list in duplicates.items():
        if paper_id in processed:
            continue
        
        # Start with primary paper
        primary = papers[paper_id].copy()
        
        # Merge all duplicates
        for dup_id, reason, confidence in dup_list:
            if dup_id in processed:
                continue
            
            if dup_id in papers:
                secondary = papers[dup_id]
                primary = merge_papers(primary, secondary)
                processed.add(dup_id)
        
        # Determine best ID
        best_id = paper_id
        primary["deduplication_confidence"] = max([conf for _, _, conf in dup_list] + [1.0])
        primary["deduplication_method"] = dup_list[0][1] if dup_list else "unique"
        
        deduplicated[best_id] = primary
        processed.add(paper_id)
    
    # Add papers that had no duplicates
    for paper_id, paper in papers.items():
        if paper_id not in processed:
            paper = paper.copy()
            paper["deduplication_method"] = "unique"
            paper["deduplication_confidence"] = 1.0
            deduplicated[paper_id] = paper
    
    print(f"  ✅ Deduplicated to {len(deduplicated)} papers (from {len(papers)})")
    return deduplicated

def save_deduplicated_papers(papers: Dict[str, Dict], output_dir: Path):
    """Save deduplicated papers to output directory, organized by category."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group by category
    by_category = defaultdict(list)
    for paper_id, paper in papers.items():
        category = paper.get("category", "interdisciplinary")
        by_category[category].append((paper_id, paper))
    
    # Save by category
    for category, paper_list in by_category.items():
        category_dir = output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        for paper_id, paper in paper_list:
            # Generate filename
            doi = normalize_doi(paper.get("doi") or "")
            if doi:
                filename = f"{doi.replace('/', '_')}.json"
            elif paper.get("arxiv_id"):
                filename = f"arxiv_{paper['arxiv_id']}.json"
            elif paper.get("pmid"):
                filename = f"pubmed_{paper['pmid']}.json"
            else:
                filename = f"{paper_id.replace(':', '_')}.json"
            
            filepath = category_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(papers)} deduplicated papers to {output_dir}")

def generate_deduplication_report(papers: Dict[str, Dict], duplicates: Dict[str, List[Tuple[str, str, float]]],
                                   original_count: int, output_dir: Path):
    """Generate a deduplication report."""
    report = {
        "deduplication_date": datetime.now().isoformat(),
        "original_count": original_count,
        "deduplicated_count": len(papers),
        "duplicates_found": len(duplicates),
        "papers_removed": original_count - len(papers),
        "deduplication_rate": (original_count - len(papers)) / original_count if original_count > 0 else 0,
        "methods_used": {},
        "summary": {
            "exact_doi_match": 0,
            "exact_arxiv_match": 0,
            "exact_pmid_match": 0,
            "title_author_match": 0,
            "unique": 0
        }
    }
    
    # Count methods
    for paper in papers.values():
        method = paper.get("deduplication_method", "unique")
        report["summary"][method] = report["summary"].get(method, 0) + 1
    
    # Save report
    report_file = output_dir / "deduplication_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("Deduplication Report")
    print("=" * 60)
    print(f"Original papers: {original_count:,}")
    print(f"Deduplicated papers: {len(papers):,}")
    print(f"Duplicates removed: {original_count - len(papers):,}")
    print(f"Deduplication rate: {report['deduplication_rate']:.1%}")
    print("\nMethods used:")
    for method, count in report["summary"].items():
        if count > 0:
            print(f"  {method}: {count:,}")
    print(f"\nReport saved to: {report_file}")

def main():
    """Main function to run paper deduplication."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deduplicate papers from multiple sources")
    parser.add_argument("--sources", nargs="+", help="Source directories to scan (default: all in papers/)")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--test", action="store_true", help="Test mode: process only 100 papers")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Paper Deduplication")
    print("=" * 60)
    
    # Determine source directories
    if args.sources:
        source_dirs = [Path(s) for s in args.sources]
    else:
        # Default: scan all subdirectories in papers/
        source_dirs = [d for d in PAPERS_DIR.iterdir() if d.is_dir() and not d.name.endswith("_deduplicated")]
    
    print(f"\nSource directories: {[str(d) for d in source_dirs]}")
    
    # Load all papers
    all_papers = load_all_papers(source_dirs)
    original_count = len(all_papers)
    
    if args.test:
        # Limit to 100 papers for testing
        test_papers = dict(list(all_papers.items())[:100])
        print(f"\n🧪 TEST MODE: Processing {len(test_papers)} papers")
        all_papers = test_papers
    
    # Find duplicates
    duplicates = find_duplicates(all_papers)
    
    # Deduplicate
    deduplicated = deduplicate_papers(all_papers, duplicates)
    
    # Save deduplicated papers
    output_path = Path(args.output)
    save_deduplicated_papers(deduplicated, output_path)
    
    # Generate report
    generate_deduplication_report(deduplicated, duplicates, original_count, output_path)
    
    print("=" * 60)

if __name__ == "__main__":
    main()
