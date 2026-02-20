#!/usr/bin/env python3
"""
Crossref Batch Paper Acquisition Script

Acquires research papers using Crossref API for DOI-based acquisition.
Target: Flexible (can be used for specific journals or DOI lists)
Focus: Multi-publisher coverage, journal-based searches
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

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
CROSSREF_API_URL = "https://api.crossref.org/works"
MAX_RESULTS_PER_QUERY = 1000  # Crossref API limit
RESULTS_PER_ITERATION = 100  # Default batch size
DELAY_BETWEEN_QUERIES = 1.0  # Seconds (be respectful, Crossref recommends 1 second)

def search_crossref(query: Optional[str] = None, filter_params: Optional[Dict] = None,
                    max_results: int = 100, offset: int = 0, sort: str = "relevance",
                    order: str = "desc") -> Optional[Dict]:
    """
    Search Crossref and return response data.
    
    Args:
        query: Crossref search query (optional)
        filter_params: Dictionary of filter parameters (e.g., {"issn": "1234-5678", "from-pub-date": "2020"})
        max_results: Maximum number of results
        offset: Starting index for pagination
        sort: Sort field (relevance, score, updated, deposited, indexed, published)
        order: Sort order (asc or desc)
    
    Returns:
        Dictionary with search results or None if error
    """
    params = {
        "rows": min(max_results, RESULTS_PER_ITERATION),
        "offset": offset,
        # Crossref expects sort and order as separate parameters.
        # See: https://api.crossref.org/swagger-ui/index.html
        "sort": sort,
        "order": order,
        "mailto": "gary@copernicusai.fyi"  # Polite use (required by Crossref)
    }
    
    if query:
        params["query.title"] = query  # Use title query for better results
        # Also try general query as fallback
        # params["query"] = query
    
    # Add filter parameters
    if filter_params:
        filters = []
        for key, value in filter_params.items():
            filters.append(f"{key}:{value}")
        if filters:
            params["filter"] = ",".join(filters)
    
    try:
        query_desc = query or str(filter_params) if filter_params else "all"
        print(f"  Searching Crossref: {query_desc[:80]}...")
        print(f"    Offset: {offset}, Rows: {params['rows']}")
        
        if REQUESTS_AVAILABLE:
            response = requests.get(CROSSREF_API_URL, params=params, timeout=30, 
                                  headers={"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"})
            response.raise_for_status()
            data = response.json()
        else:
            import urllib.request
            import urllib.parse
            url = f"{CROSSREF_API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
        
        total_results = data.get("message", {}).get("total-results", 0)
        items = data.get("message", {}).get("items", [])
        
        print(f"  Found {total_results} total papers, fetching {len(items)} entries")
        
        return {
            "items": items,
            "total_results": total_results
        }
        
    except Exception as e:
        print(f"  ❌ Error searching Crossref: {e}")
        return None

def parse_crossref_item(item: Dict) -> Optional[Dict]:
    """
    Parse a Crossref item into our standardized paper format.
    
    Args:
        item: Crossref item dictionary
    
    Returns:
        Dictionary with paper metadata or None if parsing fails
    """
    try:
        # Get DOI (required)
        doi = item.get("DOI", "")
        if not doi:
            return None
        
        # Get title
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            return None
        
        # Get authors
        authors = []
        author_list = item.get("author", [])
        for author in author_list:
            given = author.get("given", "")
            family = author.get("family", "")
            if family:
                if given:
                    authors.append(f"{family}, {given}")
                else:
                    authors.append(family)
            elif author.get("name"):  # Organization name
                authors.append(author["name"])
        
        author_string = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
        
        # Get abstract
        abstract_list = item.get("abstract", [])
        abstract = ""
        if abstract_list:
            # Crossref abstracts are often in HTML, try to extract plain text
            import re
            abstract_html = abstract_list[0] if isinstance(abstract_list, list) else abstract_list
            if isinstance(abstract_html, str):
                # Remove HTML tags
                abstract = re.sub('<[^<]+?>', '', abstract_html).strip()
        
        # Get publication date
        published = item.get("published-print", {}) or item.get("published-online", {}) or item.get("created", {})
        date_parts = published.get("date-parts", [[None]])[0] if published else [None]
        year = str(date_parts[0]) if date_parts[0] else ""
        
        # Get journal/container
        container = item.get("container-title", [])
        journal = container[0] if container else ""
        
        # Get ISSNs
        issn = item.get("ISSN", [""])[0] if item.get("ISSN") else None
        issn_type = item.get("issn-type", [{}])[0] if item.get("issn-type") else {}
        
        # Get volume, issue, page
        volume = item.get("volume", "")
        issue = item.get("issue", "")
        page = item.get("page", "")
        
        # Get article type
        article_type = item.get("type", "")
        
        # Get citation count
        citation_count = item.get("is-referenced-by-count", 0)
        
        # Get subjects/categories
        subjects = item.get("subject", [])
        
        # Get publisher
        publisher = item.get("publisher", "")
        
        # Get language
        language = item.get("language", "")
        
        # Get keywords
        keywords = []
        keyword_groups = item.get("keyword", [])
        if keyword_groups:
            for kw_group in keyword_groups:
                if isinstance(kw_group, list):
                    keywords.extend([str(kw) for kw in kw_group])
                elif isinstance(kw_group, str):
                    keywords.append(kw_group)
        
        # Determine discipline from subjects or journal
        category = determine_discipline(subjects, journal, article_type)
        
        # Get URL
        url = item.get("URL", f"https://doi.org/{doi}")
        
        # Build paper dictionary
        paper = {
            "id": f"crossref_{doi.replace('/', '_')}",
            "doi": doi,
            "title": title,
            "authors": authors,
            "author_string": author_string,
            "journal": journal,
            "issn": issn,
            "issn_type": issn_type.get("type", "") if isinstance(issn_type, dict) else "",
            "volume": volume,
            "issue": issue,
            "page": page,
            "year": year,
            "publisher": publisher,
            "language": language,
            "abstract": abstract,
            "subjects": subjects,
            "keywords": keywords,
            "article_type": article_type,
            "citation_count": citation_count,
            "url": url,
            "source": "crossref",
            "acquired_date": datetime.now().isoformat(),
            "category": category,
            "subcategories": subjects[:3] if subjects else []
        }
        
        return paper
        
    except Exception as e:
        print(f"    ⚠️  Error parsing item: {e}")
        return None

def determine_discipline(subjects: List[str], journal: str, article_type: str) -> str:
    """Determine discipline from Crossref subjects, journal name, or article type."""
    all_text = " ".join([s.lower() for s in subjects] + [journal.lower()] + [article_type.lower()])
    
    if any(term in all_text for term in ["biology", "biochemistry", "genetics", "molecular biology", "cell biology", "ecology"]):
        return "biology"
    elif any(term in all_text for term in ["chemistry", "chemical", "organic", "inorganic", "physical chemistry"]):
        return "chemistry"
    elif any(term in all_text for term in ["physics", "astrophysics", "astronomy", "quantum", "condensed matter"]):
        return "physics"
    elif any(term in all_text for term in ["mathematics", "math", "statistics", "probability", "algebra", "geometry"]):
        return "mathematics"
    elif any(term in all_text for term in ["computer science", "computing", "software", "algorithm", "artificial intelligence"]):
        return "computer_science"
    else:
        return "interdisciplinary"

def fetch_crossref_papers(query: Optional[str] = None, filter_params: Optional[Dict] = None,
                          max_results: int = 100, sort: str = "relevance", order: str = "desc") -> List[Dict]:
    """
    Fetch papers from Crossref with pagination.
    
    Args:
        query: Crossref search query (optional)
        filter_params: Dictionary of filter parameters
        max_results: Maximum number of results
        sort: Sort field
        order: Sort order
    
    Returns:
        List of paper dictionaries
    """
    all_papers = []
    offset = 0
    
    while len(all_papers) < max_results:
        remaining = max_results - len(all_papers)
        batch_size = min(remaining, RESULTS_PER_ITERATION)
        
        result = search_crossref(query, filter_params, batch_size, offset, sort, order)
        
        if result is None:
            break
        
        # Parse items
        for item in result["items"]:
            paper = parse_crossref_item(item)
            if paper:
                all_papers.append(paper)
        
        # Check if we've got all results
        if len(result["items"]) < batch_size or len(all_papers) >= max_results or offset >= result["total_results"]:
            break
        
        offset += len(result["items"])
        
        # Rate limiting
        if len(all_papers) < max_results:
            time.sleep(DELAY_BETWEEN_QUERIES)
    
    return all_papers[:max_results]

def save_papers(papers: List[Dict], output_dir: Path, batch_name: str = "crossref"):
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
            if not paper.get("doi"):
                continue
            
            # Clean DOI for filename
            doi_clean = paper["doi"].replace("/", "_").replace(":", "_")
            filename = f"{batch_name}_{doi_clean}.json"
            filepath = discipline_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)

def acquire_by_journal(journal_issn: str, target_count: int = 1000, year_start: Optional[int] = None,
                       year_end: Optional[int] = None):
    """Acquire papers from a specific journal by ISSN."""
    print(f"\nAcquiring papers from journal with ISSN: {journal_issn}")
    
    filter_params = {"issn": journal_issn}
    if year_start:
        filter_params["from-pub-date"] = str(year_start)
    if year_end:
        filter_params["until-pub-date"] = str(year_end)
    
    papers = fetch_crossref_papers(filter_params=filter_params, max_results=target_count,
                                   sort="published", order="desc")
    
    return papers

def acquire_by_query(query: str, target_count: int = 1000):
    """Acquire papers using a general Crossref query."""
    print(f"\nAcquiring papers with query: {query}")
    
    papers = fetch_crossref_papers(query=query, max_results=target_count,
                                   sort="relevance", order="desc")
    
    return papers

def acquire_by_doi_list(doi_list: List[str]) -> List[Dict]:
    """Acquire papers by specific DOI list."""
    print(f"\nAcquiring {len(doi_list)} papers by DOI...")
    
    all_papers = []
    
    for doi in doi_list:
        try:
            # Crossref API for single DOI
            url = f"https://api.crossref.org/works/{doi}"
            
            if REQUESTS_AVAILABLE:
                response = requests.get(url, timeout=30,
                                      headers={"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"})
                if response.status_code == 200:
                    data = response.json()
                    item = data.get("message", {})
                    paper = parse_crossref_item(item)
                    if paper:
                        all_papers.append(paper)
                else:
                    print(f"  ⚠️  DOI not found: {doi}")
            else:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "CopernicusAI/1.0 (mailto:gary@copernicusai.fyi)"})
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read())
                    item = data.get("message", {})
                    paper = parse_crossref_item(item)
                    if paper:
                        all_papers.append(paper)
            
            time.sleep(DELAY_BETWEEN_QUERIES)
            
        except Exception as e:
            print(f"  ⚠️  Error fetching DOI {doi}: {e}")
            continue
    
    return all_papers

def main():
    """Main function to run Crossref paper acquisition."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Acquire papers from Crossref")
    parser.add_argument("--journal-issn", type=str, help="Journal ISSN to search")
    parser.add_argument("--query", type=str, help="General search query")
    parser.add_argument("--doi-file", type=str, help="File containing list of DOIs (one per line)")
    parser.add_argument("--count", type=int, default=1000, help="Number of papers to acquire")
    parser.add_argument("--year-start", type=int, help="Start year filter")
    parser.add_argument("--year-end", type=int, help="End year filter")
    parser.add_argument("--test", action="store_true", help="Test mode: acquire only 10 papers")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Crossref Batch Paper Acquisition")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.test:
        print("\n🧪 TEST MODE: Acquiring 10 papers...")
        papers = fetch_crossref_papers(query="machine learning", max_results=10)
        save_papers(papers, OUTPUT_DIR / "crossref_test", batch_name="crossref_test")
        print(f"\n✅ Test complete: Acquired {len(papers)} papers")
        return
    
    papers = []
    
    if args.doi_file:
        # Acquire by DOI list
        with open(args.doi_file, 'r') as f:
            doi_list = [line.strip() for line in f if line.strip()]
        papers = acquire_by_doi_list(doi_list)
    elif args.journal_issn:
        # Acquire by journal
        papers = acquire_by_journal(args.journal_issn, args.count, args.year_start, args.year_end)
    elif args.query:
        # Acquire by query
        papers = acquire_by_query(args.query, args.count)
    else:
        print("\n❌ Please specify --journal-issn, --query, or --doi-file")
        parser.print_help()
        sys.exit(1)
    
    # Save papers
    if papers:
        print(f"\n💾 Saving {len(papers)} Crossref papers...")
        save_papers(papers, OUTPUT_DIR / "crossref", batch_name="crossref")
    
    # Summary
    print("\n" + "=" * 60)
    print("Acquisition Complete")
    print("=" * 60)
    print(f"Total papers acquired: {len(papers):,}")
    print(f"\nPapers saved to: {OUTPUT_DIR / 'crossref'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
