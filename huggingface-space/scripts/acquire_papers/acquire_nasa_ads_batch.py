#!/usr/bin/env python3
"""
NASA ADS Batch Paper Acquisition Script

Acquires research papers from NASA Astrophysics Data System (ADS) using their API.
Target: 5,000 papers
Focus: Astronomy, astrophysics, planetary science
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

# Try to import Google Secrets Manager
try:
    from google.cloud import secretmanager
    SECRETS_MANAGER_AVAILABLE = True
except ImportError:
    SECRETS_MANAGER_AVAILABLE = False

# Configuration
BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
OUTPUT_DIR = BASE_DIR / "metadata-database" / "papers" / "physics"
NASA_ADS_API_URL = "https://api.adsabs.harvard.edu/v1/search/query"
MAX_RESULTS_PER_QUERY = 2000  # NASA ADS API limit
RESULTS_PER_ITERATION = 100  # Default batch size
DELAY_BETWEEN_QUERIES = 1.0  # Seconds (be respectful)

def get_nasa_ads_api_token():
    """
    Get NASA ADS API token from Google Secrets Manager or environment variable.
    NASA ADS API requires authentication (free token from https://ui.adsabs.harvard.edu/user/settings/token)
    """
    if SECRETS_MANAGER_AVAILABLE:
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = "regal-scholar-453620-r7"
            secret_id = "NASA_ADS_API_TOKEN"
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            token = response.payload.data.decode("UTF-8")
            return token.strip()
        except Exception as e:
            print(f"⚠️  Could not access secret from Secrets Manager: {e}")
            print("   Falling back to environment variable...")
    
    # Fallback to environment variable
    token = os.getenv('NASA_ADS_API_TOKEN')
    if token:
        return token
    
    return None

def search_nasa_ads(query: str, max_results: int, start: int = 0, 
                    sort: str = "date desc") -> Optional[Dict]:
    """
    Search NASA ADS and return response data.
    
    Args:
        query: NASA ADS search query (e.g., "year:2020-2025")
        max_results: Maximum number of results
        start: Starting index for pagination
        sort: Sort order (date desc, citations desc, etc.)
    
    Returns:
        Dictionary with search results or None if error
    """
    token = get_nasa_ads_api_token()
    if not token:
        print("❌ NASA ADS API token required. Set NASA_ADS_API_TOKEN environment variable")
        print("   or create Google Secret. Get free token from:")
        print("   https://ui.adsabs.harvard.edu/user/settings/token")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "q": query,
        "start": start,
        "rows": min(max_results, RESULTS_PER_ITERATION),
        "sort": sort,
        "fl": "bibcode,title,author,year,pubdate,abstract,doi,keyword,citation_count,"
              "bibstem,pub,pubnote,page,identifier"
    }
    
    try:
        print(f"  Searching NASA ADS: {query[:80]}...")
        print(f"    Start: {start}, Rows: {params['rows']}")
        
        if REQUESTS_AVAILABLE:
            response = requests.get(NASA_ADS_API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        else:
            import urllib.request
            import urllib.parse
            url = f"{NASA_ADS_API_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
        
        num_found = data.get("response", {}).get("numFound", 0)
        docs = data.get("response", {}).get("docs", [])
        
        print(f"  Found {num_found} total papers, fetching {len(docs)} entries")
        
        return {
            "docs": docs,
            "num_found": num_found
        }
        
    except Exception as e:
        print(f"  ❌ Error searching NASA ADS: {e}")
        return None

def parse_nasa_ads_doc(doc: Dict) -> Optional[Dict]:
    """
    Parse a NASA ADS document into our standardized paper format.
    
    Args:
        doc: NASA ADS document dictionary
    
    Returns:
        Dictionary with paper metadata or None if parsing fails
    """
    try:
        # Get bibcode (unique identifier)
        bibcode = doc.get("bibcode", "")
        if not bibcode:
            return None
        
        # Get title
        title = doc.get("title", [""])[0] if doc.get("title") else ""
        if not title:
            return None
        
        # Get authors
        authors = doc.get("author", [])
        author_string = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
        
        # Get abstract
        abstract = doc.get("abstract", "")
        
        # Get year
        year = str(doc.get("year", ""))
        
        # Get publication date
        pubdate = doc.get("pubdate", "")
        
        # Get DOI
        doi = doc.get("doi", [None])[0] if doc.get("doi") else None
        
        # Get journal/publication
        bibstem = doc.get("bibstem", [""])[0] if doc.get("bibstem") else ""
        pub = doc.get("pub", "")
        journal = pub or bibstem or "Unknown"
        
        # Get keywords
        keywords = doc.get("keyword", []) if doc.get("keyword") else []
        
        # Get citation count
        citation_count = doc.get("citation_count", [0])[0] if doc.get("citation_count") else 0
        
        # Get identifiers (arXiv, etc.)
        identifiers = doc.get("identifier", []) if doc.get("identifier") else []
        arxiv_id = None
        for identifier in identifiers:
            if identifier.startswith("arXiv:"):
                arxiv_id = identifier.replace("arXiv:", "")
                break
        
        # Get publication note
        pubnote = doc.get("pubnote", "")
        
        # Get page numbers
        page = doc.get("page", "")
        
        # Build paper dictionary
        paper = {
            "id": f"nasa_ads_{bibcode}",
            "bibcode": bibcode,
            "title": title,
            "authors": authors,
            "author_string": author_string,
            "journal": journal,
            "journal_full": pub,
            "bibstem": bibstem,
            "pubnote": pubnote,
            "page": page,
            "year": year,
            "pubdate": pubdate,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "abstract": abstract,
            "keywords": keywords,
            "citation_count": citation_count,
            "url": f"https://ui.adsabs.harvard.edu/abs/{bibcode}",
            "pdf_url": f"https://ui.adsabs.harvard.edu/pdf/{bibcode}" if bibcode else None,
            "source": "nasa_ads",
            "acquired_date": datetime.now().isoformat(),
            "category": "physics",
            "subcategories": ["astronomy", "astrophysics"]
        }
        
        # Add planetary science if indicated
        title_lower = title.lower()
        if any(term in title_lower for term in ["planet", "exoplanet", "solar system", "asteroid", "comet"]):
            paper["subcategories"].append("planetary_science")
        
        return paper
        
    except Exception as e:
        print(f"    ⚠️  Error parsing document: {e}")
        return None

def fetch_nasa_ads_papers(query: str, max_results: int, sort: str = "date desc") -> List[Dict]:
    """
    Fetch papers from NASA ADS with pagination.
    
    Args:
        query: NASA ADS search query
        max_results: Maximum number of results
        sort: Sort order
    
    Returns:
        List of paper dictionaries
    """
    all_papers = []
    start = 0
    
    while len(all_papers) < max_results:
        remaining = max_results - len(all_papers)
        batch_size = min(remaining, RESULTS_PER_ITERATION)
        
        result = search_nasa_ads(query, batch_size, start, sort)
        
        if result is None:
            break
        
        # Parse documents
        for doc in result["docs"]:
            paper = parse_nasa_ads_doc(doc)
            if paper:
                all_papers.append(paper)
        
        # Check if we've got all results
        if len(result["docs"]) < batch_size or len(all_papers) >= max_results:
            break
        
        start += len(result["docs"])
        
        # Rate limiting
        if len(all_papers) < max_results:
            time.sleep(DELAY_BETWEEN_QUERIES)
    
    return all_papers[:max_results]

def save_papers(papers: List[Dict], output_dir: Path):
    """Save papers to JSON files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create astronomy/astrophysics subdirectories
    astronomy_dir = output_dir / "astronomy_astrophysics"
    planetary_dir = output_dir / "planetary_science"
    
    astronomy_dir.mkdir(parents=True, exist_ok=True)
    planetary_dir.mkdir(parents=True, exist_ok=True)
    
    for paper in papers:
        if not paper.get("bibcode"):
            continue
        
        # Determine subdirectory
        if "planetary_science" in paper.get("subcategories", []):
            save_dir = planetary_dir
        else:
            save_dir = astronomy_dir
        
        filename = f"nasa_ads_{paper['bibcode'].replace(':', '_')}.json"
        filepath = save_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(paper, f, indent=2, ensure_ascii=False)

def acquire_nasa_ads_papers(target_count: int = 5000):
    """Acquire papers from NASA ADS."""
    print("\n" + "=" * 60)
    print("Acquiring NASA ADS Papers")
    print("=" * 60)
    
    # Queries for different astronomy subfields
    queries = [
        ("year:2020-2025 AND (astronomy OR astrophysics)", 2000),
        ("year:2010-2019 AND citations>10 AND (astronomy OR astrophysics)", 1500),
        ("year:1950-2009 AND citations>50 AND (astronomy OR astrophysics)", 1000),
        ("planetary AND (exoplanet OR \"solar system\" OR asteroid)", 500),
    ]
    
    all_papers = []
    total_acquired = 0
    
    for query, count in queries:
        if total_acquired >= target_count:
            break
        
        remaining = target_count - total_acquired
        query_target = min(count, remaining)
        
        print(f"\nQuery: {query}")
        papers = fetch_nasa_ads_papers(query, query_target, sort="date desc")
        
        all_papers.extend(papers)
        total_acquired += len(papers)
        print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")
        
        time.sleep(DELAY_BETWEEN_QUERIES)
    
    # Save all papers
    print(f"\n💾 Saving {len(all_papers)} NASA ADS papers...")
    save_papers(all_papers, OUTPUT_DIR / "nasa_ads")
    
    return len(all_papers)

def main():
    """Main function to run NASA ADS paper acquisition."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Acquire papers from NASA ADS")
    parser.add_argument("--count", type=int, default=5000, help="Number of papers to acquire")
    parser.add_argument("--test", action="store_true", help="Test mode: acquire only 10 papers")
    args = parser.parse_args()
    
    print("=" * 60)
    print("NASA ADS Batch Paper Acquisition")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check for API token
    token = get_nasa_ads_api_token()
    if not token:
        print("\n❌ NASA ADS API token required!")
        print("   Get a free token from: https://ui.adsabs.harvard.edu/user/settings/token")
        print("   Then set environment variable: export NASA_ADS_API_TOKEN='your-token'")
        print("   Or create Google Secret: NASA_ADS_API_TOKEN")
        sys.exit(1)
    
    print(f"✅ Using NASA ADS API token")
    
    if args.test:
        print("\n🧪 TEST MODE: Acquiring 10 papers...")
        papers = fetch_nasa_ads_papers("year:2020-2025 AND astronomy", 10)
        save_papers(papers, OUTPUT_DIR / "nasa_ads_test")
        print(f"\n✅ Test complete: Acquired {len(papers)} papers")
        return
    
    # Acquire papers
    count = acquire_nasa_ads_papers(args.count)
    
    # Summary
    print("\n" + "=" * 60)
    print("Acquisition Complete")
    print("=" * 60)
    print(f"Total papers acquired: {count:,}")
    print(f"\nPapers saved to: {OUTPUT_DIR / 'nasa_ads'}")
    print("=" * 60)

if __name__ == "__main__":
    main()
