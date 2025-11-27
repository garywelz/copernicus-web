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
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")  # YouTube Data API
        
        # API endpoints
        self.endpoints = {
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
            "arxiv": "http://export.arxiv.org/api/query",
            "nasa_ads": "https://api.adsabs.harvard.edu/v1/search/query",
            "zenodo": "https://zenodo.org/api/records",
            "bioRxiv": "https://api.biorxiv.org/details",
            "core": "https://api.core.ac.uk/v3/search",
            "news_api": "https://newsapi.org/v2/everything",
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "youtube": "https://www.googleapis.com/youtube/v3/search"
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
        
        # YouTube search for academic content (conference talks, lectures)
        if self.youtube_api_key:
            search_tasks.append(self._search_youtube(base_query, depth))
        
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
        """Search arXiv for preprint papers - PUBLIC API, no authentication required"""
        sources = []
        max_results = {"basic": 5, "comprehensive": 15, "exhaustive": 25}
        
        try:
            # ArXiv is PUBLIC - search directly without OpenRouter
            # Map query to ArXiv categories for better results
            category_filter = self._map_to_arxiv_category(query)
            
            # Build search query - try category-specific first, then general
            if category_filter:
                search_query = f"cat:{category_filter}+AND+({query})"
            else:
                # General search across all fields
                search_query = f"all:{query}"
            
            arxiv_params = {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results.get(depth, 15),
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.endpoints["arxiv"], params=arxiv_params) as response:
                    if response.status == 200:
                        xml_data = await response.text()
                        sources = self._parse_arxiv_xml(xml_data)
                        print(f"✅ ArXiv search found {len(sources)} sources for: {query}")
                    else:
                        print(f"⚠️ ArXiv API returned status {response.status}")
        
        except Exception as e:
            print(f"arXiv search error: {e}")
            # Try simpler search if category search failed
            try:
                simple_params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results.get(depth, 15),
                    "sortBy": "relevance"
                }
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.endpoints["arxiv"], params=simple_params) as response:
                        if response.status == 200:
                            xml_data = await response.text()
                            sources = self._parse_arxiv_xml(xml_data)
                            print(f"✅ ArXiv fallback search found {len(sources)} sources")
            except Exception as e2:
                print(f"ArXiv fallback search also failed: {e2}")
        
        return sources
    
    def _map_to_arxiv_category(self, query: str) -> str:
        """Map search query to ArXiv category for better results"""
        query_lower = query.lower()
        
        # Mathematics categories
        if "number theory" in query_lower or "diophantine" in query_lower or "arithmetic" in query_lower:
            return "math.NT"  # Number Theory
        elif "algebra" in query_lower:
            return "math.AC"  # Commutative Algebra
        elif "geometry" in query_lower:
            return "math.DG"  # Differential Geometry
        elif "topology" in query_lower:
            return "math.GT"  # Geometric Topology
        elif "analysis" in query_lower:
            return "math.AP"  # Analysis of PDEs
        elif "probability" in query_lower or "statistics" in query_lower:
            return "math.PR"  # Probability
        elif "combinatorics" in query_lower:
            return "math.CO"  # Combinatorics
        elif "logic" in query_lower:
            return "math.LO"  # Logic
        
        # Physics categories
        elif "quantum" in query_lower:
            return "quant-ph"  # Quantum Physics
        elif "particle" in query_lower or "hep" in query_lower:
            return "hep-th"  # High Energy Physics - Theory
        
        # General math if math-related but no specific category
        if any(term in query_lower for term in ["math", "theorem", "proof", "conjecture"]):
            return "math"  # General mathematics
        
        return ""  # No category filter - search all

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
        """Search CORE aggregator for open access research papers - UK's largest aggregator"""
        sources = []
        
        if not self.core_api_key:
            print(f"⚠️ CORE API key not available - skipping CORE search")
            return sources
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.core_api_key}",
                    "Content-Type": "application/json"
                }
                
                max_results = {"basic": 10, "comprehensive": 20, "exhaustive": 30}
                
                # Optimize query for CORE - detect subject area
                subject_filter = self._detect_subject_for_core(query)
                
                params = {
                    "q": query,
                    "limit": max_results.get(depth, 20),
                    "page": 1
                }
                
                # CORE supports subject filtering - add if detected
                if subject_filter:
                    params["subject"] = subject_filter
                
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
                        
                        print(f"✅ CORE search found {len(sources)} sources for: {query}")
                        if subject_filter:
                            print(f"   Subject filter: {subject_filter}")
                    else:
                        print(f"⚠️ CORE API returned status {response.status}")
        
        except Exception as e:
            print(f"CORE API search error: {e}")
        
        return sources
    
    def _detect_subject_for_core(self, query: str) -> str:
        """Detect subject area from query for CORE filtering"""
        query_lower = query.lower()
        
        # Mathematics
        if any(term in query_lower for term in ["number theory", "math", "mathematics", "algebra", "geometry", 
                                                  "topology", "analysis", "arithmetic", "diophantine", "theorem"]):
            return "Mathematics"
        
        # Physics
        if any(term in query_lower for term in ["physics", "quantum", "particle", "astrophysics", "cosmology"]):
            return "Physics"
        
        # Biology
        if any(term in query_lower for term in ["biology", "genetic", "molecular", "cell", "biochemistry", "neuroscience"]):
            return "Biology"
        
        # Computer Science
        if any(term in query_lower for term in ["computer science", "algorithm", "computing", "software", "programming"]):
            return "Computer Science"
        
        # Chemistry
        if any(term in query_lower for term in ["chemistry", "chemical", "molecular", "organic"]):
            return "Chemistry"
        
        return ""  # No subject filter - search all

    async def _search_youtube(self, query: str, depth: str) -> List[ResearchSource]:
        """Search YouTube for academic content - conference talks, lectures, educational videos"""
        sources = []
        
        if not self.youtube_api_key:
            return sources
        
        try:
            max_results = {"basic": 5, "comprehensive": 10, "exhaustive": 15}
            
            async with aiohttp.ClientSession() as session:
                # Search for educational/academic content
                params = {
                    "part": "snippet",
                    "q": f"{query} lecture OR conference OR academic OR research",
                    "type": "video",
                    "videoCategoryId": "27",  # Education category
                    "order": "relevance",
                    "maxResults": max_results.get(depth, 10),
                    "key": self.youtube_api_key
                }
                
                async with session.get(self.endpoints["youtube"], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for item in data.get("items", []):
                            snippet = item.get("snippet", {})
                            video_id = item.get("id", {}).get("videoId", "")
                            
                            # Extract channel name as "author"
                            channel_title = snippet.get("channelTitle", "YouTube")
                            
                            source = ResearchSource(
                                title=snippet.get("title", ""),
                                authors=[channel_title],
                                abstract=snippet.get("description", "")[:500],
                                url=f"https://www.youtube.com/watch?v={video_id}",
                                publication_date=snippet.get("publishedAt", ""),
                                source="youtube",
                                keywords=snippet.get("tags", [])[:5] if snippet.get("tags") else None
                            )
                            sources.append(source)
                        
                        print(f"✅ YouTube search found {len(sources)} sources for: {query}")
                    else:
                        print(f"⚠️ YouTube API returned status {response.status}")
        
        except Exception as e:
            print(f"YouTube API search error: {e}")
        
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
