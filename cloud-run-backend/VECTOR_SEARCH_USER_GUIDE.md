# Vector Search & RAG User Guide

This guide shows you how to use the vector search and RAG capabilities in CopernicusAI.

## Quick Start

### Option 1: Interactive Demo (Recommended for First Time)

Run the interactive demo to see all features in action:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/interactive_vector_search.py
```

This will walk you through:
- Semantic search across all content
- Content type filtering
- Similarity search
- RAG question answering

### Option 2: Quick Command-Line Search

For quick searches from the command line:

```bash
# Basic semantic search
python3 scripts/quick_search.py "DNA replication"

# Search only papers
python3 scripts/quick_search.py "metabolic pathways" --type papers

# Search only GLMP processes
python3 scripts/quick_search.py "cell division" --type glmp

# Search multiple types
python3 scripts/quick_search.py "biology" --type papers --type glmp

# Get more results
python3 scripts/quick_search.py "quantum mechanics" --limit 10

# Ask a question with RAG
python3 scripts/quick_search.py "What is DNA replication?" --rag

# Find similar content
python3 scripts/quick_search.py --similar "bacillus-bacillus_biofilm_formation" --similar-type glmp
```

## Using in Your Code

### Semantic Search

```python
import asyncio
from mcp_server.tools.vector_search import search_semantic

async def search():
    # Search all content types
    results = await search_semantic("DNA replication", limit=5)
    
    # Search only papers
    results = await search_semantic("metabolic pathways", 
                                   content_types=["papers"], 
                                   limit=10)
    
    # Search multiple types
    results = await search_semantic("biology", 
                                   content_types=["papers", "glmp"], 
                                   limit=5)

asyncio.run(search())
```

### Similarity Search

```python
import asyncio
from mcp_server.tools.vector_search import find_similar_content

async def find_similar():
    # Find content similar to a specific paper
    results = await find_similar_content(
        content_id="your-paper-id",
        content_type="paper",
        limit=5
    )
    
    # Find content similar to a GLMP process
    results = await find_similar_content(
        content_id="bacillus-bacillus_biofilm_formation",
        content_type="glmp",
        limit=5
    )

asyncio.run(find_similar())
```

### RAG Question Answering

```python
import asyncio
from services.rag_service import get_rag_service

async def ask_question():
    rag_service = get_rag_service()
    
    result = await rag_service.answer_question(
        question="What is DNA replication?",
        max_context_items=5,
        content_types=["papers", "glmp", "podcasts"],
        include_sources=True
    )
    
    print(f"Answer: {result['answer']}")
    print(f"Sources: {len(result['citations'])} citations")

asyncio.run(ask_question())
```

## Understanding Results

### Search Results Format

```json
{
  "query": "DNA replication",
  "content_types_searched": ["papers", "glmp", "podcasts"],
  "papers": [
    {
      "paper_id": "...",
      "title": "...",
      "abstract": "...",
      "similarity_score": 0.85
    }
  ],
  "glmp_processes": [...],
  "podcasts": [...],
  "counts": {
    "papers": 5,
    "glmp_processes": 5,
    "podcasts": 5,
    "total": 15
  }
}
```

### RAG Results Format

```json
{
  "question": "What is DNA replication?",
  "answer": "DNA replication is... [with citations]",
  "citations": [
    {
      "number": 1,
      "type": "paper",
      "title": "...",
      "paper_id": "...",
      "similarity_score": 0.92
    }
  ],
  "metadata": {
    "context_items_used": 15,
    "retrieval_method": "vector_search",
    "model": "gemini-2.0-flash-exp"
  }
}
```

## Content Types

- **papers**: Research papers from arXiv and other sources
- **glmp**: GLMP biological/chemical processes
- **podcasts**: AI-generated podcast briefings

## Tips

1. **Similarity Scores**: Range from 0.0 to 1.0, where higher = more similar
   - 0.9+ = Very similar
   - 0.7-0.9 = Similar
   - 0.5-0.7 = Somewhat related
   - <0.5 = Less related

2. **Query Quality**: More specific queries tend to give better results
   - Good: "DNA replication initiation in E. coli"
   - Less specific: "biology"

3. **Content Type Filtering**: Use when you know what type of content you want
   - Faster queries
   - More focused results

4. **RAG Questions**: Ask natural language questions
   - "What is X?"
   - "Explain Y"
   - "How does Z work?"

## Troubleshooting

### No Results Found

- Try a broader query
- Check if content exists in the knowledge base
- Verify embeddings are generated (should be automatic)

### RAG Not Working

- Check that Vertex AI is configured
- Verify GCP credentials are set
- Check that `gemini-2.0-flash-exp` model is available

### Low Similarity Scores

- This is normal for very specific queries
- Try rephrasing your query
- Use content type filtering to narrow results

## Next Steps

- Explore the MCP tools in `mcp_server/tools/vector_search.py`
- Check the RAG service in `services/rag_service.py`
- Review test examples in `scripts/test_vector_search.py`

