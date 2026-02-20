# Knowledge Map Enhancements

## ✅ Completed Enhancements

### 1. Semantic Scholar Citation Integration
**Service:** `services/semantic_scholar_service.py`

- Fetches citation data from Semantic Scholar API
- Supports both arXiv ID and DOI lookups
- Extracts citations and references
- Rate limiting for API compliance

**Usage:**
```python
from services.semantic_scholar_service import get_semantic_scholar_service

service = get_semantic_scholar_service()
citation_data = await service.get_citations_batch(papers)
```

**Integration:**
- Added to `knowledge_map_service.extract_citation_relationships()`
- Can be enabled with `--use-semantic-scholar` flag
- Limits API calls with `--max-citations` parameter

### 2. LLM-Based Concept Extraction
**Enhancement:** Enhanced `extract_concepts_from_papers()` method

- Uses Gemini 2.0 Flash for concept extraction
- Extracts 3-5 key mathematical concepts per paper
- More detailed than category/keyword extraction
- Processes abstracts and titles

**Usage:**
```python
concepts = await service.extract_concepts_from_papers(
    papers,
    use_llm=True,
    max_papers_for_llm=100
)
```

**Integration:**
- Enabled with `--use-llm-concepts` flag
- Can be combined with basic extraction
- Limits processing with `--max-citations` parameter

### 3. Author Network Extraction
**Feature:** `extract_author_relationships()` method

- Extracts co-authorship relationships
- Connects papers with shared authors
- Creates author collaboration network
- Weighted by number of shared authors

**Usage:**
- Enabled with `include_authors=True` in `build_graph()`
- Creates `co_author` relationship edges
- Metadata includes author name

### 4. Enhancement Script
**Script:** `scripts/enhance_knowledge_map.py`

- Enhances existing knowledge maps
- Adds citations without rebuilding entire graph
- Adds LLM concepts incrementally
- Preserves existing relationships

**Usage:**
```bash
python scripts/enhance_knowledge_map.py \
    /tmp/knowledge_map_full.json \
    --output /tmp/knowledge_map_enhanced.json \
    --use-semantic-scholar \
    --use-llm-concepts \
    --max-papers 500
```

## 📊 Current Status

### Full Dataset Build (12,000 papers)
- **Status:** In Progress
- **Progress:**
  - ✅ Fetched 12,000 papers
  - ✅ Extracted 14,792 category relationships
  - 🔄 Processing similarity relationships (in progress)
  - ⏳ Concept extraction (pending)
  - ⏳ Graph export (pending)

### Expected Results
- **Nodes:** ~12,000+ papers + ~500+ concepts
- **Edges:** ~50,000+ relationships
- **File Size:** ~10-20 MB
- **Build Time:** ~30-60 minutes

## 🚀 Next Steps

### 1. Complete Full Dataset Build
Wait for current build to complete, then:
```bash
# Check results
python3 -c "
import json
with open('/tmp/knowledge_map_full.json') as f:
    data = json.load(f)
    print(f'Nodes: {len(data[\"nodes\"])}')
    print(f'Edges: {len(data[\"edges\"])}')
"
```

### 2. Enhance with Citations (Optional)
```bash
python scripts/enhance_knowledge_map.py \
    /tmp/knowledge_map_full.json \
    --output /tmp/knowledge_map_with_citations.json \
    --use-semantic-scholar \
    --max-papers 1000
```

### 3. Enhance with LLM Concepts (Optional)
```bash
python scripts/enhance_knowledge_map.py \
    /tmp/knowledge_map_full.json \
    --output /tmp/knowledge_map_with_concepts.json \
    --use-llm-concepts \
    --max-papers 500
```

### 4. Add Author Networks
Rebuild with author relationships:
```bash
# Update build script to include authors
python scripts/build_knowledge_map.py \
    --max-papers 12000 \
    --include-authors
```

### 5. Interactive Queries
Create query interface for:
- Find papers by concept
- Find path between papers
- Find related papers
- Cluster analysis

## 📋 API Endpoints

All endpoints support new features:

```bash
# Get graph with Semantic Scholar citations
GET /api/knowledge-map/graph?use_semantic_scholar=true&max_citations=500

# Get graph with LLM concepts
GET /api/knowledge-map/graph?use_llm_concepts=true&max_citations=100

# Get subgraph around a paper
GET /api/knowledge-map/subgraph/{paper_id}?depth=2
```

## 🔧 Configuration

### Environment Variables
- `SEMANTIC_SCHOLAR_API_KEY`: Optional API key for higher rate limits
- `GCP_PROJECT_ID`: For Vertex AI (LLM)
- `GCP_REGION`: For Vertex AI

### Rate Limits
- **Semantic Scholar (free):** 100 requests/5 minutes
- **Semantic Scholar (with key):** 5000 requests/5 minutes
- **Vertex AI:** Varies by quota

## 📈 Performance Tips

1. **For Large Datasets:**
   - Use `--max-citations` to limit API calls
   - Process in batches
   - Cache results

2. **For Faster Builds:**
   - Disable similarity relationships for very large graphs
   - Use category relationships only
   - Limit concept extraction

3. **For Better Quality:**
   - Enable Semantic Scholar for real citations
   - Use LLM for detailed concepts
   - Include author networks

## 🎯 Future Enhancements

1. **Temporal Analysis**
   - Show concept evolution over time
   - Citation network growth
   - Author collaboration trends

2. **Advanced Queries**
   - Find shortest path between concepts
   - Identify key papers (PageRank)
   - Community detection

3. **Visualization Improvements**
   - 3D graph visualization
   - Time-lapse animations
   - Interactive filtering

4. **Integration**
   - Link to math processes
   - Connect to podcasts
   - Cross-domain relationships

