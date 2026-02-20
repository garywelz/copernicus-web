"""
MCP Tools for Research Paper Metadata Database

Provides tools for querying research papers stored in Firestore.
"""

import logging
from typing import Any, Dict, List, Optional
import json

from mcp_server.utils.firestore_client import (
    get_firestore_client,
    query_collection,
    get_document
)
from mcp_server.config import (
    COLLECTION_PAPERS,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT
)

logger = logging.getLogger(__name__)


async def query_research_papers(
    query: Optional[str] = None,
    discipline: Optional[str] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Query research papers by search terms, discipline, or keywords.
    
    Args:
        query: Search query string (searches in title, abstract, keywords)
        discipline: Filter by discipline (e.g., "biology", "chemistry", "physics")
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with list of matching papers
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Build filters
        filters = []
        if discipline:
            filters.append(("discipline", "==", discipline))
        
        # Query Firestore
        papers = query_collection(
            collection_name=COLLECTION_PAPERS,
            filters=filters if filters else None,
            order_by="created_at",
            limit=limit
        )
        
        # Filter by query string if provided (client-side filtering for text search)
        if query:
            query_lower = query.lower()
            filtered_papers = []
            for paper in papers:
                title = paper.get("title", "").lower()
                abstract = paper.get("abstract", "").lower() if paper.get("abstract") else ""
                keywords = " ".join(paper.get("keywords", [])).lower()
                
                if (query_lower in title or 
                    query_lower in abstract or 
                    query_lower in keywords):
                    filtered_papers.append(paper)
            papers = filtered_papers[:limit]
        
        # Format results
        results = []
        for paper in papers:
            results.append({
                "paper_id": paper.get("paper_id") or paper.get("id"),
                "doi": paper.get("doi"),
                "title": paper.get("title", "Untitled"),
                "authors": paper.get("authors", []),
                "abstract": paper.get("abstract"),
                "discipline": paper.get("discipline"),
                "url": paper.get("url"),
                "created_at": paper.get("created_at"),
                "has_preprocessing": paper.get("preprocessing") is not None
            })
        
        return json.dumps({
            "papers": results,
            "count": len(results),
            "query": query,
            "discipline": discipline
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error querying research papers: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to query papers: {str(e)}",
            "papers": [],
            "count": 0
        })


async def get_paper_by_id(
    paper_id: Optional[str] = None,
    doi: Optional[str] = None
) -> str:
    """
    Get full paper metadata by paper_id or DOI.
    
    Args:
        paper_id: Paper ID (UUID)
        doi: DOI (Digital Object Identifier)
        
    Returns:
        JSON string with full paper metadata including preprocessing
    """
    try:
        if not paper_id and not doi:
            return json.dumps({
                "error": "Either paper_id or doi must be provided",
                "paper": None
            })
        
        db = get_firestore_client()
        papers_ref = db.collection(COLLECTION_PAPERS)
        
        # Try to find by paper_id first
        if paper_id:
            paper = get_document(COLLECTION_PAPERS, paper_id)
            if paper:
                return json.dumps({"paper": paper}, indent=2)
        
        # Try to find by DOI
        if doi:
            papers = query_collection(
                collection_name=COLLECTION_PAPERS,
                filters=[("doi", "==", doi)],
                limit=1
            )
            if papers:
                return json.dumps({"paper": papers[0]}, indent=2)
        
        return json.dumps({
            "error": "Paper not found",
            "paper": None,
            "paper_id": paper_id,
            "doi": doi
        })
        
    except Exception as e:
        logger.error(f"Error getting paper: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get paper: {str(e)}",
            "paper": None
        })


async def get_paper_citations(
    paper_id: Optional[str] = None,
    doi: Optional[str] = None
) -> str:
    """
    Get papers that cite the specified paper.
    
    Note: This requires citation data to be stored in Firestore.
    Currently searches for papers that reference this paper's DOI or title.
    
    Args:
        paper_id: Paper ID
        doi: DOI of the paper
        
    Returns:
        JSON string with list of citing papers
    """
    try:
        # First, get the target paper
        target_paper = None
        if paper_id:
            target_paper = get_document(COLLECTION_PAPERS, paper_id)
        elif doi:
            papers = query_collection(
                collection_name=COLLECTION_PAPERS,
                filters=[("doi", "==", doi)],
                limit=1
            )
            if papers:
                target_paper = papers[0]
        
        if not target_paper:
            return json.dumps({
                "error": "Paper not found",
                "citing_papers": [],
                "count": 0
            })
        
        target_doi = target_paper.get("doi")
        target_title = target_paper.get("title", "")
        
        # Search for papers that might cite this one
        # This is a simplified search - in production, you'd have explicit citation links
        all_papers = query_collection(
            collection_name=COLLECTION_PAPERS,
            limit=MAX_QUERY_LIMIT
        )
        
        citing_papers = []
        for paper in all_papers:
            # Skip the target paper itself
            if paper.get("paper_id") == target_paper.get("paper_id"):
                continue
            
            # Check if paper references the target (in abstract, preprocessing, etc.)
            abstract = paper.get("abstract", "").lower() if paper.get("abstract") else ""
            preprocessing = paper.get("preprocessing", {})
            llm_summary = preprocessing.get("llm_summary", "").lower() if preprocessing else ""
            
            # Simple heuristic: check if DOI or title appears in text
            if target_doi and target_doi.lower() in (abstract + llm_summary):
                citing_papers.append({
                    "paper_id": paper.get("paper_id") or paper.get("id"),
                    "title": paper.get("title"),
                    "doi": paper.get("doi"),
                    "authors": paper.get("authors", [])
                })
            elif target_title and len(target_title) > 10:
                # Check if significant portion of title appears
                title_words = set(target_title.lower().split()[:5])  # First 5 words
                text_words = set((abstract + llm_summary).split())
                if len(title_words.intersection(text_words)) >= 2:
                    citing_papers.append({
                        "paper_id": paper.get("paper_id") or paper.get("id"),
                        "title": paper.get("title"),
                        "doi": paper.get("doi"),
                        "authors": paper.get("authors", [])
                    })
        
        return json.dumps({
            "target_paper": {
                "paper_id": target_paper.get("paper_id") or target_paper.get("id"),
                "title": target_paper.get("title"),
                "doi": target_paper.get("doi")
            },
            "citing_papers": citing_papers,
            "count": len(citing_papers)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting paper citations: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get citations: {str(e)}",
            "citing_papers": [],
            "count": 0
        })


async def search_papers_by_entity(
    entity: str,
    entity_type: Optional[str] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Search for papers that mention a specific entity (gene, protein, chemical, etc.).
    
    Searches in preprocessing entities_extracted field.
    
    Args:
        entity: Entity name (e.g., "p53", "CRISPR", "ATP")
        entity_type: Optional entity type filter (e.g., "gene", "protein", "chemical")
        limit: Maximum number of results (default: 10, max: 100)
        
    Returns:
        JSON string with list of papers containing the entity
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Get all papers with preprocessing
        all_papers = query_collection(
            collection_name=COLLECTION_PAPERS,
            limit=MAX_QUERY_LIMIT
        )
        
        entity_lower = entity.lower()
        matching_papers = []
        
        for paper in all_papers:
            preprocessing = paper.get("preprocessing")
            if not preprocessing:
                continue
            
            entities_extracted = preprocessing.get("entities_extracted", {})
            if not entities_extracted:
                continue
            
            # Search in entities
            found = False
            for entity_key, entity_list in entities_extracted.items():
                if entity_type and entity_key.lower() != entity_type.lower():
                    continue
                
                if isinstance(entity_list, list):
                    for e in entity_list:
                        if isinstance(e, str) and entity_lower in e.lower():
                            found = True
                            break
                elif isinstance(entity_list, str) and entity_lower in entity_list.lower():
                    found = True
                
                if found:
                    break
            
            if found:
                matching_papers.append({
                    "paper_id": paper.get("paper_id") or paper.get("id"),
                    "title": paper.get("title"),
                    "doi": paper.get("doi"),
                    "authors": paper.get("authors", []),
                    "discipline": paper.get("discipline"),
                    "entities_found": entities_extracted
                })
                
                if len(matching_papers) >= limit:
                    break
        
        return json.dumps({
            "entity": entity,
            "entity_type": entity_type,
            "papers": matching_papers,
            "count": len(matching_papers)
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error searching papers by entity: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to search by entity: {str(e)}",
            "papers": [],
            "count": 0
        })



