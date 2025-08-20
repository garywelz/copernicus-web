#!/usr/bin/env python3
"""
Enhanced Research Discovery API Integration for Copernicus AI
Provides comprehensive research paper discovery and analysis capabilities
"""

import asyncio
import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from google.cloud import secretmanager
import re
import urllib.parse
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDiscoveryAPI:
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = "regal-scholar-453620-r7"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Google Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            return None
    
    async def search_arxiv(self, query: str, max_results: int = 10, category: str = None) -> List[Dict]:
        """Search arXiv for research papers"""
        try:
            # Build arXiv query
            search_query = query
            if category:
                # Map subject categories to arXiv categories
                category_map = {
                    'physics': 'cat:physics.*',
                    'biology': 'cat:q-bio.*',
                    'chemistry': 'cat:physics.chem-ph',
                    'mathematics': 'cat:math.*',
                    'computer_science': 'cat:cs.*'
                }
                if category.lower() in category_map:
                    search_query = f"{query} AND {category_map[category.lower()]}"
            
            url = f"http://export.arxiv.org/api/query?search_query={urllib.parse.quote(search_query)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    return self._parse_arxiv_xml(xml_content)
                else:
                    logger.error(f"arXiv API error: HTTP {response.status}")
                    return []
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict]:
        """Parse arXiv XML response"""
        papers = []
        try:
            root = ET.fromstring(xml_content)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
            
            for entry in root.findall('atom:entry', ns):
                paper = {
                    'source': 'arXiv',
                    'title': entry.find('atom:title', ns).text.strip().replace('\n', ' '),
                    'authors': [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)],
                    'abstract': entry.find('atom:summary', ns).text.strip().replace('\n', ' '),
                    'url': entry.find('atom:id', ns).text,
                    'pdf_url': None,
                    'published_date': entry.find('atom:published', ns).text[:10],
                    'categories': [cat.get('term') for cat in entry.findall('atom:category', ns)],
                    'doi': None
                }
                
                # Get PDF URL
                for link in entry.findall('atom:link', ns):
                    if link.get('type') == 'application/pdf':
                        paper['pdf_url'] = link.get('href')
                        break
                
                # Get DOI if available
                doi_elem = entry.find('arxiv:doi', ns)
                if doi_elem is not None:
                    paper['doi'] = doi_elem.text
                
                papers.append(paper)
                
        except Exception as e:
            logger.error(f"arXiv XML parsing error: {e}")
        
        return papers
    
    async def search_pubmed(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search PubMed for biomedical research papers"""
        try:
            # First, search for PMIDs
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={max_results}&sort=date&retmode=json"
            
            async with self.session.get(search_url) as response:
                if response.status == 200:
                    search_data = await response.json()
                    pmids = search_data.get('esearchresult', {}).get('idlist', [])
                    
                    if not pmids:
                        return []
                    
                    # Get detailed information for each PMID
                    pmid_str = ','.join(pmids)
                    detail_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid_str}&retmode=json"
                    
                    async with self.session.get(detail_url) as detail_response:
                        if detail_response.status == 200:
                            detail_data = await detail_response.json()
                            return self._parse_pubmed_json(detail_data)
                        
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
        
        return []
    
    def _parse_pubmed_json(self, data: Dict) -> List[Dict]:
        """Parse PubMed JSON response"""
        papers = []
        try:
            results = data.get('result', {})
            for pmid, paper_data in results.items():
                if pmid == 'uids':
                    continue
                    
                paper = {
                    'source': 'PubMed',
                    'title': paper_data.get('title', ''),
                    'authors': [author.get('name', '') for author in paper_data.get('authors', [])],
                    'abstract': '',  # Need separate call for abstracts
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    'pdf_url': None,
                    'published_date': paper_data.get('pubdate', ''),
                    'journal': paper_data.get('source', ''),
                    'pmid': pmid,
                    'doi': paper_data.get('elocationid', '').replace('doi: ', '') if 'doi:' in paper_data.get('elocationid', '') else None
                }
                papers.append(paper)
                
        except Exception as e:
            logger.error(f"PubMed JSON parsing error: {e}")
        
        return papers
    
    async def search_semantic_scholar(self, query: str, max_results: int = 10, fields: str = None) -> List[Dict]:
        """Search Semantic Scholar for academic papers"""
        try:
            if not fields:
                fields = "paperId,title,authors,abstract,url,venue,year,citationCount,referenceCount,fieldsOfStudy,publicationDate"
            
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(query)}&limit={max_results}&fields={fields}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_semantic_scholar_json(data)
                else:
                    logger.error(f"Semantic Scholar API error: HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
        
        return []
    
    def _parse_semantic_scholar_json(self, data: Dict) -> List[Dict]:
        """Parse Semantic Scholar JSON response"""
        papers = []
        try:
            for paper_data in data.get('data', []):
                paper = {
                    'source': 'Semantic Scholar',
                    'title': paper_data.get('title', ''),
                    'authors': [author.get('name', '') for author in paper_data.get('authors', [])],
                    'abstract': paper_data.get('abstract', ''),
                    'url': paper_data.get('url', ''),
                    'pdf_url': None,
                    'published_date': paper_data.get('publicationDate', ''),
                    'venue': paper_data.get('venue', ''),
                    'year': paper_data.get('year'),
                    'citation_count': paper_data.get('citationCount', 0),
                    'fields_of_study': paper_data.get('fieldsOfStudy', []),
                    'semantic_scholar_id': paper_data.get('paperId')
                }
                papers.append(paper)
                
        except Exception as e:
            logger.error(f"Semantic Scholar JSON parsing error: {e}")
        
        return papers
    
    async def search_nasa_ads(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search NASA ADS for astronomy/astrophysics papers"""
        try:
            token = self.get_secret("nasa-ads-token")
            if not token:
                logger.warning("NASA ADS token not available")
                return []
            
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://api.adsabs.harvard.edu/v1/search/query?q={urllib.parse.quote(query)}&rows={max_results}&sort=date desc"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_nasa_ads_json(data)
                else:
                    logger.error(f"NASA ADS API error: HTTP {response.status}")
                    
        except Exception as e:
            logger.error(f"NASA ADS search error: {e}")
        
        return []
    
    def _parse_nasa_ads_json(self, data: Dict) -> List[Dict]:
        """Parse NASA ADS JSON response"""
        papers = []
        try:
            for paper_data in data.get('response', {}).get('docs', []):
                paper = {
                    'source': 'NASA ADS',
                    'title': paper_data.get('title', [''])[0],
                    'authors': paper_data.get('author', []),
                    'abstract': paper_data.get('abstract', ''),
                    'url': f"https://ui.adsabs.harvard.edu/abs/{paper_data.get('bibcode', '')}/abstract",
                    'pdf_url': None,
                    'published_date': paper_data.get('pubdate', ''),
                    'journal': paper_data.get('pub', ''),
                    'bibcode': paper_data.get('bibcode'),
                    'citation_count': paper_data.get('citation_count', 0)
                }
                papers.append(paper)
                
        except Exception as e:
            logger.error(f"NASA ADS JSON parsing error: {e}")
        
        return papers
    
    def calculate_relevance_score(self, paper: Dict, query_terms: List[str], subject_category: str = None) -> float:
        """Calculate relevance score for a paper based on query and subject"""
        score = 0.0
        
        # Text fields to search
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        
        # Query term matching (weighted)
        for term in query_terms:
            term_lower = term.lower()
            if term_lower in title:
                score += 3.0  # Title matches are highly weighted
            if term_lower in abstract:
                score += 1.0  # Abstract matches
        
        # Recency bonus (papers from last 2 years get bonus)
        try:
            pub_date = paper.get('published_date', '')
            if pub_date:
                pub_year = int(pub_date[:4])
                current_year = datetime.now().year
                if current_year - pub_year <= 2:
                    score += 2.0
        except:
            pass
        
        # Citation count bonus (if available)
        citation_count = paper.get('citation_count', 0)
        if citation_count > 0:
            score += min(citation_count / 10.0, 5.0)  # Cap at 5 points
        
        # Subject category matching
        if subject_category:
            categories = paper.get('categories', []) + paper.get('fields_of_study', [])
            category_text = ' '.join(categories).lower()
            if subject_category.lower() in category_text:
                score += 2.0
        
        return score
    
    async def comprehensive_search(self, query: str, subject_category: str = None, max_results_per_source: int = 5) -> List[Dict]:
        """Perform comprehensive search across all available sources"""
        all_papers = []
        query_terms = query.split()
        
        # Search all sources concurrently
        tasks = [
            self.search_arxiv(query, max_results_per_source, subject_category),
            self.search_pubmed(query, max_results_per_source),
            self.search_semantic_scholar(query, max_results_per_source),
            self.search_nasa_ads(query, max_results_per_source)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        for result in results:
            if isinstance(result, list):
                all_papers.extend(result)
        
        # Calculate relevance scores and sort
        for paper in all_papers:
            paper['relevance_score'] = self.calculate_relevance_score(paper, query_terms, subject_category)
        
        # Sort by relevance score and remove duplicates
        all_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Remove duplicates based on title similarity
        unique_papers = []
        seen_titles = set()
        
        for paper in all_papers:
            title_key = re.sub(r'[^\w\s]', '', paper.get('title', '')).lower().strip()
            if title_key not in seen_titles and len(title_key) > 10:
                seen_titles.add(title_key)
                unique_papers.append(paper)
        
        return unique_papers[:max_results_per_source * 2]  # Return top results

async def main():
    """Test the research discovery API"""
    async with ResearchDiscoveryAPI() as api:
        print("🔬 Testing Research Discovery APIs")
        print("=" * 60)
        
        # Test comprehensive search
        results = await api.comprehensive_search("quantum computing", "physics", 3)
        
        print(f"\n📊 Found {len(results)} unique papers:")
        for i, paper in enumerate(results[:5], 1):
            print(f"\n{i}. {paper['title'][:80]}...")
            print(f"   Source: {paper['source']}")
            print(f"   Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
            print(f"   Relevance Score: {paper['relevance_score']:.2f}")
            if paper.get('published_date'):
                print(f"   Published: {paper['published_date']}")

if __name__ == "__main__":
    asyncio.run(main())
