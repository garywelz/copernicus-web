# Mathematics Knowledge Map Guide

## Overview

The Mathematics Knowledge Map is an interactive visualization of relationships between:
- **Papers**: Research papers from arXiv
- **Concepts**: Mathematical concepts extracted from papers
- **Relationships**: Citations, similarity, category connections

## Features

✅ **Relationship Extraction**
- Category-based relationships (papers in same category)
- Similarity relationships (vector-based semantic similarity)
- Concept extraction (mathematical concepts from papers)

✅ **Graph Structure**
- Nodes: Papers and Concepts
- Edges: Various relationship types
- Metadata: Titles, categories, arXiv IDs

✅ **Visualization**
- Interactive Cytoscape.js visualization
- Filterable by relationship type
- Zoomable and pannable

## Usage

### 1. Build Knowledge Map

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate

# Build with default settings (all papers)
python scripts/build_knowledge_map.py

# Build with limited papers (faster for testing)
python scripts/build_knowledge_map.py --max-papers 500

# Build without concepts (papers only)
python scripts/build_knowledge_map.py --no-concepts

# Export in different formats
python scripts/build_knowledge_map.py --format d3 --output knowledge_map_d3.json
```

### 2. Access via API

```bash
# Get full graph
curl "http://localhost:8000/api/knowledge-map/graph?max_papers=500&format=cytoscape"

# Get subgraph around a paper
curl "http://localhost:8000/api/knowledge-map/subgraph/{paper_id}?depth=2&max_nodes=50"

# Get statistics
curl "http://localhost:8000/api/knowledge-map/stats"
```

### 3. Visualize in Browser

1. Start the FastAPI server:
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. Open `knowledge-map-visualization.html` in your browser

3. Adjust settings:
   - Max Papers: Limit number of papers (10-5000)
   - Include Concepts: Toggle concept nodes
   - Include Similarity: Toggle similarity relationships
   - Include Categories: Toggle category relationships

4. Click "Load Graph" to visualize

## Graph Structure

### Nodes

**Paper Nodes:**
- Type: `paper`
- Color: Blue (#3498db)
- Data: title, categories, arxiv_id, doi

**Concept Nodes:**
- Type: `concept`
- Color: Red (#e74c3c)
- Shape: Diamond
- Data: concept name, paper count

### Edges

**Relationship Types:**
- `same_category`: Papers in same arXiv category (gray, low opacity)
- `similar_to`: Papers with similar embeddings (blue)
- `cites`: Citation relationships (red)
- `mentions`: Paper mentions concept (gray)

## Performance

**Recommended Settings:**
- **Small demo**: 100-200 papers
- **Medium**: 500-1000 papers
- **Full**: 5000+ papers (may be slow)

**Optimization Tips:**
- Disable concepts for faster builds
- Use category relationships only for large graphs
- Limit similarity relationships to reduce edges

## Next Steps

1. **Add Citation Data**: Integrate with Semantic Scholar API for real citations
2. **LLM Concept Extraction**: Use Gemini to extract more detailed concepts
3. **Author Networks**: Add author nodes and co-authorship edges
4. **Temporal Analysis**: Show how concepts evolve over time
5. **Interactive Queries**: Search and highlight specific papers/concepts

## Files

- **Service**: `cloud-run-backend/services/knowledge_map_service.py`
- **API**: `cloud-run-backend/endpoints/knowledge_map/routes.py`
- **Builder Script**: `cloud-run-backend/scripts/build_knowledge_map.py`
- **Visualization**: `knowledge-map-visualization.html`

