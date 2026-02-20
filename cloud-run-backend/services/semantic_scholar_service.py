"""
Semantic Scholar API Service

Fetches citation data from Semantic Scholar API for knowledge map construction.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class SemanticScholarService:
    """
    Service for fetching citation data from Semantic Scholar API.
    
    API Documentation: https://api.semanticscholar.org/api-docs/
    """
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Semantic Scholar service.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.session = None
        self.rate_limit_delay = 0.1  # 100ms between requests (10 req/sec free tier)
        
        if api_key:
            structured_logger.info("Semantic Scholar service initialized with API key")
        else:
            structured_logger.info("Semantic Scholar service initialized (free tier)")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None:
            headers = {}
            if self.api_key:
                headers['x-api-key'] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get paper data from Semantic Scholar by arXiv ID.
        
        Args:
            arxiv_id: arXiv ID (e.g., "2301.00001" or "math.AT/2301.00001")
        
        Returns:
            Paper data with citations and references, or None if not found
        """
        # Clean arXiv ID
        arxiv_id_clean = arxiv_id.replace('arxiv:', '').replace('math.', '').split('/')[-1]
        
        try:
            session = await self._get_session()
            
            # Search by arXiv ID
            url = f"{self.BASE_URL}/paper/arXiv:{arxiv_id_clean}"
            fields = "paperId,title,authors,abstract,url,venue,year,citationCount,referenceCount,fieldsOfStudy,publicationDate,citations,citations.paperId,citations.title,references,references.paperId,references.title"
            
            async with session.get(url, params={'fields': fields}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 404:
                    logger.debug(f"Paper not found in Semantic Scholar: {arxiv_id}")
                    return None
                else:
                    logger.warning(f"Semantic Scholar API error: HTTP {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching paper from Semantic Scholar: {e}")
            return None
        
        finally:
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
    
    async def get_paper_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Get paper data from Semantic Scholar by DOI.
        
        Args:
            doi: DOI (e.g., "10.1234/example")
        
        Returns:
            Paper data with citations and references, or None if not found
        """
        try:
            session = await self._get_session()
            
            url = f"{self.BASE_URL}/paper/{quote(doi)}"
            fields = "paperId,title,authors,abstract,url,venue,year,citationCount,referenceCount,fieldsOfStudy,publicationDate,citations,citations.paperId,citations.title,references,references.paperId,references.title"
            
            async with session.get(url, params={'fields': fields}) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                elif response.status == 404:
                    logger.debug(f"Paper not found in Semantic Scholar: {doi}")
                    return None
                else:
                    logger.warning(f"Semantic Scholar API error: HTTP {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching paper from Semantic Scholar: {e}")
            return None
        
        finally:
            await asyncio.sleep(self.rate_limit_delay)
    
    async def get_citations_batch(
        self,
        papers: List[Dict[str, Any]],
        max_papers: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch citation data for a batch of papers.
        
        Args:
            papers: List of paper dictionaries with arxiv_id or doi
            max_papers: Maximum number of papers to process (None for all)
        
        Returns:
            Dictionary mapping paper_id to citation data
        """
        if max_papers:
            papers = papers[:max_papers]
        
        structured_logger.info(f"Fetching citations for {len(papers)} papers from Semantic Scholar")
        
        citation_data = {}
        successful = 0
        failed = 0
        
        for i, paper in enumerate(papers, 1):
            paper_id = paper.get('paper_id') or paper.get('id')
            arxiv_id = paper.get('arxiv_id')
            doi = paper.get('doi')
            
            if not arxiv_id and not doi:
                failed += 1
                continue
            
            try:
                # Try arXiv ID first, then DOI
                if arxiv_id:
                    data = await self.get_paper_by_arxiv_id(arxiv_id)
                elif doi:
                    data = await self.get_paper_by_doi(doi)
                else:
                    data = None
                
                if data:
                    citation_data[paper_id] = {
                        'semantic_scholar_id': data.get('paperId'),
                        'citation_count': data.get('citationCount', 0),
                        'reference_count': data.get('referenceCount', 0),
                        'citations': [
                            {
                                'paper_id': cit.get('paperId'),
                                'title': cit.get('title')
                            }
                            for cit in data.get('citations', [])[:50]  # Limit to 50 citations
                        ],
                        'references': [
                            {
                                'paper_id': ref.get('paperId'),
                                'title': ref.get('title')
                            }
                            for ref in data.get('references', [])[:50]  # Limit to 50 references
                        ]
                    }
                    successful += 1
                else:
                    failed += 1
                
                if i % 10 == 0:
                    structured_logger.info(
                        f"Progress: {i}/{len(papers)} (successful: {successful}, failed: {failed})"
                    )
            
            except Exception as e:
                logger.error(f"Error processing paper {paper_id}: {e}")
                failed += 1
        
        structured_logger.info(
            f"Citation fetch complete: {successful} successful, {failed} failed"
        )
        
        return citation_data


def get_semantic_scholar_service(api_key: Optional[str] = None) -> SemanticScholarService:
    """Get or create Semantic Scholar service instance."""
    import os
    api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    return SemanticScholarService(api_key=api_key)

