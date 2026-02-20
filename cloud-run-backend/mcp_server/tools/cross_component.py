"""
MCP Tools for Cross-Component Integration

Provides tools for querying across multiple knowledge engine components,
enabling cross-modal linking and relationship discovery.
"""

import logging
from typing import Any, Dict, List, Optional
import json

from mcp_server.tools.papers import query_research_papers, get_paper_by_id
from mcp_server.tools.glmp import list_glmp_processes, search_glmp_by_entity
from mcp_server.tools.podcasts import list_podcasts, get_podcast_details
from mcp_server.config import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT

logger = logging.getLogger(__name__)


async def find_related_content(
    paper_id: Optional[str] = None,
    podcast_id: Optional[str] = None,
    process_id: Optional[str] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Find related content across all components for a given paper, podcast, or process.
    
    Args:
        paper_id: Paper ID or DOI
        podcast_id: Podcast job ID
        process_id: GLMP process ID
        limit: Maximum results per component (default: 10, max: 100)
        
    Returns:
        JSON string with related content from all components
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        related_content = {
            "query": {},
            "papers": [],
            "podcasts": [],
            "glmp_processes": []
        }
        
        # If paper_id provided, find related podcasts and GLMP processes
        if paper_id:
            related_content["query"]["paper_id"] = paper_id
            
            # Get paper details
            paper_result = await get_paper_by_id(paper_id=paper_id)
            paper_data = json.loads(paper_result)
            paper = paper_data.get("paper")
            
            if paper:
                # Extract entities and keywords from paper
                preprocessing = paper.get("preprocessing", {})
                entities = preprocessing.get("entities_extracted", {})
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                
                # Find podcasts that might reference this paper
                # Search by DOI, title keywords, or entity overlap
                podcasts_result = await list_podcasts(limit=MAX_QUERY_LIMIT)
                podcasts_data = json.loads(podcasts_result)
                
                for podcast in podcasts_data.get("podcasts", []):
                    podcast_details_result = await get_podcast_details(podcast.get("job_id"))
                    podcast_details = json.loads(podcast_details_result)
                    podcast_data = podcast_details.get("podcast", {})
                    
                    # Check if podcast references this paper
                    source_papers = podcast_data.get("source_papers", [])
                    paper_doi = podcast_data.get("paper_doi")
                    
                    if (paper.get("doi") and paper_doi == paper.get("doi")) or \
                       any(paper.get("doi") in str(sp) for sp in source_papers):
                        related_content["podcasts"].append({
                            "job_id": podcast.get("job_id"),
                            "title": podcast.get("title"),
                            "category": podcast.get("category")
                        })
                
                # Find GLMP processes related to paper entities
                if entities:
                    for entity_type, entity_list in entities.items():
                        if isinstance(entity_list, list):
                            for entity in entity_list[:3]:  # Check first 3 entities
                                if isinstance(entity, str):
                                    glmp_result = await search_glmp_by_entity(entity=entity, limit=5)
                                    glmp_data = json.loads(glmp_result)
                                    related_content["glmp_processes"].extend(
                                        glmp_data.get("processes", [])
                                    )
        
        # If podcast_id provided, find related papers and GLMP processes
        elif podcast_id:
            related_content["query"]["podcast_id"] = podcast_id
            
            # Get podcast source papers
            from mcp_server.tools.podcasts import get_podcast_source_papers
            papers_result = await get_podcast_source_papers(podcast_id=podcast_id)
            papers_data = json.loads(papers_result)
            related_content["papers"] = papers_data.get("source_papers", [])
            
            # Find GLMP processes related to podcast topic
            podcast_details_result = await get_podcast_details(podcast_id=podcast_id)
            podcast_details = json.loads(podcast_details_result)
            podcast_data = podcast_details.get("podcast", {})
            topic = podcast_data.get("title", "")
            
            # Search GLMP by topic keywords
            if topic:
                keywords = topic.split()[:3]  # First 3 words
                for keyword in keywords:
                    if len(keyword) > 3:  # Skip short words
                        glmp_result = await list_glmp_processes(limit=5)
                        glmp_data = json.loads(glmp_result)
                        # Filter by keyword match in title/description
                        for process in glmp_data.get("processes", []):
                            if keyword.lower() in process.get("title", "").lower():
                                related_content["glmp_processes"].append(process)
        
        # If process_id provided, find related papers and podcasts
        elif process_id:
            related_content["query"]["process_id"] = process_id
            
            # Get process details
            from mcp_server.tools.glmp import get_glmp_process
            process_result = await get_glmp_process(process_id=process_id)
            process_data = json.loads(process_result)
            process = process_data.get("process")
            
            if process:
                # Extract entities from process
                entities = process.get("entities", [])
                title = process.get("title", "")
                
                # Find papers mentioning these entities
                if entities:
                    for entity in entities[:3]:  # First 3 entities
                        if isinstance(entity, str):
                            papers_result = await query_research_papers(
                                query=entity,
                                limit=5
                            )
                            papers_data = json.loads(papers_result)
                            related_content["papers"].extend(
                                papers_data.get("papers", [])
                            )
                
                # Find podcasts related to process topic
                podcasts_result = await list_podcasts(limit=MAX_QUERY_LIMIT)
                podcasts_data = json.loads(podcasts_result)
                
                for podcast in podcasts_data.get("podcasts", []):
                    if title.lower() in podcast.get("title", "").lower():
                        related_content["podcasts"].append(podcast)
        
        # Deduplicate results
        seen_papers = set()
        unique_papers = []
        for paper in related_content["papers"]:
            paper_id = paper.get("paper_id") or paper.get("doi")
            if paper_id and paper_id not in seen_papers:
                seen_papers.add(paper_id)
                unique_papers.append(paper)
        related_content["papers"] = unique_papers[:limit]
        
        seen_podcasts = set()
        unique_podcasts = []
        for podcast in related_content["podcasts"]:
            podcast_id = podcast.get("job_id")
            if podcast_id and podcast_id not in seen_podcasts:
                seen_podcasts.add(podcast_id)
                unique_podcasts.append(podcast)
        related_content["podcasts"] = unique_podcasts[:limit]
        
        seen_processes = set()
        unique_processes = []
        for process in related_content["glmp_processes"]:
            process_id = process.get("id")
            if process_id and process_id not in seen_processes:
                seen_processes.add(process_id)
                unique_processes.append(process)
        related_content["glmp_processes"] = unique_processes[:limit]
        
        # Add counts
        related_content["counts"] = {
            "papers": len(related_content["papers"]),
            "podcasts": len(related_content["podcasts"]),
            "glmp_processes": len(related_content["glmp_processes"])
        }
        
        return json.dumps(related_content, indent=2)
        
    except Exception as e:
        logger.error(f"Error finding related content: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to find related content: {str(e)}",
            "papers": [],
            "podcasts": [],
            "glmp_processes": [],
            "counts": {"papers": 0, "podcasts": 0, "glmp_processes": 0}
        })


async def get_paper_visualizations(
    paper_id: Optional[str] = None,
    doi: Optional[str] = None
) -> str:
    """
    Get GLMP processes and Programming Framework diagrams related to a paper.
    
    Args:
        paper_id: Paper ID
        doi: Paper DOI
        
    Returns:
        JSON string with related visualizations
    """
    try:
        # Get paper details
        paper_result = await get_paper_by_id(paper_id=paper_id, doi=doi)
        paper_data = json.loads(paper_result)
        paper = paper_data.get("paper")
        
        if not paper:
            return json.dumps({
                "error": "Paper not found",
                "paper_id": paper_id,
                "doi": doi,
                "visualizations": []
            })
        
        visualizations = {
            "paper": {
                "paper_id": paper.get("paper_id") or paper.get("id"),
                "title": paper.get("title"),
                "doi": paper.get("doi")
            },
            "glmp_processes": [],
            "programming_framework_diagrams": []  # Future: Programming Framework integration
        }
        
        # Extract entities from paper
        preprocessing = paper.get("preprocessing", {})
        entities = preprocessing.get("entities_extracted", {})
        
        # Find GLMP processes related to paper entities
        if entities:
            for entity_type, entity_list in entities.items():
                if isinstance(entity_list, list):
                    for entity in entity_list[:5]:  # Check first 5 entities
                        if isinstance(entity, str) and len(entity) > 2:
                            glmp_result = await search_glmp_by_entity(entity=entity, limit=3)
                            glmp_data = json.loads(glmp_result)
                            visualizations["glmp_processes"].extend(
                                glmp_data.get("processes", [])
                            )
        
        # Deduplicate
        seen = set()
        unique_processes = []
        for process in visualizations["glmp_processes"]:
            process_id = process.get("id")
            if process_id and process_id not in seen:
                seen.add(process_id)
                unique_processes.append(process)
        visualizations["glmp_processes"] = unique_processes
        
        visualizations["counts"] = {
            "glmp_processes": len(visualizations["glmp_processes"]),
            "programming_framework_diagrams": 0  # Future
        }
        
        return json.dumps(visualizations, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting paper visualizations: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to get visualizations: {str(e)}",
            "visualizations": []
        })


async def search_across_components(
    query: str,
    components: Optional[List[str]] = None,
    limit: int = DEFAULT_QUERY_LIMIT
) -> str:
    """
    Search across multiple components (papers, podcasts, GLMP) with a single query.
    
    Args:
        query: Search query string
        components: List of components to search (default: all)
                    Options: ["papers", "podcasts", "glmp"]
        limit: Maximum results per component (default: 10, max: 100)
        
    Returns:
        JSON string with results from all specified components
    """
    try:
        # Validate limit
        limit = min(max(1, limit), MAX_QUERY_LIMIT)
        
        # Default to all components if not specified
        if not components:
            components = ["papers", "podcasts", "glmp"]
        
        results = {
            "query": query,
            "components_searched": components,
            "papers": [],
            "podcasts": [],
            "glmp_processes": []
        }
        
        # Search papers
        if "papers" in components:
            papers_result = await query_research_papers(query=query, limit=limit)
            papers_data = json.loads(papers_result)
            results["papers"] = papers_data.get("papers", [])
        
        # Search podcasts
        if "podcasts" in components:
            podcasts_result = await search_podcasts_by_topic(topic=query, limit=limit)
            podcasts_data = json.loads(podcasts_result)
            results["podcasts"] = podcasts_data.get("podcasts", [])
        
        # Search GLMP processes
        if "glmp" in components:
            # Try entity search first
            glmp_entity_result = await search_glmp_by_entity(entity=query, limit=limit)
            glmp_entity_data = json.loads(glmp_entity_result)
            results["glmp_processes"] = glmp_entity_data.get("processes", [])
            
            # Also try category search
            glmp_list_result = await list_glmp_processes(limit=limit)
            glmp_list_data = json.loads(glmp_list_result)
            # Filter by query match
            query_lower = query.lower()
            for process in glmp_list_data.get("processes", []):
                if query_lower in process.get("title", "").lower():
                    # Avoid duplicates
                    if not any(p.get("id") == process.get("id") for p in results["glmp_processes"]):
                        results["glmp_processes"].append(process)
        
        # Add summary counts
        results["counts"] = {
            "papers": len(results["papers"]),
            "podcasts": len(results["podcasts"]),
            "glmp_processes": len(results["glmp_processes"]),
            "total": len(results["papers"]) + len(results["podcasts"]) + len(results["glmp_processes"])
        }
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        logger.error(f"Error searching across components: {e}", exc_info=True)
        return json.dumps({
            "error": f"Failed to search: {str(e)}",
            "papers": [],
            "podcasts": [],
            "glmp_processes": [],
            "counts": {"papers": 0, "podcasts": 0, "glmp_processes": 0, "total": 0}
        })



