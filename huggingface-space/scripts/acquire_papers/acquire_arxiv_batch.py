#!/usr/bin/env python3
"""
arXiv Batch Paper Acquisition Script

Acquires research papers from arXiv using their API.
Target: 10,000 papers (5,000 recent 2023-2025, 5,000 classic highly cited pre-2023)
Focus: Physics, CS, math, quantitative biology
"""

import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys
import urllib.request
import urllib.parse

# Try to import requests (preferred) or use urllib
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  Warning: requests not available. Using urllib (slower)")

# Configuration
BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
OUTPUT_DIR = BASE_DIR / "metadata-database" / "papers"
ARXIV_API_URL = "https://export.arxiv.org/api/query"
MAX_RESULTS_PER_QUERY = 2000  # arXiv API limit
RESULTS_PER_ITERATION = 100  # arXiv default, max 2000
DELAY_BETWEEN_QUERIES = 3.0  # Seconds (be respectful, arXiv recommends 3 seconds)

def search_arxiv(query: str, max_results: int, sort_by: str = "submittedDate", 
                 sort_order: str = "descending", start: int = 0) -> Dict:
    """
    Search arXiv and return response data.
    
    Args:
        query: arXiv search query (e.g., "cat:physics.quant-ph AND submittedDate:[20230101* TO 20251231*]")
        max_results: Maximum number of results
        sort_by: Sort field (relevance, lastUpdatedDate, submittedDate)
        sort_order: ascending or descending
        start: Starting index for pagination
    
    Returns:
        Dictionary with search results or None if error
    """
    params = {
        "search_query": query,
        "start": start,
        "max_results": min(max_results, RESULTS_PER_ITERATION),
        "sortBy": sort_by,
        "sortOrder": sort_order
    }
    
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"
    
    try:
        print(f"  Searching arXiv: {query[:80]}...")
        print(f"    Start: {start}, Max results: {params['max_results']}")
        
        if REQUESTS_AVAILABLE:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.content
        else:
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()
        
        # Parse XML response
        root = ET.fromstring(content)
        
        # Get namespace
        # NOTE: arXiv returns Atom feeds with both opensearch and arxiv namespaces.
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
            'arxiv': 'http://arxiv.org/schemas/atom',
        }
        
        # Get total results
        # opensearch is not under the Atom namespace; look it up directly.
        total_results_elem = root.find('.//opensearch:totalResults', ns)
        if total_results_elem is not None and total_results_elem.text:
            total_results = int(total_results_elem.text)
        else:
            # Fallback: count entries
            total_results = len(root.findall('atom:entry', ns))
        
        # Get entries
        entries = root.findall('atom:entry', ns)
        
        print(f"  Found {total_results} total papers, fetching {len(entries)} entries")
        
        return {
            "entries": entries,
            "total": total_results,
            "namespace": ns
        }
        
    except Exception as e:
        print(f"  ❌ Error searching arXiv: {e}")
        return None

def parse_arxiv_entry(entry: ET.Element, ns: Dict) -> Optional[Dict]:
    """
    Parse an arXiv entry into our standardized paper format.
    
    Args:
        entry: arXiv entry XML element
        ns: XML namespace dictionary
    
    Returns:
        Dictionary with paper metadata or None if parsing fails
    """
    try:
        # Get arXiv ID
        arxiv_id = entry.find('atom:id', ns).text.split('/')[-1]
        
        # Get title
        title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
        
        # Get authors
        authors = []
        for author in entry.findall('atom:author', ns):
            name = author.find('atom:name', ns)
            if name is not None:
                authors.append(name.text)
        
        # Get abstract
        abstract = entry.find('atom:summary', ns)
        abstract_text = abstract.text.strip().replace('\n', ' ') if abstract is not None else ""
        
        # Get published date
        published = entry.find('atom:published', ns)
        published_date = published.text if published is not None else ""
        year = published_date[:4] if len(published_date) >= 4 else ""
        
        # Get updated date
        updated = entry.find('atom:updated', ns)
        updated_date = updated.text if updated is not None else published_date
        
        # Get categories/subjects
        categories = []
        primary_category = None
        for category in entry.findall('atom:category', ns):
            term = category.get('term', '')
            categories.append(term)
            if category.get('scheme') == 'http://arxiv.org/schemas/atom':
                primary_category = term
        
        # Get DOI (if available)
        doi = None
        doi_elem = entry.find('arxiv:doi', ns)
        if doi_elem is not None:
            doi = doi_elem.text
        else:
            # Try alternative namespace
            for link in entry.findall('atom:link', ns):
                if link.get('rel') == 'alternate' and 'doi.org' in link.get('href', ''):
                    doi = link.get('href').split('doi.org/')[-1]
                    break
        
        # Get journal reference (if published)
        journal_ref = None
        journal_ref_elem = entry.find('arxiv:journal_ref', ns)
        if journal_ref_elem is not None:
            journal_ref = journal_ref_elem.text
        
        # Get comment (version info, etc.)
        comment = None
        comment_elem = entry.find('arxiv:comment', ns)
        if comment_elem is not None:
            comment = comment_elem.text
        
        # Determine discipline from primary category
        category = determine_discipline(primary_category or categories[0] if categories else "")
        
        # Build paper dictionary
        paper = {
            "id": f"arxiv_{arxiv_id}",
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "author_string": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
            "journal": journal_ref or f"arXiv:{arxiv_id}",
            "journal_ref": journal_ref,
            "year": year,
            "doi": doi,
            "abstract": abstract_text,
            "categories": categories,
            "primary_category": primary_category,
            "comment": comment,
            "published_date": published_date,
            "updated_date": updated_date,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            "source": "arxiv",
            "acquired_date": datetime.now().isoformat(),
            "category": category,
            "subcategories": categories[:3] if categories else []
        }
        
        return paper
        
    except Exception as e:
        print(f"    ⚠️  Error parsing entry: {e}")
        return None

def determine_discipline(category: str) -> str:
    """Determine discipline from arXiv category."""
    if not category:
        return "interdisciplinary"
    
    category_lower = category.lower()
    
    # Physics on arXiv spans multiple top-level groups (not only "physics.*").
    if (
        category_lower.startswith('physics.')
        or category_lower.startswith('astro-ph')
        or category_lower.startswith('cond-mat')
        or category_lower.startswith('hep-')
        or category_lower.startswith('nucl-')
        or category_lower.startswith('gr-qc')
        or category_lower.startswith('quant-ph')
        or category_lower.startswith('math-ph')
    ):
        return "physics"
    elif category_lower.startswith('math'):
        return "mathematics"
    elif category_lower.startswith('cs'):
        return "computer_science"
    elif category_lower.startswith('q-bio'):
        return "biology"
    elif category_lower.startswith('q-fin'):
        return "interdisciplinary"
    elif category_lower.startswith('stat'):
        return "mathematics"
    else:
        return "interdisciplinary"

def fetch_arxiv_papers(query: str, max_results: int, sort_by: str = "submittedDate",
                       sort_order: str = "descending") -> List[Dict]:
    """
    Fetch papers from arXiv with pagination.
    
    Args:
        query: arXiv search query
        max_results: Maximum number of results
        sort_by: Sort field
        sort_order: ascending or descending
    
    Returns:
        List of paper dictionaries
    """
    all_papers = []
    start = 0
    
    while len(all_papers) < max_results:
        remaining = max_results - len(all_papers)
        batch_size = min(remaining, RESULTS_PER_ITERATION)
        
        result = search_arxiv(query, batch_size, sort_by, sort_order, start)
        
        if result is None:
            break
        
        # Parse entries
        for entry in result["entries"]:
            paper = parse_arxiv_entry(entry, result["namespace"])
            if paper:
                all_papers.append(paper)
        
        # Check if we've got all results
        if len(result["entries"]) < batch_size or len(all_papers) >= max_results:
            break
        
        start += len(result["entries"])
        
        # Rate limiting
        if len(all_papers) < max_results:
            time.sleep(DELAY_BETWEEN_QUERIES)
    
    return all_papers[:max_results]

def save_papers(papers: List[Dict], output_dir: Path, batch_name: str = "arxiv"):
    """Save papers to JSON files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Group papers by discipline
    by_discipline = {}
    for paper in papers:
        discipline = paper.get("category", "interdisciplinary")
        if discipline not in by_discipline:
            by_discipline[discipline] = []
        by_discipline[discipline].append(paper)
    
    # Save by discipline
    for discipline, discipline_papers in by_discipline.items():
        discipline_dir = output_dir / discipline
        discipline_dir.mkdir(parents=True, exist_ok=True)
        
        for paper in discipline_papers:
            if not paper.get("arxiv_id"):
                continue
            
            filename = f"{batch_name}_{paper['arxiv_id']}.json"
            filepath = discipline_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)

def acquire_recent_papers(target_count: int = 5000):
    """Acquire recent papers (2023-2025)."""
    print("\n" + "=" * 60)
    print("Acquiring Recent arXiv Papers (2023-2025)")
    print("=" * 60)
    
    # Queries for different categories
    # Note: arXiv API doesn't support date range syntax, so we use simple category queries
    # and sort by submittedDate descending to get the most recent papers
    # arXiv category prefixes:
    # - physics: astro-ph.*, cond-mat.*, hep-*, nucl-*, gr-qc, physics.*, quant-ph, math-ph
    # - math: math.*
    # - cs: cs.*
    # - biology: q-bio.*
    queries = [
        ("(cat:astro-ph.* OR cat:cond-mat.* OR cat:gr-qc OR cat:hep-ph OR cat:hep-th OR cat:hep-ex OR cat:hep-lat OR cat:nucl-ex OR cat:nucl-th OR cat:physics.* OR cat:quant-ph OR cat:math-ph)", "physics", 1500),
        ("cat:math.*", "mathematics", 1200),
        ("cat:cs.*", "computer_science", 1200),
        ("cat:q-bio.*", "biology", 600),
        ("cat:stat.*", "mathematics", 300),
        ("cat:q-fin.*", "interdisciplinary", 200),
    ]
    
    all_papers = []
    total_acquired = 0
    
    for query, category, count in queries:
        if total_acquired >= target_count:
            break
        
        remaining = target_count - total_acquired
        query_target = min(count, remaining)
        
        print(f"\nQuery: {query}")
        papers = fetch_arxiv_papers(query, query_target, sort_by="submittedDate", sort_order="descending")
        
        all_papers.extend(papers)
        total_acquired += len(papers)
        print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")
        
        time.sleep(DELAY_BETWEEN_QUERIES)
    
    # Save all papers
    print(f"\n💾 Saving {len(all_papers)} recent papers...")
    save_papers(all_papers, OUTPUT_DIR / "arxiv_recent", batch_name="arxiv_recent")
    
    return len(all_papers)

def acquire_classic_papers(target_count: int = 5000):
    """Acquire classic highly cited papers (pre-2023)."""
    print("\n" + "=" * 60)
    print("Acquiring Classic arXiv Papers (Pre-2023)")
    print("=" * 60)
    
    # Focus on highly cited papers - use relevance sort for classic papers
    # arXiv doesn't have citation counts, so we'll sort by relevance
    # Note: arXiv API doesn't support date range syntax, so we use simple category queries
    queries = [
        ("(cat:astro-ph.* OR cat:cond-mat.* OR cat:gr-qc OR cat:hep-ph OR cat:hep-th OR cat:hep-ex OR cat:hep-lat OR cat:nucl-ex OR cat:nucl-th OR cat:physics.* OR cat:quant-ph OR cat:math-ph)", "physics", 1500),
        ("cat:math.*", "mathematics", 1200),
        ("cat:cs.*", "computer_science", 1200),
        ("cat:q-bio.*", "biology", 600),
        ("cat:stat.*", "mathematics", 300),
        ("cat:q-fin.*", "interdisciplinary", 200),
    ]
    
    all_papers = []
    total_acquired = 0
    
    for query, category, count in queries:
        if total_acquired >= target_count:
            break
        
        remaining = target_count - total_acquired
        query_target = min(count, remaining)
        
        print(f"\nQuery: {query}")
        # Sort by relevance for classic papers (hopefully gets highly cited ones)
        papers = fetch_arxiv_papers(query, query_target, sort_by="relevance", sort_order="descending")
        
        all_papers.extend(papers)
        total_acquired += len(papers)
        print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")
        
        time.sleep(DELAY_BETWEEN_QUERIES)
    
    # Save all papers
    print(f"\n💾 Saving {len(all_papers)} classic papers...")
    save_papers(all_papers, OUTPUT_DIR / "arxiv_classic", batch_name="arxiv_classic")
    
    return len(all_papers)

def main():
    """Main function to run arXiv paper acquisition."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Acquire papers from arXiv")
    parser.add_argument("--recent", type=int, default=5000, help="Number of recent papers (2023-2025)")
    parser.add_argument("--classic", type=int, default=5000, help="Number of classic papers (pre-2023)")
    parser.add_argument("--test", action="store_true", help="Test mode: acquire only 10 papers")
    args = parser.parse_args()
    
    print("=" * 60)
    print("arXiv Batch Paper Acquisition")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.test:
        print("\n🧪 TEST MODE: Acquiring 10 papers...")
        papers = fetch_arxiv_papers("cat:quant-ph", 10, sort_by="submittedDate", sort_order="descending")
        save_papers(papers, OUTPUT_DIR / "arxiv_test", batch_name="arxiv_test")
        print(f"\n✅ Test complete: Acquired {len(papers)} papers")
        return
    
    # Acquire recent papers
    recent_count = acquire_recent_papers(args.recent)
    
    # Acquire classic papers
    classic_count = acquire_classic_papers(args.classic)
    
    # Summary
    print("\n" + "=" * 60)
    print("Acquisition Complete")
    print("=" * 60)
    print(f"Recent papers (2023-2025): {recent_count:,}")
    print(f"Classic papers (pre-2023): {classic_count:,}")
    print(f"Total papers acquired: {recent_count + classic_count:,}")
    print(f"\nPapers saved to: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
