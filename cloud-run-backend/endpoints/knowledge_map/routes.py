"""
Knowledge Map API Endpoints

Provides endpoints for querying and visualizing the knowledge map.

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import json

from services.knowledge_map_service import get_knowledge_map_service
from services.knowledge_map_queries import get_query_service
from utils.logging import structured_logger
from config.database import db as firestore_db

router = APIRouter(prefix="/api/knowledge-map", tags=["knowledge-map"])


@router.get("/graph")
async def get_knowledge_graph(
    max_papers: Optional[int] = Query(None, description="Maximum number of papers to include"),
    include_concepts: bool = Query(True, description="Include concept nodes"),
    include_similarity: bool = Query(True, description="Include similarity relationships"),
    include_categories: bool = Query(True, description="Include category relationships"),
    format: str = Query("cytoscape", description="Output format: cytoscape, d3, or raw"),
    force_rebuild: bool = Query(False, description="Force rebuild even if graph exists"),
    # New filtering parameters
    content_types: Optional[str] = Query(None, description="Comma-separated content types: papers,processes,videos,podcasts"),
    disciplines: Optional[str] = Query(None, description="Comma-separated disciplines: biology,chemistry,physics,mathematics,computer_science,interdisciplinary"),
    sources: Optional[str] = Query(None, description="Comma-separated sources: pubmed,arxiv,nasa_ads,crossref,youtube,rss"),
    date_start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    keyword: Optional[str] = Query(None, description="Keyword search in title/abstract")
):
    """
    Get the full knowledge graph.
    
    Returns nodes and edges for visualization.
    Caches the graph in memory for faster subsequent requests.
    """
    try:
        service = get_knowledge_map_service()
        
        # Parse filter parameters
        content_types_list = content_types.split(',') if content_types else None
        disciplines_list = disciplines.split(',') if disciplines else None
        sources_list = sources.split(',') if sources else None
        
        # Check if any filters are present - if so, force rebuild
        has_filters = any([
            content_types_list,
            disciplines_list,
            sources_list,
            date_start,
            date_end,
            keyword
        ])
        
        # Always clear cache and rebuild when filters are present or force_rebuild is True
        # This ensures we get fresh data matching the filters
        if force_rebuild or has_filters:
            structured_logger.info("Clearing cache and rebuilding graph due to filters or force_rebuild",
                                 has_filters=has_filters,
                                 force_rebuild=force_rebuild,
                                 filters={
                                     'content_types': content_types_list,
                                     'disciplines': disciplines_list,
                                     'sources': sources_list,
                                     'date_start': date_start,
                                     'date_end': date_end,
                                     'keyword': keyword
                                 })
            service.clear_cache()
        elif service.nodes and len(service.nodes) > 0:
            # Only use cached graph if no filters and not forcing rebuild
            structured_logger.info("Using cached knowledge graph", 
                                 node_count=len(service.nodes),
                                 edge_count=len(service.edges))
            # Export existing graph
            if format == "raw":
                graph = {
                    'nodes': list(service.nodes.values()),
                    'edges': service.edges,
                    'metadata': {
                        'papers': sum(1 for n in service.nodes.values() if n.get('type') == 'paper'),
                        'concepts': sum(1 for n in service.nodes.values() if n.get('type') == 'concept'),
                        'relationships': len(service.edges),
                        'built_at': datetime.now().isoformat(),
                        'cached': True
                    }
                }
                return graph
            else:
                export_data = service.export_for_visualization(format=format)
                export_data['metadata'] = {
                    'papers': sum(1 for n in service.nodes.values() if n.get('type') == 'paper'),
                    'concepts': sum(1 for n in service.nodes.values() if n.get('type') == 'concept'),
                    'relationships': len(service.edges),
                    'built_at': datetime.now().isoformat(),
                    'cached': True
                }
                return export_data
        
        # Build new graph with filters
        graph = await service.build_graph(
            max_papers=max_papers,
            include_concepts=include_concepts,
            include_similarity=include_similarity,
            include_categories=include_categories,
            content_types=content_types_list,
            disciplines=disciplines_list,
            sources=sources_list,
            date_start=date_start,
            date_end=date_end,
            keyword=keyword
        )
        
        if format == "raw":
            return graph
        else:
            export_data = service.export_for_visualization(format=format)
            export_data['metadata'] = graph['metadata']
            return export_data
    
    except Exception as e:
        structured_logger.error(f"Failed to build knowledge graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build knowledge graph: {str(e)}")


@router.get("/subgraph/{paper_id}")
async def get_subgraph(
    paper_id: str,
    depth: int = Query(2, description="Relationship depth"),
    max_nodes: int = Query(50, description="Maximum number of nodes")
):
    """
    Get a subgraph centered on a specific paper.
    
    Returns nodes and edges connected to the specified paper.
    """
    try:
        service = get_knowledge_map_service()
        
        # Build graph first if not already built
        if not service.nodes:
            await service.build_graph(max_papers=1000)  # Build with reasonable limit
        
        subgraph = service.get_subgraph(paper_id, depth=depth, max_nodes=max_nodes)
        
        # Export for visualization
        export_data = service.export_for_visualization(format="cytoscape")
        
        # Filter to only subgraph nodes and edges
        subgraph_node_ids = {n['id'] for n in subgraph['nodes']}
        filtered_nodes = [n for n in export_data['nodes'] if n['data']['id'] in subgraph_node_ids]
        filtered_edges = [
            e for e in export_data['edges']
            if e['data']['source'] in subgraph_node_ids and e['data']['target'] in subgraph_node_ids
        ]
        
        return {
            'nodes': filtered_nodes,
            'edges': filtered_edges,
            'center': paper_id,
            'depth': depth,
            'metadata': {
                'nodes': len(filtered_nodes),
                'edges': len(filtered_edges)
            }
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to get subgraph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get subgraph: {str(e)}")


@router.get("/stats")
async def get_knowledge_map_stats():
    """Get statistics about the knowledge map."""
    try:
        # IMPORTANT: This endpoint should never hard-fail just because embeddings/Vertex are disabled.
        # We return:
        # - knowledge-map graph stats if cached graph exists
        # - plus Firestore collection counts (papers) as a useful baseline

        # Baseline counts from Firestore (Vertex-free)
        papers_total = 0
        try:
            if firestore_db:
                count_res = firestore_db.collection("research_papers").count().get()
                # Result shape: [ [Aggregation(...)] ]
                if count_res and isinstance(count_res[0], list) and count_res[0]:
                    papers_total = int(getattr(count_res[0][0], "value", 0) or 0)
        except Exception as e:
            structured_logger.warning("Failed to count research_papers for knowledge-map stats", error=str(e))

        # Try to use cached knowledge map if available
        try:
            service = get_knowledge_map_service()
            if service.nodes and len(service.nodes) > 0:
                papers = sum(1 for n in service.nodes.values() if n.get('type') == 'paper')
                concepts = sum(1 for n in service.nodes.values() if n.get('type') == 'concept')
                return {
                    'papers': papers,
                    'concepts': concepts,
                    'nodes': len(service.nodes),
                    'edges': len(service.edges),
                    'cached': True,
                    'papers_total_in_firestore': papers_total,
                }
        except Exception as e:
            # If the knowledge map service can't initialize (e.g. Vertex disabled), that's fine.
            structured_logger.info("Knowledge map service unavailable for stats; returning Firestore-only baseline", error=str(e))

        return {
            'papers': 0,
            'concepts': 0,
            'nodes': 0,
            'edges': 0,
            'cached': False,
            'papers_total_in_firestore': papers_total,
            'note': 'Load the Knowledge Map tab to build/cache the graph. Vertex/embeddings are not required for counts.',
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/query/papers-by-concept")
async def query_papers_by_concept(
    concept: str = Query(..., description="Concept name to search for"),
    limit: int = Query(20, description="Maximum number of papers to return")
):
    """Find papers that mention a specific concept."""
    try:
        service = get_knowledge_map_service()
        
        # Build graph if not already built
        if not service.nodes:
            await service.build_graph(max_papers=1000)
        
        query_service = get_query_service(service)
        papers = query_service.find_papers_by_concept(concept, limit=limit)
        
        return {
            'concept': concept,
            'papers': papers,
            'count': len(papers)
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to query papers by concept: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to query: {str(e)}")


@router.get("/query/path")
async def query_path(
    source: str = Query(..., description="Source paper ID"),
    target: str = Query(..., description="Target paper ID"),
    max_depth: int = Query(5, description="Maximum path depth"),
    relationship_types: Optional[List[str]] = Query(None, description="Filter by relationship types")
):
    """Find shortest path between two papers."""
    try:
        service = get_knowledge_map_service()
        
        if not service.nodes:
            await service.build_graph(max_papers=1000)
        
        query_service = get_query_service(service)
        path = query_service.find_path(source, target, max_depth=max_depth, relationship_types=relationship_types)
        
        if path is None:
            return {
                'source': source,
                'target': target,
                'path': None,
                'found': False
            }
        
        return {
            'source': source,
            'target': target,
            'path': path,
            'length': len(path),
            'found': True
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to find path: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find path: {str(e)}")


@router.get("/query/related")
async def query_related_papers(
    paper_id: str = Query(..., description="Paper ID to find related papers for"),
    depth: int = Query(2, description="Relationship depth"),
    limit: int = Query(20, description="Maximum number of papers"),
    relationship_types: Optional[List[str]] = Query(None, description="Filter by relationship types")
):
    """Find papers related to a given paper."""
    try:
        service = get_knowledge_map_service()
        
        if not service.nodes:
            await service.build_graph(max_papers=1000)
        
        query_service = get_query_service(service)
        related = query_service.find_related_papers(
            paper_id,
            depth=depth,
            max_papers=limit,
            relationship_types=relationship_types
        )
        
        return {
            'paper_id': paper_id,
            'related_papers': related,
            'count': len(related)
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to find related papers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find related papers: {str(e)}")


@router.get("/query/search")
async def query_search_papers(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Search papers by title."""
    try:
        service = get_knowledge_map_service()
        
        if not service.nodes:
            await service.build_graph(max_papers=1000)
        
        query_service = get_query_service(service)
        results = query_service.search_papers(q, limit=limit)
        
        return {
            'query': q,
            'results': results,
            'count': len(results)
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to search papers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")


@router.get("/query/cluster")
async def query_paper_cluster(
    paper_id: str = Query(..., description="Seed paper ID"),
    min_cluster_size: int = Query(3, description="Minimum cluster size")
):
    """Get cluster of closely connected papers."""
    try:
        service = get_knowledge_map_service()
        
        if not service.nodes:
            await service.build_graph(max_papers=1000)
        
        query_service = get_query_service(service)
        cluster = query_service.get_paper_cluster(paper_id, min_cluster_size=min_cluster_size)
        
        return {
            'paper_id': paper_id,
            'cluster': cluster,
            'size': len(cluster)
        }
    
    except Exception as e:
        structured_logger.error(f"Failed to get cluster: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cluster: {str(e)}")

