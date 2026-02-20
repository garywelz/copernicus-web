# Knowledge Engine Dashboard

## Overview

The Knowledge Engine Dashboard is a unified web interface for exploring the CopernicusAI Knowledge Engine. It provides access to all major capabilities through an intuitive, tab-based interface.

## Access

Navigate to `/knowledge-engine` in your browser.

## Features

### 1. Knowledge Map 🗺️

Interactive visualization of the knowledge graph showing:
- **Papers**: Research papers as nodes
- **Concepts**: Extracted concepts as diamond-shaped nodes
- **Relationships**: Similarity, category, and citation connections

**Controls:**
- Adjust max papers (10-5000)
- Toggle concepts, similarity, and category relationships
- Reload, reset view, and clear highlights

**API Endpoint:** `GET /api/knowledge-map/graph`

### 2. Search 🔍

Semantic search across all content types:
- **Research Papers**: Search by title, abstract, authors
- **Podcasts**: Search by title, description, transcript
- **Processes**: Search GLMP, Math, Chemistry, Physics, CS processes

**Features:**
- Filter by content type
- Adjustable result limit
- Similarity scores displayed

**API Endpoint:** `GET /api/vector-search/semantic`

### 3. Ask Questions 💬

RAG (Retrieval-Augmented Generation) interface for question-answering:
- Ask questions about research, concepts, or processes
- Get answers with citations
- View source documents and similarity scores

**Features:**
- Example questions provided
- Adjustable context items (1-20)
- Citation tracking

**API Endpoint:** `GET /api/rag/answer`

### 4. Browse Content 📚

Browse all content in the knowledge base:
- Papers
- Podcasts
- Processes

**Status:** Coming soon - placeholder for future content browser

### 5. Statistics 📊

System statistics and metrics:
- Total papers, podcasts, processes, concepts
- Knowledge map statistics (nodes, edges)
- System information

**API Endpoint:** `GET /api/knowledge-map/stats`

## Configuration

### API Base URL

The dashboard uses the `NEXT_PUBLIC_API_URL` environment variable. If not set, it defaults to `http://localhost:8000`.

**For Development:**
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**For Production:**
```bash
# .env.production
NEXT_PUBLIC_API_URL=https://your-api-url.com
```

## Components

### Main Page
- **File:** `app/knowledge-engine/page.tsx`
- Tab-based navigation
- Renders appropriate component based on active tab

### Knowledge Map View
- **File:** `components/knowledge-engine/KnowledgeMapView.tsx`
- Cytoscape.js integration
- Dynamic loading to avoid SSR issues
- Interactive graph visualization

### Search Interface
- **File:** `components/knowledge-engine/SearchInterface.tsx`
- Unified search across all content types
- Content type filtering
- Result display with metadata

### RAG Interface
- **File:** `components/knowledge-engine/RAGInterface.tsx`
- Question-answering interface
- Citation display
- Example questions

### Content Browser
- **File:** `components/knowledge-engine/ContentBrowser.tsx`
- Placeholder for content browsing
- Ready for implementation

### Stats Dashboard
- **File:** `components/knowledge-engine/StatsDashboard.tsx`
- System statistics display
- Knowledge map metrics

## Dependencies

- `cytoscape` - Graph visualization
- `cytoscape-dagre` - Graph layout algorithm
- Next.js 15
- React 18
- Tailwind CSS

## Development

### Start Development Server

```bash
npm run dev
```

### Start API Server

```bash
cd cloud-run-backend
source venv/bin/activate
uvicorn main:app --reload
```

### Access Dashboard

Navigate to: `http://localhost:3000/knowledge-engine`

## Future Enhancements

1. **Content Browser**: Implement full content browsing with pagination
2. **Advanced Filters**: Add more filtering options for search
3. **Export Features**: Allow exporting knowledge maps and search results
4. **User Preferences**: Save user preferences and search history
5. **Collaboration**: Share knowledge maps and queries
6. **Mobile Responsiveness**: Optimize for mobile devices

## Troubleshooting

### Knowledge Map Not Loading

1. Check that API server is running at the configured URL
2. Verify API endpoint is accessible: `GET /api/knowledge-map/graph`
3. Check browser console for errors
4. Ensure Cytoscape.js is properly loaded (check network tab)

### Search Not Working

1. Verify vector search endpoint is available
2. Check API base URL configuration
3. Ensure content types are properly configured

### RAG Not Responding

1. Check RAG service is running
2. Verify LLM model is available
3. Check API endpoint: `GET /api/rag/answer`

## API Requirements

The dashboard requires the following API endpoints:

- `GET /api/knowledge-map/graph` - Get knowledge graph
- `GET /api/knowledge-map/stats` - Get statistics
- `GET /api/vector-search/semantic` - Semantic search
- `GET /api/rag/answer` - RAG question answering

Ensure all endpoints are properly configured and accessible.

