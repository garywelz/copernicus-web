import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import re

@dataclass
class ResearchSource:
    title: str
    authors: List[str]
    abstract: str
    url: str
    publication_date: str
    source: str  # "pubmed", "arxiv", "nasa_ads", "zenodo", etc.
    doi: Optional[str] = None
    citations: Optional[int] = None
    keywords: Optional[List[str]] = None
    relevance_score: Optional[float] = None

class ComprehensiveResearchPipeline:
    """
    Comprehensive research pipeline leveraging all available academic APIs
    """
    
    def __init__(self):
        # Load API keys from environment
        self.pubmed_api_key = os.getenv("PUBMED_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.nasa_ads_token = os.getenv("NASA_ADS_TOKEN")
        self.zenodo_api_key = os.getenv("ZENODO_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.core_api_key = os.getenv("CORE_API_KEY")  # CORE aggregator API
        
        # API endpoints
        self.endpoints = {
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            "arxiv": "http://export.arxiv.org/api/query",
            "nasa_ads": "https://api.adsabs.harvard.edu/v1/search/query",
            "zenodo": "https://zenodo.org/api/records",
            "bioRxiv": "https://api.biorxiv.org/details",
            "core": "https://api.core.ac.uk/v3/search",
            "news_api": "https://newsapi.org/v2/everything",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions"
        }
        
        # Source weights for relevance scoring
        self.source_weights = {
            "pubmed": 1.0,
            "arxiv": 0.9,
            "nasa_ads": 0.95,
            "zenodo": 0.8,
            "bioRxiv": 0.85,
            "core": 0.85,
            "news_api": 0.6,
            "google_scholar": 0.85
        }

    async def health_check(self) -> Dict[str, str]:
        """Check health of all research sources"""
        health_status = {}
        
        # Check each API endpoint
        async with aiohttp.ClientSession() as session:
            for source, endpoint in self.endpoints.items():
                try:
                    async with session.get(endpoint, timeout=5) as response:
                        if response.status < 500:
                            health_status[source] = "healthy"
                        else:
                            health_status[source] = "degraded"
                except:
                    health_status[source] = "unavailable"
        
        return health_status

    async def comprehensive_search(
        self,
        subject: str,
        additional_context: str = "",
        source_links: List[str] = None,
        depth: str = "comprehensive",
        include_preprints: bool = True,
        include_social_trends: bool = False
    ) -> List[ResearchSource]:
        """
        Perform comprehensive research across all available sources
        """
        
        # Construct search queries
        base_query = f"{subject} {additional_context}".strip()
        
        # Parallel search across all sources
        search_tasks = []
        
        # Academic sources
        search_tasks.append(self._search_pubmed(base_query, depth))
        
        if include_preprints:
            search_tasks.append(self._search_arxiv(base_query, depth))
            search_tasks.append(self._search_biorxiv(base_query, depth))
        
        # Specialized sources based on subject
        if any(term in subject.lower() for term in ["space", "astronomy", "astrophysics", "cosmology"]):
            search_tasks.append(self._search_nasa_ads(base_query, depth))
        
        search_tasks.append(self._search_zenodo(base_query, depth))
        
        # CORE aggregator for open access papers
        search_tasks.append(self._search_core(base_query, depth))
        
        # Current trends and news
        if include_social_trends:
            search_tasks.append(self._search_news_api(base_query))
        
        # Execute all searches in parallel
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        all_sources = []
        for result in search_results:
            if isinstance(result, list):
                all_sources.extend(result)
            elif isinstance(result, Exception):
                print(f"Search error: {result}")
        
        # Add user-provided source links
        if source_links:
            user_sources = await self._process_user_links(source_links, subject)
            all_sources.extend(user_sources)
        
        # Score and rank results
        ranked_sources = await self._rank_and_score_sources(all_sources, subject)
        
        # Filter by depth setting
        max_results = {"basic": 10, "comprehensive": 25, "exhaustive": 50}
        return ranked_sources[:max_results.get(depth, 25)]

    async def _search_pubmed(self, query: str, depth: str) -> List[ResearchSource]:
        """Search PubMed for biomedical literature"""
        sources = []
        max_results = {"basic": 5, "comprehensive": 15, "exhaustive": 30}
        
        try:
            async with aiohttp.ClientSession() as session:
                # First, search for article IDs
                search_url = f"{self.endpoints['pubmed']}esearch.fcgi"
                search_params = {
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results.get(depth, 15),
                    "retmode": "json",
                    "sort": "relevance"
                }
                
                async with session.get(search_url, params=search_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pmids = data.get("esearchresult", {}).get("idlist", [])
                        
                        if pmids:
                            # Fetch detailed information
                            fetch_url = f"{self.endpoints['pubmed']}efetch.fcgi"
                            fetch_params = {
                                "db": "pubmed",
                                "id": ",".join(pmids),
                                "retmode": "xml"
                            }
                            
                            async with session.get(fetch_url, params=fetch_params) as fetch_response:
                                if fetch_response.status == 200:
                                    xml_data = await fetch_response.text()
                                    sources = self._parse_pubmed_xml(xml_data)
        
        except Exception as e:
            print(f"PubMed search error: {e}")
        
        return sources

    async def _search_arxiv(self, query: str, depth: str) -> List[ResearchSource]:
        """Search arXiv for preprint papers via OpenRouter"""
        sources = []
        max_results = {"basic": 5, "comprehensive": 15, "exhaustive": 25}
        
        try:
            # Use OpenRouter to search arXiv intelligently
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                }
                
                # First, use AI to refine the search query for arXiv
                refine_prompt = f"""
                Convert this research query into optimal arXiv search terms: "{query}"
                
                Return only the refined search terms, focusing on:
                - Key scientific concepts
                - Relevant arXiv categories
                - Technical terminology
                
                Refined query:"""
                
                ai_data = {
                    "model": "anthropic/claude-3-haiku",
                    "messages": [{"role": "user", "content": refine_prompt}],
                    "max_tokens": 100
                }
                
                async with session.post(self.endpoints["openrouter"], 
                                      headers=headers, json=ai_data) as ai_response:
                    if ai_response.status == 200:
                        ai_result = await ai_response.json()
                        refined_query = ai_result["choices"][0]["message"]["content"].strip()
                    else:
                        refined_query = query
                
                # Now search arXiv with refined query
                arxiv_params = {
                    "search_query": f"all:{refined_query}",
                    "start": 0,
                    "max_results": max_results.get(depth, 15),
                    "sortBy": "relevance",
                    "sortOrder": "descending"
                }
                
                async with session.get(self.endpoints["arxiv"], params=arxiv_params) as response:
                    if response.status == 200:
                        xml_data = await response.text()
                        sources = self._parse_arxiv_xml(xml_data)
        
        except Exception as e:
            print(f"arXiv search error: {e}")
        
        return sources

    async def _search_nasa_ads(self, query: str, depth: str) -> List[ResearchSource]:
        """Search NASA ADS for astronomy/astrophysics papers"""
        sources = []
        max_results = {"basic": 5, "comprehensive": 10, "exhaustive": 20}
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.nasa_ads_token}"}
                
                params = {
                    "q": query,
                    "fl": "title,author,abstract,bibcode,doi,pubdate,citation_count",
                    "rows": max_results.get(depth, 10),
                    "sort": "citation_count desc"
                }
                
                async with session.get(self.endpoints["nasa_ads"], 
                                     headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for doc in data.get("response", {}).get("docs", []):
                            source = ResearchSource(
                                title=doc.get("title", [""])[0],
                                authors=doc.get("author", []),
                                abstract=doc.get("abstract", ""),
                                url=f"https://ui.adsabs.harvard.edu/abs/{doc.get('bibcode', '')}",
                                publication_date=doc.get("pubdate", ""),
                                source="nasa_ads",
                                doi=doc.get("doi", [""])[0] if doc.get("doi") else None,
                                citations=doc.get("citation_count", 0)
                            )
                            sources.append(source)
        
        except Exception as e:
            print(f"NASA ADS search error: {e}")
        
        return sources

    async def _search_zenodo(self, query: str, depth: str) -> List[ResearchSource]:
        """Search Zenodo for open research data and publications"""
        sources = []
        max_results = {"basic": 3, "comprehensive": 8, "exhaustive": 15}
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": query,
                    "size": max_results.get(depth, 8),
                    "sort": "mostrecent",
                    "type": "publication"
                }
                
                async with session.get(self.endpoints["zenodo"], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for record in data.get("hits", {}).get("hits", []):
                            metadata = record.get("metadata", {})
                            source = ResearchSource(
                                title=metadata.get("title", ""),
                                authors=[creator.get("name", "") for creator in metadata.get("creators", [])],
                                abstract=metadata.get("description", ""),
                                url=record.get("links", {}).get("self_html", ""),
                                publication_date=metadata.get("publication_date", ""),
                                source="zenodo",
                                doi=metadata.get("doi", "")
                            )
                            sources.append(source)
        
        except Exception as e:
            print(f"Zenodo search error: {e}")
        
        return sources

    async def _search_news_api(self, query: str) -> List[ResearchSource]:
        """Search for recent science news and trends"""
        sources = []
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "q": f"{query} science research",
                    "domains": "nature.com,science.org,cell.com,sciencedaily.com,phys.org",
                    "sortBy": "relevancy",
                    "pageSize": 10,
                    "apiKey": self.news_api_key
                }
                
                async with session.get(self.endpoints["news_api"], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for article in data.get("articles", []):
                            source = ResearchSource(
                                title=article.get("title", ""),
                                authors=[article.get("author", "Science News")],
                                abstract=article.get("description", ""),
                                url=article.get("url", ""),
                                publication_date=article.get("publishedAt", ""),
                                source="news_api"
                            )
                            sources.append(source)
        
        except Exception as e:
            print(f"News API search error: {e}")
        
        return sources

    async def _search_biorxiv(self, query: str, depth: str) -> List[ResearchSource]:
        """Search BioRxiv for biology preprints"""
        sources = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # BioRxiv API doesn't require authentication
                url = f"{self.endpoints['bioRxiv']}/{query}/0/50"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.text()
                        # Parse XML response
                        root = ET.fromstring(data)
                        
                        for record in root.findall('.//record'):
                            title = record.findtext('title', '').strip()
                            authors = [author.text for author in record.findall('.//author')]
                            abstract = record.findtext('abstract', '').strip()
                            doi = record.findtext('.//doi', '')
                            pub_date = record.findtext('.//date', '')
                            
                            source = ResearchSource(
                                title=title,
                                authors=authors if authors else ["Unknown"],
                                abstract=abstract[:500],
                                url=f"https://doi.org/{doi}" if doi else "",
                                publication_date=pub_date,
                                source="bioRxiv",
                                doi=doi
                            )
                            sources.append(source)
        
        except Exception as e:
            print(f"BioRxiv API search error: {e}")
        
        return sources

    async def _search_core(self, query: str, depth: str) -> List[ResearchSource]:
        """Search CORE aggregator for open access research papers"""
        sources = []
        
        if not self.core_api_key:
            return sources
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.core_api_key}",
                    "Content-Type": "application/json"
                }
                
                params = {
                    "q": query,
                    "limit": 20,
                    "page": 1
                }
                
                async with session.get(
                    self.endpoints["core"],
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for paper in data.get("data", []):
                            title = paper.get("title", "").strip()
                            authors = [
                                author.get("name", "")
                                for author in paper.get("authors", [])
                            ]
                            
                            source = ResearchSource(
                                title=title,
                                authors=authors if authors else ["Unknown"],
                                abstract=paper.get("abstract", "")[:500],
                                url=paper.get("downloadUrl") or paper.get("url", ""),
                                publication_date=paper.get("publishedDate", ""),
                                source="core",
                                doi=paper.get("doi"),
                                keywords=paper.get("topics", [])
                            )
                            sources.append(source)
        
        except Exception as e:
            print(f"CORE API search error: {e}")
        
        return sources

    async def _process_user_links(self, links: List[str], subject: str) -> List[ResearchSource]:
        """Process user-provided research links"""
        sources = []
        
        for link in links:
            try:
                # Extract metadata from user links using AI
                async with aiohttp.ClientSession() as session:
                    # Fetch page content
                    async with session.get(link, timeout=10) as response:
                        if response.status == 200:
                            content = await response.text()
                            
                            # Use AI to extract research metadata
                            metadata = await self._extract_metadata_with_ai(content, link, subject)
                            if metadata:
                                sources.append(metadata)
            
            except Exception as e:
                print(f"Error processing user link {link}: {e}")
        
        return sources

    async def _extract_metadata_with_ai(self, content: str, url: str, subject: str) -> Optional[ResearchSource]:
        """Use AI to extract research metadata from web content"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                }
                
                # Truncate content to avoid token limits
                truncated_content = content[:3000]
                
                prompt = f"""
                Extract research metadata from this web content about {subject}:
                
                URL: {url}
                Content: {truncated_content}
                
                Return a JSON object with:
                - title: string
                - authors: array of strings
                - abstract: string (summary of main content)
                - publication_date: string (if available)
                - keywords: array of strings
                
                JSON:"""
                
                ai_data = {
                    "model": "anthropic/claude-3-haiku",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300
                }
                
                async with session.post(self.endpoints["openrouter"], 
                                      headers=headers, json=ai_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        metadata_text = result["choices"][0]["message"]["content"]
                        
                        # Parse JSON response
                        try:
                            metadata = json.loads(metadata_text)
                            return ResearchSource(
                                title=metadata.get("title", ""),
                                authors=metadata.get("authors", []),
                                abstract=metadata.get("abstract", ""),
                                url=url,
                                publication_date=metadata.get("publication_date", ""),
                                source="user_provided",
                                keywords=metadata.get("keywords", [])
                            )
                        except json.JSONDecodeError:
                            pass
        
        except Exception as e:
            print(f"AI metadata extraction error: {e}")
        
        return None

    async def _rank_and_score_sources(self, sources: List[ResearchSource], subject: str) -> List[ResearchSource]:
        """Rank and score research sources by relevance"""
        
        # Calculate relevance scores
        for source in sources:
            score = 0.0
            
            # Base score from source type
            score += self.source_weights.get(source.source, 0.5)
            
            # Title relevance
            if subject.lower() in source.title.lower():
                score += 0.3
            
            # Abstract relevance
            if source.abstract and subject.lower() in source.abstract.lower():
                score += 0.2
            
            # Citation count bonus (if available)
            if source.citations and source.citations > 0:
                score += min(0.2, source.citations / 100)
            
            # Recency bonus
            if source.publication_date:
                try:
                    pub_date = datetime.fromisoformat(source.publication_date.replace('Z', '+00:00'))
                    days_old = (datetime.now() - pub_date).days
                    if days_old < 365:  # Published within last year
                        score += 0.1
                except:
                    pass
            
            source.relevance_score = score
        
        # Sort by relevance score
        return sorted(sources, key=lambda x: x.relevance_score or 0, reverse=True)

    def _parse_pubmed_xml(self, xml_data: str) -> List[ResearchSource]:
        """Parse PubMed XML response"""
        sources = []
        
        try:
            root = ET.fromstring(xml_data)
            for article in root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                abstract_elem = article.find(".//AbstractText")
                authors = article.findall(".//Author")
                
                title = title_elem.text if title_elem is not None else ""
                abstract = abstract_elem.text if abstract_elem is not None else ""
                author_names = []
                
                for author in authors:
                    lastname = author.find("LastName")
                    forename = author.find("ForeName")
                    if lastname is not None and forename is not None:
                        author_names.append(f"{forename.text} {lastname.text}")
                
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                source = ResearchSource(
                    title=title,
                    authors=author_names,
                    abstract=abstract,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    publication_date="",
                    source="pubmed"
                )
                sources.append(source)
        
        except Exception as e:
            print(f"PubMed XML parsing error: {e}")
        
        return sources

    def _parse_arxiv_xml(self, xml_data: str) -> List[ResearchSource]:
        """Parse arXiv XML response"""
        sources = []
        
        try:
            root = ET.fromstring(xml_data)
            namespace = {"atom": "http://www.w3.org/2005/Atom"}
            
            for entry in root.findall("atom:entry", namespace):
                title = entry.find("atom:title", namespace).text.strip()
                summary = entry.find("atom:summary", namespace).text.strip()
                
                authors = []
                for author in entry.findall("atom:author", namespace):
                    name = author.find("atom:name", namespace).text
                    authors.append(name)
                
                link = entry.find("atom:id", namespace).text
                published = entry.find("atom:published", namespace).text
                
                source = ResearchSource(
                    title=title,
                    authors=authors,
                    abstract=summary,
                    url=link,
                    publication_date=published,
                    source="arxiv"
                )
                sources.append(source)
        
        except Exception as e:
            print(f"arXiv XML parsing error: {e}")
        
        return sources

    async def get_available_sources(self) -> List[str]:
        """Get list of available research sources"""
        return list(self.endpoints.keys())

    async def get_source_status(self) -> List[Dict[str, Any]]:
        """Get detailed status of all research sources"""
        health = await self.health_check()
        
        sources = []
        for source, endpoint in self.endpoints.items():
            sources.append({
                "name": source,
                "endpoint": endpoint,
                "status": health.get(source, "unknown"),
                "weight": self.source_weights.get(source, 0.5),
                "description": self._get_source_description(source)
            })
        
        return sources

    def _get_source_description(self, source: str) -> str:
        """Get description of research source"""
        descriptions = {
            "pubmed": "Biomedical and life sciences literature",
            "arxiv": "Preprint repository for physics, mathematics, computer science",
            "nasa_ads": "Astronomy and astrophysics literature",
            "zenodo": "Open research data and publications",
            "news_api": "Recent science news and trends",
            "openrouter": "Multi-LLM AI research assistance"
        }
        return descriptions.get(source, "Research source")
