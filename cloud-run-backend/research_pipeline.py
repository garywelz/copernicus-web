import asyncio
import time
import aiohttp
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
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
    journal: Optional[str] = None  # real venue; never treat pubmed/arxiv as the journal
    keywords: Optional[List[str]] = None
    relevance_score: Optional[float] = None
    pid: Optional[str] = None  # P number, set only on a confirmed paper (gap 3 fix 1)
    # The registry's own record (paper_confirmation shape) when this source was parsed straight from an arXiv or PubMed
    # response, so confirmation can reuse it instead of asking the same registry again. Set only by the two parsers below.
    registry_record: Optional[Dict[str, Any]] = field(default=None, repr=False, compare=False)
    # "datacite" when the paper was found through the OpenAlex fallback (arXiv unreachable): confirmation then uses DataCite's record
    # of the paper's arXiv DOI (10.48550/arXiv.<id>) instead of the arXiv API.
    confirm_via: Optional[str] = field(default=None, repr=False, compare=False)

def _registry_records(xml_data: str, kind: str) -> Dict[str, Dict[str, Any]]:
    """The response parsed the way paper_confirmation parses it, keyed by arXiv id+version or PMID (cached per response)."""
    cache = _registry_records.__dict__.setdefault("_cache", {})
    key = (kind, hash(xml_data))
    if key not in cache:
        from paper_confirmation import parse_arxiv, parse_pubmed
        try:
            cache.clear()
            cache[key] = (parse_arxiv if kind == "arxiv" else parse_pubmed)(xml_data)
        except Exception:
            cache[key] = {}
    return cache[key]


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
        
        from paper_confirmation import RegistryUnavailable
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
            elif isinstance(result, RegistryUnavailable):
                raise result  # arXiv could not be reached: never carry on with only the other sources
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

    # arXiv asks for one request per 3 seconds and answers 429 when a shared address is over its limit. Waits between attempts:
    ARXIV_RETRY_WAITS = (3.0, 6.0, 12.0)
    ARXIV_REQUEST_TIMEOUT_S = 45
    ARXIV_USER_AGENT = "CopernicusAI/1.0 (+https://www.copernicusai.fyi)"

    @staticmethod
    def _arxiv_search_query(query: str, category_filter: str) -> str:
        """The arXiv search_query string. Real spaces (the HTTP client encodes them); a literal '+' would be sent as %2B and
        be part of the query text, which made category searches malformed."""
        query_lower = query.lower()
        if "topological data analysis" in query_lower or " tda " in query_lower or query_lower.strip() == "tda":
            # Phrase search + related terms for TDA (persistent homology, Mapper are core TDA methods)
            return 'all:"Topological Data Analysis" OR all:"persistent homology" OR all:"topological data analysis"'
        if category_filter:
            return f"cat:{category_filter} AND ({query})"
        return f"all:{query}"

    async def _arxiv_request(self, params: Dict[str, Any]):
        """One GET to the arXiv API: (status, body text or '', Retry-After header or None). Network errors propagate."""
        timeout = aiohttp.ClientTimeout(total=self.ARXIV_REQUEST_TIMEOUT_S)
        async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": self.ARXIV_USER_AGENT}) as session:
            async with session.get(self.endpoints["arxiv"], params=params) as response:
                text = await response.text() if response.status == 200 else ""
                return response.status, text, response.headers.get("Retry-After")

    async def _arxiv_get(self, params: Dict[str, Any]) -> str:
        """arXiv search with retries. Returns the XML on a 200. A 429, any other non-200, a timeout or a connection error is
        retried after 3, 6 and 12 seconds (a numeric Retry-After header lengthens the wait, up to 30 s); when every attempt
        fails this raises RegistryUnavailable, so the episode fails with 'try again later' instead of continuing with only
        the other sources. Every attempt is logged as one line: arxiv_search attempt=N status=S retry_after=R elapsed=E."""
        from paper_confirmation import RegistryUnavailable
        attempts = len(self.ARXIV_RETRY_WAITS) + 1
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            status, text, retry_after, error = None, "", None, None
            try:
                status, text, retry_after = await self._arxiv_request(params)
            except Exception as e:  # timeout, DNS, connection reset
                error = type(e).__name__
            print(f"arxiv_search attempt={attempt}/{attempts} status={status if status is not None else error} "
                  f"retry_after={retry_after} elapsed={time.monotonic() - started:.1f}s")
            if status == 200:
                return text
            if attempt < attempts:
                wait = self.ARXIV_RETRY_WAITS[attempt - 1]
                try:
                    wait = min(max(wait, float(retry_after)), 30.0)
                except (TypeError, ValueError):
                    pass
                await asyncio.sleep(wait)
        raise RegistryUnavailable(["arxiv"])

    async def _search_arxiv(self, query: str, depth: str) -> List[ResearchSource]:
        """Search arXiv for preprint papers - PUBLIC API, no authentication required.
        Raises RegistryUnavailable when arXiv cannot be reached (see _arxiv_get); a 200 with no entries is a real 'no results'."""
        max_results = {"basic": 5, "comprehensive": 15, "exhaustive": 25}
        params = {
            "search_query": self._arxiv_search_query(query, self._map_to_arxiv_category(query)),
            "start": 0,
            "max_results": max_results.get(depth, 15),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        from paper_confirmation import RegistryUnavailable
        try:
            xml_data = await self._arxiv_get(params)
        except RegistryUnavailable:
            # arXiv refused or could not be reached on every attempt (Cloud Run's shared address is rate-limited by arXiv):
            # search arXiv-hosted works through OpenAlex instead; confirmation then uses DataCite's record of each arXiv DOI.
            return await self._search_openalex_arxiv(query, depth)
        sources = self._parse_arxiv_xml(xml_data)
        print(f"✅ ArXiv search found {len(sources)} sources for: {query}")
        if self.FOCUSED_QUERIES:
            sources = await self._add_focused_arxiv_results(query, sources)
        return sources

    # Fix 4 (i) / fix 6: the full topic sentence is a poor arXiv query (generic words outrank the one paper that is exactly about the
    # question), so two or three focused queries of 2-3 distinctive terms run beside it. A model proposes them (self.query_llm, set by the
    # integrator); without one, search_queries builds them from the topic words. They go to OpenAlex (arXiv-hosted works, confirmed through
    # DataCite), not to arXiv: from Cloud Run arXiv answers 429 or times out for the second and third request in a row (2026-10-14), which
    # lost the one paper the focused queries exist to find. Results are merged with the sentence results and ordered by how many of the
    # distinctive terms they contain.
    FOCUSED_QUERIES = True
    FOCUSED_MAX_RESULTS = 10
    ARXIV_MAX_AFTER_FOCUS = 20
    query_llm = None
    _ARXIV_ID = re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})", re.I)

    def _arxiv_key(self, source) -> str:
        m = self._ARXIV_ID.search(getattr(source, "url", "") or "")
        return m.group(1) if m else (getattr(source, "url", "") or getattr(source, "title", ""))

    async def _add_focused_arxiv_results(self, topic: str, sentence_sources: List[ResearchSource]) -> List[ResearchSource]:
        from paper_confirmation import RegistryUnavailable
        from search_queries import focused_queries, query_terms, lexical_score, distinctive_terms, keep_focused_paper
        queries = await focused_queries(topic, self.query_llm)
        if not queries:
            return sentence_sources
        distinctive = distinctive_terms(topic)   # a paper only a focused query found must contain one of these (fix 7)
        merged = list(sentence_sources)
        seen = {self._arxiv_key(s) for s in merged}
        for q in queries:
            search = " ".join(query_terms([q]))
            try:
                found = await self._search_openalex_arxiv(search, "comprehensive", per_page=self.FOCUSED_MAX_RESULTS)
            except RegistryUnavailable:
                print(f"focused_search query={search!r} unavailable; skipping the remaining focused queries")
                break  # OpenAlex is refusing or slow: the sentence results stand
            fresh = [s for s in found if self._arxiv_key(s) not in seen]
            seen.update(self._arxiv_key(s) for s in fresh)
            kept = [s for s in fresh if keep_focused_paper(s.title, s.abstract, distinctive)]
            merged.extend(kept)
            print(f"focused_search query={search!r} results={len(found)} new={len(fresh)} kept={len(kept)} "
                  f"dropped_without_a_distinctive_term={[s.title[:40] for s in fresh if s not in kept]}")
        terms = query_terms(queries)
        order = sorted(range(len(merged)), key=lambda i: (-lexical_score(merged[i].title, merged[i].abstract, terms, distinctive), i))
        return [merged[i] for i in order][:self.ARXIV_MAX_AFTER_FOCUS]

    OPENALEX_ARXIV_SOURCE = "S4306400194"  # OpenAlex's id for arXiv as a source of works
    OPENALEX_RETRY_WAITS = (2.0, 4.0)
    # OpenAlex's "polite pool": requests that carry a contact address get faster, steadier service. This is the project's dedicated
    # notification mailbox, never a personal address.
    OPENALEX_MAILTO = "copernicusai.verify@gmail.com"
    OPENALEX_ARXIV_ID = re.compile(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})(?:v\d+)?$", re.I)

    @staticmethod
    def _openalex_abstract(inverted: Optional[Dict[str, List[int]]]) -> str:
        """OpenAlex ships abstracts as {word: [positions]}; put the words back in order."""
        if not inverted:
            return ""
        slots: Dict[int, str] = {}
        for word, positions in inverted.items():
            for pos in positions:
                slots[pos] = word
        return " ".join(slots[i] for i in sorted(slots))

    async def _openalex_request(self, params: Dict[str, Any]):
        """One GET to the OpenAlex works API: (status, parsed JSON or None). Network errors propagate."""
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": self.ARXIV_USER_AGENT}) as session:
            async with session.get("https://api.openalex.org/works", params=params) as response:
                return response.status, (await response.json() if response.status == 200 else None)

    async def _search_openalex_arxiv(self, query: str, depth: str, per_page: Optional[int] = None) -> List[ResearchSource]:
        """arXiv-hosted works from OpenAlex, as ResearchSource objects flagged for DataCite confirmation. Raises
        RegistryUnavailable(["arxiv", "openalex"]) when OpenAlex cannot be reached either: never continue with other sources only."""
        from paper_confirmation import RegistryUnavailable
        per_page = per_page or {"basic": 5, "comprehensive": 15, "exhaustive": 25}.get(depth, 15)
        params = {"search": query, "filter": f"primary_location.source.id:{self.OPENALEX_ARXIV_SOURCE}", "per-page": per_page, "mailto": self.OPENALEX_MAILTO,
                  "select": "id,doi,title,publication_year,authorships,abstract_inverted_index"}
        attempts = len(self.OPENALEX_RETRY_WAITS) + 1
        data = None
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            status, error = None, None
            try:
                status, data = await self._openalex_request(params)
            except Exception as e:
                error = type(e).__name__
            print(f"openalex_search attempt={attempt}/{attempts} status={status if status is not None else error} "
                  f"elapsed={time.monotonic() - started:.1f}s")
            if status == 200:
                break
            if attempt < attempts:
                await asyncio.sleep(self.OPENALEX_RETRY_WAITS[attempt - 1])
        else:
            raise RegistryUnavailable(["arxiv", "openalex"])
        sources: List[ResearchSource] = []
        for w in (data or {}).get("results") or []:
            m = self.OPENALEX_ARXIV_ID.search(w.get("doi") or "")
            title = (w.get("title") or "").strip()
            if not m or not title:
                continue
            arxiv_id = m.group(1)
            sources.append(ResearchSource(
                title=title,
                authors=[a["author"]["display_name"] for a in w.get("authorships") or [] if (a.get("author") or {}).get("display_name")],
                abstract=self._openalex_abstract(w.get("abstract_inverted_index")),
                url=f"https://arxiv.org/abs/{arxiv_id}",
                publication_date=str(w.get("publication_year") or ""),
                source="arxiv",
                doi=f"10.48550/arXiv.{arxiv_id}",
                confirm_via="datacite",
            ))
        print(f"✅ OpenAlex (arXiv fallback) found {len(sources)} sources for: {query}")
        return sources

    def _map_to_arxiv_category(self, query: str) -> str:
        """Map search query to ArXiv category for better results"""
        query_lower = query.lower()
        
        # Topological Data Analysis - must come BEFORE generic "analysis" (math.AP = PDEs is wrong for TDA)
        if "topological data analysis" in query_lower or " tda " in query_lower or query_lower.strip() == "tda":
            return ""  # No category filter - search all for exact phrase match (TDA papers span cs.LG, stat.ML, math.AT)
        
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
        
        # No filter for general mathematics: 'math' is not an arXiv category, so cat:math matches nothing useful
        
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
        """Process user-provided research links.

        Gap 3 fix 1 (C3): a link becomes a source only if an identifier (arXiv id, PubMed id or DOI) can be found
        for it -- in the URL, then in the page's standard metadata -- AND that identifier is confirmed in its
        registry. Title, authors and abstract come from the registry record. No model writes any metadata here.
        Links that cannot be confirmed are dropped (and printed, as other errors in this module are).
        """
        from paper_confirmation import (
            confirm_sources, discover_identifiers_in_page, RegistryUnavailable,
        )
        sources: List[ResearchSource] = []

        for link in links:
            try:
                ids = discover_identifiers_in_page(link, "")
                if not any(ids.values()):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(link, timeout=10) as response:
                            if response.status == 200:
                                ids = discover_identifiers_in_page(link, (await response.text())[:200000])
                if not any(ids.values()):
                    print(f"User link dropped (no identifier found): {link}")
                    continue

                from types import SimpleNamespace
                probe = SimpleNamespace(
                    title="", publication_date="", doi=ids.get("doi"),
                    url=(f"https://arxiv.org/abs/{ids['arxiv']}{ids['arxiv_version'] or ''}" if ids.get("arxiv")
                         else f"https://pubmed.ncbi.nlm.nih.gov/{ids['pmid']}/" if ids.get("pmid") else ""),
                )

                result = await confirm_sources([probe])
                if not result.confirmed:
                    print(f"User link dropped ({result.drop_counts()}): {link}")
                    continue
                c = result.confirmed[0]
                sources.append(ResearchSource(
                    title=c.title, authors=list(c.authors), abstract=c.abstract, url=c.url,
                    publication_date=str(c.year or ""), source="user_provided",
                    doi=c.ids.get("doi"), journal=c.venue,
                ))
            except RegistryUnavailable:
                raise
            except Exception as e:
                print(f"Error processing user link {link}: {e}")

        return sources

    async def _rank_and_score_sources(self, sources: List[ResearchSource], subject: str) -> List[ResearchSource]:
        """Rank and score research sources by relevance"""
        subject_lower = subject.lower()
        # For TDA topics, also match on core terminology to boost actual TDA papers
        tda_terms = ["topological data analysis", "tda", "persistent homology", "mapper algorithm", "simplicial complex"]
        is_tda_topic = "topological data analysis" in subject_lower or " tda " in subject_lower or subject_lower.strip() == "tda"
        
        # Calculate relevance scores
        for source in sources:
            score = 0.0
            
            # Base score from source type
            score += self.source_weights.get(source.source, 0.5)
            
            # Title relevance
            if subject_lower in source.title.lower():
                score += 0.3
            
            # Abstract relevance
            if source.abstract and subject_lower in source.abstract.lower():
                score += 0.2
            
            # TDA-specific: boost papers that actually discuss TDA (avoid physics/astronomy false matches)
            if is_tda_topic and source.abstract:
                abstract_lower = (source.title + " " + (source.abstract or "")).lower()
                for term in tda_terms:
                    if term in abstract_lower:
                        score += 0.25  # Strong boost for topic-relevant papers
                        break
            
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

                journal_elem = article.find(".//Journal/Title")
                if journal_elem is None or not (journal_elem.text or "").strip():
                    journal_elem = article.find(".//Journal/ISOAbbreviation")
                journal = (journal_elem.text or "").strip() if journal_elem is not None else ""

                year = ""
                year_elem = article.find(".//PubDate/Year")
                if year_elem is not None and (year_elem.text or "").strip():
                    year = year_elem.text.strip()[:4]
                else:
                    medline = article.find(".//PubDate/MedlineDate")
                    if medline is not None and medline.text:
                        m = re.match(r"(\d{4})", medline.text.strip())
                        if m:
                            year = m.group(1)

                doi = ""
                doi_elem = article.find(".//ArticleId[@IdType='doi']")
                if doi_elem is not None and doi_elem.text:
                    doi = doi_elem.text.strip()
                
                source = ResearchSource(
                    title=title,
                    authors=author_names,
                    abstract=abstract,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    publication_date=year,
                    source="pubmed",
                    doi=doi or None,
                    journal=journal or None,
                    registry_record=_registry_records(xml_data, "pubmed").get(pmid),
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
                
                m = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5}v\d+)", link or "")
                source = ResearchSource(
                    title=title,
                    authors=authors,
                    abstract=summary,
                    url=link,
                    publication_date=published,
                    source="arxiv",
                    registry_record=_registry_records(xml_data, "arxiv").get(m.group(1)) if m else None,
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
