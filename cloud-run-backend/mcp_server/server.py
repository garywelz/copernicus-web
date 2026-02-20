"""
MCP Server for CopernicusAI Knowledge Engine

Main server implementation using Model Context Protocol (MCP).
This server exposes all knowledge engine components as queryable tools.

Usage:
    python -m mcp_server.server
"""

import asyncio
import sys
import logging
import json
from typing import Any, Sequence

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: MCP SDK not available: {e}")
    print("Install with: pip install mcp")
    MCP_AVAILABLE = False

# Local imports
from mcp_server.config import (
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT
)

# Tool implementations
from mcp_server.tools.papers import (
    query_research_papers,
    get_paper_by_id,
    get_paper_citations,
    search_papers_by_entity
)
from mcp_server.tools.glmp import (
    list_glmp_processes,
    get_glmp_process,
    search_glmp_by_entity,
    get_glmp_categories
)
from mcp_server.tools.podcasts import (
    list_podcasts,
    get_podcast_details,
    get_podcast_source_papers,
    search_podcasts_by_topic
)
from mcp_server.tools.cross_component import (
    find_related_content,
    get_paper_visualizations,
    search_across_components
)
from mcp_server.tools.vector_search import (
    search_semantic,
    find_similar_content
)
from mcp_server.tools.rag import (
    answer_with_rag,
    explain_concept,
    compare_concepts
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
if MCP_AVAILABLE:
    server = Server(MCP_SERVER_NAME)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List all available MCP tools.
    
    Includes tools from all implemented phases.
    """
    tools = [
        # Server info tool
        Tool(
            name="get_server_info",
            description="Get information about the CopernicusAI Knowledge Engine MCP server",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        # Research Paper Tools (Phase 2)
        Tool(
            name="query_research_papers",
            description="Query research papers by search terms, discipline, or keywords. Searches in title, abstract, and keywords.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (searches in title, abstract, keywords)"
                    },
                    "discipline": {
                        "type": "string",
                        "description": "Filter by discipline (e.g., 'biology', 'chemistry', 'physics')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_paper_by_id",
            description="Get full paper metadata by paper_id or DOI. Returns complete paper data including preprocessing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper ID (UUID)"
                    },
                    "doi": {
                        "type": "string",
                        "description": "DOI (Digital Object Identifier)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_paper_citations",
            description="Get papers that cite the specified paper. Searches for papers referencing the target paper's DOI or title.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper ID of the target paper"
                    },
                    "doi": {
                        "type": "string",
                        "description": "DOI of the target paper"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="search_papers_by_entity",
            description="Search for papers that mention a specific entity (gene, protein, chemical compound, etc.). Searches in preprocessing entities_extracted field.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name (e.g., 'p53', 'CRISPR', 'ATP')"
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Optional entity type filter (e.g., 'gene', 'protein', 'chemical')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": ["entity"]
            }
        ),
        # GLMP Tools (Phase 3)
        Tool(
            name="list_glmp_processes",
            description="List GLMP biological processes, optionally filtered by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category (e.g., 'metabolism', 'signaling', 'replication')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_glmp_process",
            description="Get full GLMP process details including Mermaid diagram.",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_id": {
                        "type": "string",
                        "description": "GLMP process ID"
                    },
                    "process_name": {
                        "type": "string",
                        "description": "Process name (alternative to process_id)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="search_glmp_by_entity",
            description="Search for GLMP processes that involve a specific entity (gene, protein, molecule).",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name (e.g., 'p53', 'ATP', 'CRISPR')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": ["entity"]
            }
        ),
        Tool(
            name="get_glmp_categories",
            description="Get list of all GLMP categories with process counts.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        # Podcast Tools (Phase 4)
        Tool(
            name="list_podcasts",
            description="List CopernicusAI podcast episodes, optionally filtered by discipline or subscriber ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "discipline": {
                        "type": "string",
                        "description": "Filter by discipline (e.g., 'biology', 'chemistry', 'physics')"
                    },
                    "subscriber_id": {
                        "type": "string",
                        "description": "Filter by subscriber ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_podcast_details",
            description="Get full metadata for a specific podcast episode by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "podcast_id": {
                        "type": "string",
                        "description": "Podcast episode ID"
                    }
                },
                "required": ["podcast_id"]
            }
        ),
        Tool(
            name="get_podcast_source_papers",
            description="Get the research papers that were used as sources for a specific podcast episode.",
            inputSchema={
                "type": "object",
                "properties": {
                    "podcast_id": {
                        "type": "string",
                        "description": "Podcast episode ID"
                    }
                },
                "required": ["podcast_id"]
            }
        ),
        Tool(
            name="search_podcasts_by_topic",
            description="Search for podcast episodes by topic or keywords in their title and description.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Search topic or keywords"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": ["topic"]
            }
        ),
        # Cross-Component Tools (Phase 5)
        Tool(
            name="find_related_content",
            description="Find related content (papers, GLMP processes, podcasts) across the CopernicusAI Knowledge Engine based on a query or entity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Find content related to this paper ID"
                    },
                    "podcast_id": {
                        "type": "string",
                        "description": "Find content related to this podcast ID"
                    },
                    "process_id": {
                        "type": "string",
                        "description": "Find content related to this GLMP process ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results per component (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_paper_visualizations",
            description="Get GLMP biological process diagrams that are related to a specific research paper by its ID or DOI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper ID"
                    },
                    "doi": {
                        "type": "string",
                        "description": "DOI (Digital Object Identifier)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="search_across_components",
            description="Perform a unified search across research papers, GLMP processes, and podcast episodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string"
                    },
                    "components": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["papers", "glmp", "podcasts"]
                        },
                        "description": "Components to search (default: all)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum number of results per component (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": ["query"]
            }
        ),
        # Vector Search Tools (Semantic Search)
        Tool(
            name="search_semantic",
            description="Semantic search across all content using vector embeddings. Finds content that is semantically similar to the query, even without exact keyword matches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "content_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["papers", "podcasts", "glmp"]
                        },
                        "description": "Content types to search (default: all)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum results per content type (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    },
                    "distance_threshold": {
                        "type": "number",
                        "description": "Maximum distance for similarity (0.0-1.0, lower = more similar, default: 0.7)",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="find_similar_content",
            description="Find content similar to a given paper, podcast, or GLMP process using vector embeddings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_id": {
                        "type": "string",
                        "description": "ID of the content item (paper_id, job_id, or process_id)"
                    },
                    "content_type": {
                        "type": "string",
                        "enum": ["paper", "podcast", "glmp"],
                        "description": "Type of content"
                    },
                    "limit": {
                        "type": "integer",
                        "description": f"Maximum results to return (default: {DEFAULT_QUERY_LIMIT}, max: {MAX_QUERY_LIMIT})",
                        "default": DEFAULT_QUERY_LIMIT,
                        "minimum": 1,
                        "maximum": MAX_QUERY_LIMIT
                    }
                },
                "required": ["content_id", "content_type"]
            }
        ),
        # RAG Tools (Question Answering)
        Tool(
            name="answer_with_rag",
            description="Answer questions using RAG (Retrieval-Augmented Generation). Retrieves relevant content from the knowledge base and generates grounded answers with citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question to answer"
                    },
                    "max_context_items": {
                        "type": "integer",
                        "description": "Maximum number of retrieved items to use as context (default: 5, max: 10)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10
                    },
                    "content_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["papers", "podcasts", "glmp"]
                        },
                        "description": "Content types to search (default: all)"
                    },
                    "include_sources": {
                        "type": "boolean",
                        "description": "Whether to include source citations (default: true)",
                        "default": True
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="explain_concept",
            description="Explain a scientific concept using RAG. Provides comprehensive explanations at different depth levels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Concept to explain (e.g., 'ATP synthesis', 'DNA replication')"
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["basic", "intermediate", "advanced"],
                        "description": "Explanation depth level (default: intermediate)",
                        "default": "intermediate"
                    },
                    "content_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["papers", "podcasts", "glmp"]
                        },
                        "description": "Content types to search (default: all)"
                    }
                },
                "required": ["concept"]
            }
        ),
        Tool(
            name="compare_concepts",
            description="Compare two scientific concepts using RAG. Highlights similarities, differences, and relationships.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept1": {
                        "type": "string",
                        "description": "First concept to compare"
                    },
                    "concept2": {
                        "type": "string",
                        "description": "Second concept to compare"
                    },
                    "content_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["papers", "podcasts", "glmp"]
                        },
                        "description": "Content types to search (default: all)"
                    }
                },
                "required": ["concept1", "concept2"]
            }
        ),
    ]
    
    logger.info(f"Listing {len(tools)} tools")
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """
    Handle tool calls from MCP clients.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Sequence of text content results
    """
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    if name == "get_server_info":
        info = f"""CopernicusAI Knowledge Engine MCP Server
Version: {MCP_SERVER_VERSION}
Server Name: {MCP_SERVER_NAME}

Available Components:
- Research Paper Metadata Database ✅ (4 tools implemented)
- GLMP (Genome Logic Modeling Project) ✅ (4 tools implemented)
- CopernicusAI Podcasts ✅ (4 tools implemented)
- Cross-Component Integration ✅ (3 tools implemented)
- Science Video Database (future)
- Programming Framework (future)

Status: Phase 7 (RAG) - 20 tools operational
- Core components: 15 tools
- Vector Search: 2 tools (semantic search)
- RAG: 3 tools (question answering, explanations, comparisons)
All core components complete! Vector search and RAG ready for testing.
"""
        return [TextContent(type="text", text=info)]
    
    # Research Paper Tools (Phase 2)
    elif name == "query_research_papers":
        query = arguments.get("query")
        discipline = arguments.get("discipline")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        result = await query_research_papers(query=query, discipline=discipline, limit=limit)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_paper_by_id":
        paper_id = arguments.get("paper_id")
        doi = arguments.get("doi")
        result = await get_paper_by_id(paper_id=paper_id, doi=doi)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_paper_citations":
        paper_id = arguments.get("paper_id")
        doi = arguments.get("doi")
        result = await get_paper_citations(paper_id=paper_id, doi=doi)
        return [TextContent(type="text", text=result)]
    
    elif name == "search_papers_by_entity":
        entity = arguments.get("entity")
        entity_type = arguments.get("entity_type")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        if not entity:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Entity parameter is required"}, indent=2)
            )]
        result = await search_papers_by_entity(entity=entity, entity_type=entity_type, limit=limit)
        return [TextContent(type="text", text=result)]
    
    # GLMP Tools (Phase 3)
    elif name == "list_glmp_processes":
        category = arguments.get("category")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        result = await list_glmp_processes(category=category, limit=limit)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_glmp_process":
        process_id = arguments.get("process_id")
        process_name = arguments.get("process_name")
        result = await get_glmp_process(process_id=process_id, process_name=process_name)
        return [TextContent(type="text", text=result)]
    
    elif name == "search_glmp_by_entity":
        entity = arguments.get("entity")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        if not entity:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Entity parameter is required"}, indent=2)
            )]
        result = await search_glmp_by_entity(entity=entity, limit=limit)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_glmp_categories":
        result = await get_glmp_categories()
        return [TextContent(type="text", text=result)]
    
    # Podcast Tools (Phase 4)
    elif name == "list_podcasts":
        discipline = arguments.get("discipline")
        subscriber_id = arguments.get("subscriber_id")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        result = await list_podcasts(discipline=discipline, subscriber_id=subscriber_id, limit=limit)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_podcast_details":
        podcast_id = arguments.get("podcast_id")
        if not podcast_id:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "podcast_id parameter is required"}, indent=2)
            )]
        result = await get_podcast_details(podcast_id=podcast_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "get_podcast_source_papers":
        podcast_id = arguments.get("podcast_id")
        if not podcast_id:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "podcast_id parameter is required"}, indent=2)
            )]
        result = await get_podcast_source_papers(podcast_id=podcast_id)
        return [TextContent(type="text", text=result)]
    
    elif name == "search_podcasts_by_topic":
        topic = arguments.get("topic")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        if not topic:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "topic parameter is required"}, indent=2)
            )]
        result = await search_podcasts_by_topic(topic=topic, limit=limit)
        return [TextContent(type="text", text=result)]
    
    # Cross-Component Tools (Phase 5)
    elif name == "find_related_content":
        paper_id = arguments.get("paper_id")
        podcast_id = arguments.get("podcast_id")
        process_id = arguments.get("process_id")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        result = await find_related_content(
            paper_id=paper_id,
            podcast_id=podcast_id,
            process_id=process_id,
            limit=limit
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "get_paper_visualizations":
        paper_id = arguments.get("paper_id")
        doi = arguments.get("doi")
        result = await get_paper_visualizations(paper_id=paper_id, doi=doi)
        return [TextContent(type="text", text=result)]
    
    elif name == "search_across_components":
        query = arguments.get("query")
        components = arguments.get("components")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        if not query:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "query parameter is required"}, indent=2)
            )]
        result = await search_across_components(query=query, components=components, limit=limit)
        return [TextContent(type="text", text=result)]
    
    # Vector Search Tools (Semantic Search)
    elif name == "search_semantic":
        query = arguments.get("query")
        content_types = arguments.get("content_types")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        distance_threshold = arguments.get("distance_threshold", 0.7)
        if not query:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "query parameter is required"}, indent=2)
            )]
        result = await search_semantic(
            query=query,
            content_types=content_types,
            limit=limit,
            distance_threshold=distance_threshold
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "find_similar_content":
        content_id = arguments.get("content_id")
        content_type = arguments.get("content_type")
        limit = arguments.get("limit", DEFAULT_QUERY_LIMIT)
        if not content_id or not content_type:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "content_id and content_type parameters are required"}, indent=2)
            )]
        result = await find_similar_content(
            content_id=content_id,
            content_type=content_type,
            limit=limit
        )
        return [TextContent(type="text", text=result)]
    
    # RAG Tools (Question Answering)
    elif name == "answer_with_rag":
        question = arguments.get("question")
        max_context_items = arguments.get("max_context_items", 5)
        content_types = arguments.get("content_types")
        include_sources = arguments.get("include_sources", True)
        if not question:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "question parameter is required"}, indent=2)
            )]
        result = await answer_with_rag(
            question=question,
            max_context_items=max_context_items,
            content_types=content_types,
            include_sources=include_sources
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "explain_concept":
        concept = arguments.get("concept")
        depth = arguments.get("depth", "intermediate")
        content_types = arguments.get("content_types")
        if not concept:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "concept parameter is required"}, indent=2)
            )]
        result = await explain_concept(
            concept=concept,
            depth=depth,
            content_types=content_types
        )
        return [TextContent(type="text", text=result)]
    
    elif name == "compare_concepts":
        concept1 = arguments.get("concept1")
        concept2 = arguments.get("concept2")
        content_types = arguments.get("content_types")
        if not concept1 or not concept2:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "concept1 and concept2 parameters are required"}, indent=2)
            )]
        result = await compare_concepts(
            concept1=concept1,
            concept2=concept2,
            content_types=content_types
        )
        return [TextContent(type="text", text=result)]
    
    else:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}, indent=2))]


async def main():
    """Main entry point for the MCP server."""
    if not MCP_AVAILABLE:
        logger.error("MCP SDK not available. Cannot start server.")
        sys.exit(1)
    
    logger.info(f"Starting {MCP_SERVER_NAME} v{MCP_SERVER_VERSION}")
    logger.info("MCP server running on stdio (for Cursor/Claude Desktop)")
    
    # Run server on stdio (standard input/output)
    # This allows Cursor and Claude Desktop to communicate with the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

