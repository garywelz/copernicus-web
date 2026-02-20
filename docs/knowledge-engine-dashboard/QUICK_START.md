# Knowledge Engine Dashboard - Quick Start

## Getting Started

### 1. Start the API Server

```bash
cd cloud-run-backend
source venv/bin/activate
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### 2. Configure Environment (Optional)

If your API is running on a different URL, create a `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start the Next.js Development Server

```bash
npm run dev
```

### 4. Access the Dashboard

Navigate to: `http://localhost:3000/knowledge-engine`

## Features Overview

### Knowledge Map
- Visualize relationships between papers and concepts
- Interactive graph with zoom and pan
- Filter by relationship types

### Search
- Semantic search across papers, podcasts, and processes
- Filter by content type
- View similarity scores

### Ask Questions
- Ask questions using RAG (Retrieval-Augmented Generation)
- Get answers with citations
- View source documents

### Statistics
- View system statistics
- Knowledge map metrics
- Content counts

## Troubleshooting

### "Failed to load knowledge map"
- Ensure API server is running at `http://localhost:8000`
- Check API endpoint: `GET /api/knowledge-map/graph`
- Verify CORS is configured correctly

### "Search failed"
- Check vector search endpoint is available
- Verify content types are configured
- Check API logs for errors

### "RAG not responding"
- Ensure RAG service is running
- Check LLM model availability
- Verify API endpoint: `GET /api/rag/answer`

## Next Steps

1. **Test Knowledge Map**: Load the knowledge map and explore relationships
2. **Try Search**: Search for papers, concepts, or processes
3. **Ask Questions**: Use RAG to answer questions about research
4. **View Statistics**: Check system metrics and content counts

## Support

For issues or questions, check:
- API documentation: `/docs` endpoint
- Component documentation: `docs/knowledge-engine-dashboard/README.md`
- Strategic planning: `docs/strategic/`

