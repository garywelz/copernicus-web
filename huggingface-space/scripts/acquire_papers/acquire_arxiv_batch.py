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
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import sys
import urllib.error
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


def _empty_save_stats() -> Dict[str, int]:
    return {
        "fetched": 0,
        "saved": 0,
        "new_files": 0,
        "updated_files": 0,
        "errors": 0,
        "queries_attempted": 0,
        "queries_failed": 0,
    }


def _merge_save_stats(dest: Dict[str, int], src: Dict[str, int]) -> None:
    for key, value in src.items():
        dest[key] = dest.get(key, 0) + int(value)


def _print_save_summary(stats: Dict[str, int]) -> None:
    print(
        f"  📊 Save summary: fetched={stats.get('fetched', 0)}  "
        f"new_json={stats.get('new_files', 0)}  "
        f"updated_json={stats.get('updated_files', 0)}  "
        f"errors={stats.get('errors', 0)}"
    )


def format_scout_stats(stats: Dict[str, int]) -> str:
    """Same keys as PubMed/bioRxiv, plus errors= for arXiv query failures."""
    return (
        f"SCOUT_STATS fetched={stats.get('fetched', 0)} "
        f"new_json={stats.get('new_files', 0)} "
        f"updated_json={stats.get('updated_files', 0)} "
        f"errors={stats.get('errors', 0)}"
    )


def classify_arxiv_exception(exc: BaseException) -> str:
    """Map an exception to a stable error kind for per-query accounting."""
    if isinstance(exc, ET.ParseError):
        return "parse"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if REQUESTS_AVAILABLE and isinstance(exc, requests.Timeout):
        return "timeout"
    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or (reason and "timed out" in str(reason).lower()):
            return "timeout"
        if "timed out" in str(exc).lower():
            return "timeout"
    status = None
    if REQUESTS_AVAILABLE and isinstance(exc, requests.HTTPError):
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
    elif isinstance(exc, urllib.error.HTTPError):
        status = getattr(exc, "code", None)
    if status == 429:
        return "http_429"
    if isinstance(status, int) and status >= 500:
        return "http_5xx"
    if isinstance(status, int) and status >= 400:
        return f"http_{status}"
    text = str(exc).lower()
    if "timed out" in text or "timeout" in text:
        return "timeout"
    if "parse" in text or "not well-formed" in text:
        return "parse"
    return "other"


def search_arxiv(query: str, max_results: int, sort_by: str = "submittedDate",
                 sort_order: str = "descending", start: int = 0) -> Dict:
    """
    Search arXiv and return response data.

    Returns a dict with ok=True and entries/total/namespace on success, or
    ok=False with error/error_kind on HTTP (429/5xx), timeout, or parse failure.
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

        # NOTE: arXiv returns Atom feeds with both opensearch and arxiv namespaces.
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
            'arxiv': 'http://arxiv.org/schemas/atom',
        }

        total_results_elem = root.find('.//opensearch:totalResults', ns)
        if total_results_elem is not None and total_results_elem.text:
            total_results = int(total_results_elem.text)
        else:
            total_results = len(root.findall('atom:entry', ns))

        entries = root.findall('atom:entry', ns)

        print(f"  Found {total_results} total papers, fetching {len(entries)} entries")

        return {
            "ok": True,
            "entries": entries,
            "total": total_results,
            "namespace": ns,
        }

    except Exception as e:
        kind = classify_arxiv_exception(e)
        print(f"  ❌ Error searching arXiv ({kind}): {e}")
        return {
            "ok": False,
            "entries": [],
            "total": 0,
            "namespace": None,
            "error": str(e),
            "error_kind": kind,
        }

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
        category = determine_discipline(primary_category or (categories[0] if categories else ""))
        
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
            "discipline": category,
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
                       sort_order: str = "descending") -> Tuple[List[Dict], Optional[Dict]]:
    """
    Fetch papers from arXiv with pagination.

    Returns:
        (papers, error_info). error_info is set when the query gets no successful
        page (HTTP 429/5xx, timeout, or feed parse error). A successful empty
        feed is ( [], None).
    """
    all_papers = []
    start = 0
    saw_success = False
    first_error: Optional[Dict] = None

    while len(all_papers) < max_results:
        remaining = max_results - len(all_papers)
        batch_size = min(remaining, RESULTS_PER_ITERATION)

        result = search_arxiv(query, batch_size, sort_by, sort_order, start)

        if not result.get("ok"):
            if first_error is None:
                first_error = {
                    "error": result.get("error", "unknown"),
                    "error_kind": result.get("error_kind", "other"),
                }
            # No successful page yet → whole query failed.
            if not saw_success:
                break
            # Later page failed after some papers: keep what we have, log, stop.
            print(
                f"  ⚠️  Stopping pagination after partial results "
                f"({first_error.get('error_kind')}: {first_error.get('error')})"
            )
            break

        saw_success = True
        for entry in result["entries"]:
            paper = parse_arxiv_entry(entry, result["namespace"])
            if paper:
                all_papers.append(paper)

        if len(result["entries"]) < batch_size or len(all_papers) >= max_results:
            break

        start += len(result["entries"])

        if len(all_papers) < max_results:
            time.sleep(DELAY_BETWEEN_QUERIES)

    if not saw_success:
        return [], first_error or {"error": "search failed", "error_kind": "other"}
    return all_papers[:max_results], None

def save_papers(papers: List[Dict], output_dir: Path, batch_name: str = "arxiv") -> Dict[str, int]:
    """Save papers to JSON files. Returns fetched/new/updated counts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = _empty_save_stats()
    stats["fetched"] = len(papers)

    by_discipline: Dict[str, List[Dict]] = {}
    for paper in papers:
        discipline = paper.get("category", "interdisciplinary")
        by_discipline.setdefault(discipline, []).append(paper)

    for discipline, discipline_papers in by_discipline.items():
        discipline_dir = output_dir / discipline
        discipline_dir.mkdir(parents=True, exist_ok=True)

        for paper in discipline_papers:
            if not paper.get("arxiv_id"):
                continue

            filename = f"{batch_name}_{paper['arxiv_id']}.json"
            filepath = discipline_dir / filename

            if filepath.exists():
                stats["updated_files"] += 1
            else:
                stats["new_files"] += 1
            stats["saved"] += 1

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper, f, indent=2, ensure_ascii=False)

    return stats

def load_config_queries(config_path: Optional[str]) -> Optional[List[Dict]]:
    if not config_path:
        return None
    path = Path(config_path)
    if not path.exists():
        print(f"  ⚠️  Config queries file not found: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else None


def build_arxiv_query(categories: List[str], days_back: int = 14, keyword_filter: Optional[str] = None) -> str:
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    end = date.today()
    start = end - timedelta(days=days_back)
    date_filter = f"submittedDate:[{start.strftime('%Y%m%d')}* TO {end.strftime('%Y%m%d')}*]"
    base = f"({cat_query})"
    if keyword_filter:
        kw_terms = [t.strip() for t in keyword_filter.replace(" OR ", "|").split("|") if t.strip()]
        kw_query = " OR ".join(f"all:{term}" for term in kw_terms)
        base = f"{base} AND ({kw_query})"
    return f"{base} AND {date_filter}"


def acquire_recent_papers(
    target_count: int = 5000, config_queries_path: Optional[str] = None
) -> Tuple[int, Dict[str, int]]:
    """Acquire recent q-bio / ML-for-biology papers only — no math/CS overflow."""
    print("\n" + "=" * 60)
    print("Acquiring Recent arXiv Papers (biology-focused)")
    print("=" * 60)

    config_queries = load_config_queries(config_queries_path)
    if config_queries:
        print(f"  Using {len(config_queries)} queries from config file")
        query_plan = []
        for qdef in config_queries:
            share = float(qdef.get("share", 0.25))
            count = max(1, int(target_count * share))
            query = build_arxiv_query(
                qdef.get("categories", ["q-bio.GN"]),
                int(qdef.get("days_back", 14)),
                qdef.get("keyword_filter"),
            )
            query_plan.append((query, qdef.get("name", "config query"), count))
    else:
        q_bio_target = max(1, int(target_count * 0.60))
        cs_target = max(1, int(target_count * 0.20))
        bio_physics_target = max(1, target_count - q_bio_target - cs_target)
        query_plan = [
            (build_arxiv_query(["q-bio.GN", "q-bio.MN", "q-bio.CB", "q-bio.BM"], 14), "q-bio core", q_bio_target),
            (build_arxiv_query(["cs.LG", "cs.NE"], 7, "biology OR genomics OR gene OR regulatory"), "ML for biology", cs_target),
            (build_arxiv_query(["q-bio.QM", "q-bio.PE", "q-bio.NC"], 14), "q-bio extended", bio_physics_target),
        ]

    all_papers = []
    seen_ids = set()
    total_acquired = 0
    stats = _empty_save_stats()
    failed_queries: List[str] = []

    for query, name, count in query_plan:
        if total_acquired >= target_count:
            break

        remaining = target_count - total_acquired
        query_target = min(count, remaining)

        print(f"\nQuery ({name}): {query[:100]}...")
        stats["queries_attempted"] += 1
        papers, error_info = fetch_arxiv_papers(
            query, query_target, sort_by="submittedDate", sort_order="descending"
        )

        if error_info is not None:
            stats["queries_failed"] += 1
            stats["errors"] += 1
            kind = error_info.get("error_kind", "other")
            msg = error_info.get("error", "")
            failed_queries.append(f"{name} ({kind}): {msg}")
            print(f"  ❌ Query failed ({kind}): {msg}")
            print(f"  ✅ Acquired 0 papers (unique total: {total_acquired}/{target_count})")
            time.sleep(DELAY_BETWEEN_QUERIES)
            continue

        for paper in papers:
            arxiv_id = paper.get("arxiv_id") or paper.get("id")
            if arxiv_id in seen_ids:
                continue
            seen_ids.add(arxiv_id)
            paper["category"] = "biology"
            paper["discipline"] = "biology"
            all_papers.append(paper)

        total_acquired = len(all_papers)
        print(f"  ✅ Acquired {len(papers)} papers (unique total: {total_acquired}/{target_count})")

        time.sleep(DELAY_BETWEEN_QUERIES)

    if failed_queries:
        print("\n⚠️  Query failures this run:")
        for line in failed_queries:
            print(f"   - {line}")

    if total_acquired < target_count:
        print(f"  ℹ️  Stopped at {total_acquired}/{target_count} — no math/CS overflow categories used.")

    print(f"\n💾 Saving {len(all_papers)} recent papers...")
    save_stats = save_papers(all_papers, OUTPUT_DIR / "arxiv_recent", batch_name="arxiv_recent")
    stats["fetched"] = save_stats["fetched"]
    stats["saved"] = save_stats["saved"]
    stats["new_files"] = save_stats["new_files"]
    stats["updated_files"] = save_stats["updated_files"]
    _print_save_summary(stats)

    return len(all_papers), stats

def acquire_classic_papers(target_count: int = 5000) -> Tuple[int, Dict[str, int]]:
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
    stats = _empty_save_stats()
    failed_queries: List[str] = []

    for query, category, count in queries:
        if total_acquired >= target_count:
            break

        remaining = target_count - total_acquired
        query_target = min(count, remaining)

        print(f"\nQuery: {query}")
        stats["queries_attempted"] += 1
        papers, error_info = fetch_arxiv_papers(
            query, query_target, sort_by="relevance", sort_order="descending"
        )

        if error_info is not None:
            stats["queries_failed"] += 1
            stats["errors"] += 1
            kind = error_info.get("error_kind", "other")
            msg = error_info.get("error", "")
            failed_queries.append(f"{category} ({kind}): {msg}")
            print(f"  ❌ Query failed ({kind}): {msg}")
            print(f"  ✅ Acquired 0 papers (Total: {total_acquired}/{target_count})")
            time.sleep(DELAY_BETWEEN_QUERIES)
            continue

        all_papers.extend(papers)
        total_acquired += len(papers)
        print(f"  ✅ Acquired {len(papers)} papers (Total: {total_acquired}/{target_count})")

        time.sleep(DELAY_BETWEEN_QUERIES)

    if failed_queries:
        print("\n⚠️  Query failures this run:")
        for line in failed_queries:
            print(f"   - {line}")

    print(f"\n💾 Saving {len(all_papers)} classic papers...")
    save_stats = save_papers(all_papers, OUTPUT_DIR / "arxiv_classic", batch_name="arxiv_classic")
    stats["fetched"] = save_stats["fetched"]
    stats["saved"] = save_stats["saved"]
    stats["new_files"] = save_stats["new_files"]
    stats["updated_files"] = save_stats["updated_files"]
    _print_save_summary(stats)

    return len(all_papers), stats


def all_queries_failed(stats: Dict[str, int]) -> bool:
    """True when every attempted query failed (exit non-zero)."""
    attempted = int(stats.get("queries_attempted", 0))
    failed = int(stats.get("queries_failed", 0))
    return attempted > 0 and failed == attempted


def main() -> int:
    """Main function to run arXiv paper acquisition. Exit 1 if every query failed."""
    import argparse

    parser = argparse.ArgumentParser(description="Acquire papers from arXiv")
    parser.add_argument("--recent", type=int, default=5000, help="Number of recent biology-focused papers")
    parser.add_argument("--classic", type=int, default=5000, help="Number of classic papers (pre-2023)")
    parser.add_argument("--config-queries", type=str, default=None, help="JSON file with arxiv_queries list")
    parser.add_argument("--test", action="store_true", help="Test mode: acquire only 10 papers")
    args = parser.parse_args()

    print("=" * 60)
    print("arXiv Batch Paper Acquisition")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.test:
        print("\n🧪 TEST MODE: Acquiring 10 papers...")
        stats = _empty_save_stats()
        stats["queries_attempted"] = 1
        papers, error_info = fetch_arxiv_papers(
            "cat:q-bio.GN", 10, sort_by="submittedDate", sort_order="descending"
        )
        if error_info is not None:
            stats["queries_failed"] = 1
            stats["errors"] = 1
            print(f"  ❌ Query failed ({error_info.get('error_kind')}): {error_info.get('error')}")
        save_stats = save_papers(papers, OUTPUT_DIR / "arxiv_test", batch_name="arxiv_test")
        _merge_save_stats(stats, {
            "fetched": save_stats["fetched"],
            "saved": save_stats["saved"],
            "new_files": save_stats["new_files"],
            "updated_files": save_stats["updated_files"],
        })
        print(f"\n✅ Test complete: Acquired {len(papers)} papers")
        print(format_scout_stats(stats))
        return 1 if all_queries_failed(stats) else 0

    total_stats = _empty_save_stats()

    recent_count, recent_stats = acquire_recent_papers(args.recent, args.config_queries)
    _merge_save_stats(total_stats, recent_stats)

    classic_count = 0
    if args.classic > 0:
        classic_count, classic_stats = acquire_classic_papers(args.classic)
        _merge_save_stats(total_stats, classic_stats)

    print("\n" + "=" * 60)
    print("Acquisition Complete")
    print("=" * 60)
    print(f"Recent papers (biology-focused): {recent_count:,}")
    if args.classic > 0:
        print(f"Classic papers (pre-2023): {classic_count:,}")
    print(f"Total papers acquired: {recent_count + classic_count:,}")
    _print_save_summary(total_stats)
    print(f"\nPapers saved to: {OUTPUT_DIR}")
    print("=" * 60)
    print(format_scout_stats(total_stats))

    if all_queries_failed(total_stats):
        print(
            f"ERROR: all {total_stats['queries_attempted']} arXiv queries failed "
            f"({total_stats['errors']} errors); exiting non-zero"
        )
        return 1
    if total_stats.get("errors", 0) > 0:
        print(
            f"WARNING: {total_stats['queries_failed']}/{total_stats['queries_attempted']} "
            f"queries failed; continuing with partial results"
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
