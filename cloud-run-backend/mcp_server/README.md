# CopernicusAI Knowledge Engine - MCP Server

Model Context Protocol (MCP) server for the CopernicusAI Knowledge Engine.

## Overview

This MCP server exposes all knowledge engine components as queryable tools for AI assistants (Cursor, Claude Desktop, etc.), enabling direct access to:

- Research Paper Metadata Database
- GLMP (Genome Logic Modeling Project) processes
- CopernicusAI Podcasts
- Cross-component relationships

## Status

**✅ All Core Tools Implemented (15 tools)**

- Phase 1: Foundation ✅
- Phase 2: Research Paper Tools (4 tools) ✅
- Phase 3: GLMP Tools (4 tools) ✅
- Phase 4: Podcast Tools (4 tools) ✅
- Phase 5: Cross-Component Tools (3 tools) ✅

## Installation

```bash
cd cloud-run-backend
pip install -r mcp_server/requirements.txt
```

## Usage

### Running the Server

```bash
python -m mcp_server.server
```

The server runs on stdio (standard input/output) for communication with MCP clients like Cursor and Claude Desktop.

### Configuration

Set environment variables (or use defaults in `config.py`):

- `GCP_PROJECT_ID` - Google Cloud Project ID
- `FIRESTORE_DATABASE` - Firestore database name
- `GCP_AUDIO_BUCKET` - GCS bucket name
- `GLMP_BUCKET_PATH` - Path to GLMP files in GCS

## Available Tools

### Research Paper Tools (4)
- `query_research_papers` - Search papers by query, discipline, keywords
- `get_paper_by_id` - Get full paper metadata by ID or DOI
- `get_paper_citations` - Find papers that cite a specified paper
- `search_papers_by_entity` - Search papers by entity (gene, protein, etc.)

### GLMP Tools (4)
- `list_glmp_processes` - List biological processes by category
- `get_glmp_process` - Get full process with Mermaid diagram
- `search_glmp_by_entity` - Search processes by entity
- `get_glmp_categories` - Get all categories with counts

### Podcast Tools (4)
- `list_podcasts` - List podcasts by discipline or subscriber
- `get_podcast_details` - Get full podcast metadata
- `get_podcast_source_papers` - Get source papers for a podcast
- `search_podcasts_by_topic` - Search podcasts by topic

### Cross-Component Tools (3)
- `find_related_content` - Find related content across all components
- `get_paper_visualizations` - Get GLMP processes related to a paper
- `search_across_components` - Unified search across all components

## Integration with Cursor/Claude Desktop

1. Configure MCP server in Cursor settings
2. Point to: `python -m mcp_server.server`
3. All 15 tools will be available for AI assistant queries

## Architecture

```
mcp_server/
├── server.py              # Main MCP server
├── config.py              # Configuration
├── tools/
│   ├── papers.py          # Research paper tools
│   ├── glmp.py            # GLMP process tools
│   ├── podcasts.py        # Podcast tools
│   └── cross_component.py # Cross-component tools
├── utils/
│   ├── firestore_client.py # Firestore utilities
│   └── gcs_client.py      # GCS utilities
└── models/                # Data models (future)
```

## Development Status

**Current:** All core tools implemented and ready for testing  
**Next:** Phase 6 (Testing & Validation), Phase 7 (Deployment)

See `CHECKPOINTS.md` for detailed progress tracking.

## License

Part of the CopernicusAI Knowledge Engine project.



