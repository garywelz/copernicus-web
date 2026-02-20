# Knowledge Map Filtering - Backend Support Required

## Current Status

The Knowledge Map frontend UI has been enhanced with comprehensive filtering options:
- Content type selection (Papers, Processes, Videos, Podcasts)
- Discipline filters (Biology, Chemistry, Physics, Mathematics, Computer Science, Interdisciplinary)
- Source filters (PubMed, arXiv, NASA ADS, Crossref, YouTube, RSS)
- Date range filtering
- Keyword search

**However, the backend API does not yet support these filtering parameters.**

## Backend API Current Parameters

The `/api/knowledge-map/graph` endpoint currently only accepts:
- `max_papers` - Maximum number of papers to include
- `include_concepts` - Include concept nodes
- `include_similarity` - Include similarity relationships
- `include_categories` - Include category relationships
- `format` - Output format (cytoscape, d3, or raw)
- `force_rebuild` - Force rebuild even if graph exists

## What's Happening

When users apply filters in the frontend, the parameters are sent to the backend API:
- `content_types` (multiple values)
- `disciplines` (comma-separated list)
- `sources` (comma-separated list)
- `date_start` / `date_end`
- `keyword`

The backend ignores these parameters and returns the cached/default graph.

## Next Steps

The backend API (`/cloud-run-backend/endpoints/knowledge_map/routes.py`) needs to be updated to:

1. Accept the new filtering parameters
2. Pass them to the `build_graph` method or implement filtering logic
3. Either filter the cached graph or rebuild with the specified filters

This is a backend development task, not a frontend issue.
