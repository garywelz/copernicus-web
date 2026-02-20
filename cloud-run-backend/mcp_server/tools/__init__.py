"""
MCP Tools for CopernicusAI Knowledge Engine

This package contains tool implementations for:
- Research Paper Metadata Database (Phase 2)
- GLMP Process Database (Phase 3)
- CopernicusAI Podcasts (Phase 4)
- Cross-Component Integration (Phase 5)
"""

# Research Paper Tools (Phase 2)
from .papers import (
    query_research_papers,
    get_paper_by_id,
    get_paper_citations,
    search_papers_by_entity
)

# GLMP Tools (Phase 3)
from .glmp import (
    list_glmp_processes,
    get_glmp_process,
    search_glmp_by_entity,
    get_glmp_categories
)

# Podcast Tools (Phase 4)
from .podcasts import (
    list_podcasts,
    get_podcast_details,
    get_podcast_source_papers,
    search_podcasts_by_topic
)

# Cross-Component Tools (Phase 5)
from .cross_component import (
    find_related_content,
    get_paper_visualizations,
    search_across_components
)

__all__ = [
    # Research Paper Tools
    "query_research_papers",
    "get_paper_by_id",
    "get_paper_citations",
    "search_papers_by_entity",
    # GLMP Tools
    "list_glmp_processes",
    "get_glmp_process",
    "search_glmp_by_entity",
    "get_glmp_categories",
    # Podcast Tools
    "list_podcasts",
    "get_podcast_details",
    "get_podcast_source_papers",
    "search_podcasts_by_topic",
    # Cross-Component Tools
    "find_related_content",
    "get_paper_visualizations",
    "search_across_components",
]

