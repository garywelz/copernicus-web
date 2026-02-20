#!/usr/bin/env python3
"""
PubMed Batch Paper Acquisition Script

Acquires research papers from PubMed/NCBI using Entrez API.
Target: 30,000 papers (15,000 recent 2020-2025, 15,000 classic 1950-2019)
Focus: Biology, medicine, biochemistry
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

# Try to import Biopython for Entrez API
try:
    from Bio import Entrez
    from Bio.Entrez import efetch, esearch, read
    BIOENTREZ_AVAILABLE = True
except ImportError:
    BIOENTREZ_AVAILABLE = False
    print("⚠️  Warning: Bio.Entrez not available. Install with: pip install biopython")

try:
    from google.cloud import secretmanager
    SECRETS_MANAGER_AVAILABLE = True
except ImportError:
    SECRETS_MANAGER_AVAILABLE = False
    print("⚠️  Warning: google.cloud.secretmanager not available.")

# Configuration
BASE_DIR = Path("/home/gdubs/copernicus-web-public/huggingface-space")
OUTPUT_DIR = BASE_DIR / "metadata-database" / "papers" / "biology"
EMAIL = "gary@copernicusai.fyi"  # Required by Entrez API
MAX_RESULTS_PER_QUERY = 10000  # Entrez API limit
BATCH_SIZE = 100  # Number of papers to fetch at once
DELAY_BETWEEN_QUERIES = 0.34  # Seconds (NCBI requires < 3 requests/second)

def get_pubmed_api_key():
    """
    Get PubMed/NCBI API key from Google Secrets Manager or environment variable.
    PubMed API key is optional but recommended for higher rate limits.
    """
    if SECRETS_MANAGER_AVAILABLE:
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = "regal-scholar-453620-r7"
            secret_id = "PUBMED_API_KEY"  # Create this secret if needed
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            api_key = response.payload.data.decode("UTF-8")
            return api_key.strip()
        except Exception as e:
            # API key is optional, so just log and continue
            pass
    
    # Fallback to environment variable
    api_key = os.getenv('PUBMED_API_KEY')
    if api_key:
        return api_key
    
    return None

def setup_entrez():
    """Configure Entrez API with email and optional API key."""
    Entrez.email = EMAIL
    api_key = get_pubmed_api_key()
    if api_key:
        Entrez.api_key = api_key
        print(f"✅ Using PubMed API key (rate limit: 10 requests/second)")
    else:
        print(f"⚠️  No PubMed API key found (rate limit: 3 requests/second)")
        print(f"   Set PUBMED_API_KEY environment variable or create Google Secret for higher limits")

def search_pubmed(query: str, max_results: int, mindate: Optional[str] = None, 
                  maxdate: Optional[str] = None, sort: str = "relevance") -> List[str]:
    """
    Search PubMed and return list of PMIDs.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results
        mindate: Minimum publication date (YYYY/MM/DD)
        maxdate: Maximum publication date (YYYY/MM/DD)
        sort: Sort order (relevance, pub_date, etc.)
    
    Returns:
        List of PubMed IDs (PMIDs)
    """
    if not BIOENTREZ_AVAILABLE:
        print("❌ Bio.Entrez not available. Cannot search PubMed.")
        return []
    
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, MAX_RESULTS_PER_QUERY),
        "sort": sort,
        "usehistory": "y"
    }
    
    if mindate:
        search_params["mindate"] = mindate
    if maxdate:
        search_params["maxdate"] = maxdate
    
    try:
        print(f"  Searching PubMed: {query[:80]}...")
        handle = Entrez.esearch(**search_params)
        record = Entrez.read(handle)
        handle.close()
        
        count = int(record["Count"])
        pmids = record["IdList"]
        
        print(f"  Found {count} papers, fetching {len(pmids)} PMIDs")
        
        # If we need more results, use history for pagination
        if count > len(pmids):
            webenv = record["WebEnv"]
            query_key = record["QueryKey"]
            
            # Fetch additional batches
            additional_pmids = []
            for start in range(len(pmids), min(count, max_results), MAX_RESULTS_PER_QUERY):
                time.sleep(DELAY_BETWEEN_QUERIES)
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retstart=start,
                    retmax=MAX_RESULTS_PER_QUERY,
                    webenv=webenv,
                    query_key=query_key,
                    sort=sort
                )
                batch_record = Entrez.read(handle)
                handle.close()
                additional_pmids.extend(batch_record["IdList"])
            
            pmids.extend(additional_pmids[:max_results - len(pmids)])
        
        return pmids[:max_results]
        
    except Exception as e:
        print(f"  ❌ Error searching PubMed: {e}")
        return []

def fetch_pubmed_details(pmids: List[str]) -> List[Dict]:
    """
    Fetch detailed information for a list of PubMed IDs.
    
    Args:
        pmids: List of PubMed IDs
    
    Returns:
        List of paper dictionaries with metadata
    """
    if not BIOENTREZ_AVAILABLE:
        return []
    
    if not pmids:
        return []
    
    papers = []
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(pmids), BATCH_SIZE):
        batch_pmids = pmids[i:i+BATCH_SIZE]
        
        try:
            print(f"  Fetching batch {i//BATCH_SIZE + 1} ({len(batch_pmids)} papers)...")
            
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(batch_pmids),
                rettype="abstract",
                retmode="xml"
            )
            
            records = Entrez.read(handle)
            handle.close()
            
            # Parse records
            for record in records["PubmedArticle"]:
                paper = parse_pubmed_record(record)
                if paper:
                    papers.append(paper)
            
            # Rate limiting
            if i + BATCH_SIZE < len(pmids):
                time.sleep(DELAY_BETWEEN_QUERIES)
                
        except Exception as e:
            print(f"  ⚠️  Error fetching batch: {e}")
            continue
    
    return papers

def parse_pubmed_record(record: Dict) -> Optional[Dict]:
    """
    Parse a PubMed record into our standardized paper format.
    
    Args:
        record: PubMed Entrez record
    
    Returns:
        Dictionary with paper metadata or None if parsing fails
    """
    try:
        medline = record.get("MedlineCitation", {})
        article = medline.get("Article", {})
        pubmed_data = record.get("PubmedData", {})
        
        # Get title
        title = article.get("ArticleTitle", "").strip()
        if not title:
            return None
        
        # Get authors
        author_list = article.get("AuthorList", [])
        authors = []
        for author in author_list:
            if author.get("LastName") and author.get("ForeName"):
                authors.append(f"{author['LastName']}, {author['ForeName']}")
            elif author.get("LastName"):
                authors.append(author["LastName"])
            elif author.get("CollectiveName"):
                authors.append(author["CollectiveName"])
        
        # Get journal
        journal = article.get("Journal", {})
        journal_title = journal.get("Title", "")
        journal_iso = journal.get("ISOAbbreviation", "")
        
        # Get publication date
        pub_date = article.get("PubDate", {})
        year = pub_date.get("Year", "")
        if not year and pub_date.get("MedlineDate"):
            # Try to extract year from MedlineDate
            year_match = str(pub_date["MedlineDate"])[:4]
            if year_match.isdigit():
                year = year_match
        
        # Get abstract
        abstract = ""
        abstract_list = article.get("Abstract", {}).get("AbstractText", [])
        if isinstance(abstract_list, list):
            abstract = " ".join([str(ab) for ab in abstract_list])
        elif isinstance(abstract_list, str):
            abstract = abstract_list
        
        # Get PMID
        pmid = str(medline.get("PMID", ""))
        
        # Get DOI
        doi = None
        article_ids = pubmed_data.get("ArticleIdList", [])
        for article_id in article_ids:
            if article_id.attributes.get("IdType") == "doi":
                doi = str(article_id)
                break
        
        # Get citation count (if available in record)
        citation_count = None
        
        # Get keywords
        keywords = []
        keyword_list = medline.get("KeywordList", [])
        for kw_set in keyword_list:
            if isinstance(kw_set, list):
                keywords.extend([str(kw) for kw in kw_set])
        
        # Build paper dictionary
        # Schema conforms to metadata_schema.json (NSF Objective 2: Unified Metadata Representation)
        paper = {
            "id": f"pubmed_{pmid}",
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "author_string": ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else ""),
            "journal": journal_iso or journal_title,
            "journal_full": journal_title,
            "year": year,
            "doi": doi,
            "abstract": abstract,
            "keywords": keywords,
            "citation_count": citation_count,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
            "source": "pubmed",
            "acquired_date": datetime.now().isoformat(),
            "category": "biology",
            "subcategories": []
        }
        
        return paper
        
    except Exception as e:
        print(f"    ⚠️  Error parsing record: {e}")
        return None

def save_papers(papers: List[Dict], output_dir: Path, batch_num: int = 0):
    """Save papers to JSON files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save individual papers
    for paper in papers:
        if not paper.get("pmid"):
            continue
        
        filename = f"pubmed_{paper['pmid']}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(paper, f, indent=2, ensure_ascii=False)
    
    # Save batch summary
    if batch_num > 0:
        batch_file = output_dir / f"batch_{batch_num:04d}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump({
                "batch_number": batch_num,
                "papers_count": len(papers),
                "pmids": [p["pmid"] for p in papers if p.get("pmid")],
                "acquired_date": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

def acquire_recent_papers(target_count: int = 15000):
    """Acquire recent papers (2020-2025)."""
    print("\n" + "=" * 60)
    print("Acquiring Recent Papers (2020-2025)")
    print("=" * 60)
    
    # Queries for different biology subfields
    queries = [
        ("molecular biology[MeSH] OR genetics[MeSH]", 2500),
        ("biochemistry[MeSH] OR metabolism[MeSH]", 2500),
        ("cell biology[MeSH] OR developmental biology[MeSH]", 2500),
        ("immunology[MeSH] OR immunology", 2500),
        ("neuroscience[MeSH] OR neurobiology", 2000),
        ("ecology[MeSH] OR evolution[MeSH]", 1500),
        ("microbiology[MeSH] OR bacteriology", 1000),
    ]
    
    all_papers = []
    total_acquired = 0
    
    for query, count in queries:
        if total_acquired >= target_count:
            break
        
        remaining = target_count - total_acquired
        query_target = min(count, remaining)
        
        print(f"\nQuery: {query}")
        pmids = search_pubmed(query, query_target, mindate="2020/01/01", maxdate="2025/12/31")
        
        if pmids:
            papers = fetch_pubmed_details(pmids)
            all_papers.extend(papers)
            total_acquired += len(papers)
            print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")
        
        time.sleep(DELAY_BETWEEN_QUERIES * 2)
    
    # Save all papers
    print(f"\n💾 Saving {len(all_papers)} recent papers...")
    save_papers(all_papers, OUTPUT_DIR / "recent", batch_num=1)
    
    return len(all_papers)

def acquire_classic_papers(target_count: int = 15000):
    """Acquire classic/foundational papers (1950-2019)."""
    print("\n" + "=" * 60)
    print("Acquiring Classic Papers (1950-2019)")
    print("=" * 60)
    
    # Focus on highly cited classic papers
    queries = [
        ("molecular biology[MeSH] AND review[PT]", 2500),
        ("biochemistry[MeSH] AND review[PT]", 2500),
        ("genetics[MeSH] AND review[PT]", 2000),
        ("cell biology[MeSH] AND review[PT]", 2000),
        ("immunology[MeSH] AND review[PT]", 1500),
        ("evolution[MeSH] AND review[PT]", 1500),
        ("ecology[MeSH] AND review[PT]", 1000),
    ]
    
    all_papers = []
    total_acquired = 0
    
    for query, count in queries:
        if total_acquired >= target_count:
            break
        
        remaining = target_count - total_acquired
        query_target = min(count, remaining)
        
        print(f"\nQuery: {query}")
        pmids = search_pubmed(query, query_target, mindate="1950/01/01", maxdate="2019/12/31", sort="pub_date")
        
        if pmids:
            papers = fetch_pubmed_details(pmids)
            all_papers.extend(papers)
            total_acquired += len(papers)
            print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")
        
        time.sleep(DELAY_BETWEEN_QUERIES * 2)
    
    # Save all papers
    print(f"\n💾 Saving {len(all_papers)} classic papers...")
    save_papers(all_papers, OUTPUT_DIR / "classic", batch_num=1)
    
    return len(all_papers)

def main():
    """Main function to run paper acquisition."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Acquire papers from PubMed")
    parser.add_argument("--recent", type=int, default=15000, help="Number of recent papers (2020-2025)")
    parser.add_argument("--classic", type=int, default=15000, help="Number of classic papers (1950-2019)")
    parser.add_argument("--test", action="store_true", help="Test mode: acquire only 10 papers")
    args = parser.parse_args()
    
    print("=" * 60)
    print("PubMed Batch Paper Acquisition")
    print("=" * 60)
    
    if not BIOENTREZ_AVAILABLE:
        print("\n❌ Bio.Entrez not available. Install with:")
        print("   pip install biopython")
        sys.exit(1)
    
    setup_entrez()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.test:
        print("\n🧪 TEST MODE: Acquiring 10 papers...")
        pmids = search_pubmed("molecular biology[MeSH]", 10, mindate="2020/01/01", maxdate="2025/12/31")
        if pmids:
            papers = fetch_pubmed_details(pmids)
            save_papers(papers, OUTPUT_DIR / "test", batch_num=1)
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
    print(f"Recent papers (2020-2025): {recent_count:,}")
    print(f"Classic papers (1950-2019): {classic_count:,}")
    print(f"Total papers acquired: {recent_count + classic_count:,}")
    print(f"\nPapers saved to: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
