# Interactive Query Interface for Knowledge Map

## ✅ Completed Features

### 1. Query Service (`services/knowledge_map_queries.py`)

**Capabilities:**
- **Find Papers by Concept**: Search for papers mentioning specific mathematical concepts
- **Find Path**: Discover shortest path between two papers
- **Find Related Papers**: Get papers connected to a given paper
- **Search Papers**: Search by title or metadata
- **Get Cluster**: Find closely connected paper clusters

**Performance:**
- Indexed for fast queries
- BFS path finding algorithm
- Efficient graph traversal

### 2. API Endpoints (`/api/knowledge-map/query/`)

**Available Endpoints:**

#### Search Papers
```
GET /api/knowledge-map/query/search?q={query}&limit=20
```
Returns papers matching the search query.

#### Papers by Concept
```
GET /api/knowledge-map/query/papers-by-concept?concept={concept}&limit=20
```
Finds papers that mention a specific concept.

#### Find Path
```
GET /api/knowledge-map/query/path?source={paper_id}&target={paper_id}&max_depth=5
```
Finds shortest path between two papers.

#### Related Papers
```
GET /api/knowledge-map/query/related?paper_id={id}&depth=2&limit=20
```
Finds papers related to a given paper.

#### Get Cluster
```
GET /api/knowledge-map/query/cluster?paper_id={id}&min_cluster_size=3
```
Gets cluster of closely connected papers.

### 3. Interactive Visualization (`knowledge-map-interactive.html`)

**Features:**
- **Sidebar Query Panel**: Multiple query types in one interface
- **Search Papers**: Real-time paper search
- **Concept Search**: Find papers by mathematical concept
- **Path Visualization**: Visual path highlighting between papers
- **Related Papers**: Highlight related papers with one click
- **Cluster Analysis**: Visualize paper clusters
- **Interactive Highlighting**: Click results to highlight in graph
- **Graph Controls**: Load, reset, clear highlights

**Layout:**
- Left sidebar: Query interface
- Main area: Interactive graph visualization
- Bottom: Statistics panel

## 🎯 Usage Examples

### Example 1: Find Papers About "Topology"
1. Enter "topology" in "Papers by Concept" field
2. Click "Find Papers"
3. Results show papers mentioning topology
4. Click any result to highlight it in the graph

### Example 2: Find Path Between Papers
1. Get two paper IDs (from search or graph)
2. Enter source ID in "Path Source"
3. Enter target ID in "Path Target"
4. Click "Find Path"
5. Path is highlighted in red in the graph

### Example 3: Explore Related Papers
1. Enter a paper ID in "Related Papers" field
2. Set depth (how many relationship hops)
3. Click "Find Related"
4. All related papers are highlighted
5. Click any result to focus on it

### Example 4: Discover Clusters
1. Enter a seed paper ID
2. Click "Get Cluster"
3. See all papers in the same research cluster
4. Cluster is highlighted in the graph

## 📊 Query Performance

**Optimizations:**
- Indexed graph structure for O(1) node lookups
- Efficient BFS for path finding
- Limited depth traversal for related papers
- Cached graph structure

**Expected Performance:**
- Search: < 100ms
- Path finding: < 500ms (depending on depth)
- Related papers: < 200ms
- Cluster analysis: < 300ms

## 🔧 Integration

### With Existing Knowledge Map

The query service works with the knowledge map service:

```python
from services.knowledge_map_service import get_knowledge_map_service
from services.knowledge_map_queries import get_query_service

# Build or load knowledge map
km_service = get_knowledge_map_service()
await km_service.build_graph(max_papers=1000)

# Create query service
query_service = get_query_service(km_service)

# Use queries
papers = query_service.find_papers_by_concept("topology")
path = query_service.find_path(source_id, target_id)
related = query_service.find_related_papers(paper_id)
```

### With API

All queries are available via REST API:

```bash
# Search
curl "http://localhost:8000/api/knowledge-map/query/search?q=algebra"

# Find papers by concept
curl "http://localhost:8000/api/knowledge-map/query/papers-by-concept?concept=topology"

# Find path
curl "http://localhost:8000/api/knowledge-map/query/path?source=paper1&target=paper2"
```

## 🎨 Visualization Features

### Highlighting
- **Node Highlighting**: Selected papers/concepts highlighted in orange
- **Path Highlighting**: Path edges highlighted in red
- **Cluster Highlighting**: All cluster nodes highlighted together
- **Auto-zoom**: Graph automatically zooms to highlighted nodes

### Interaction
- **Click Results**: Click any result item to highlight in graph
- **Node Click**: Click nodes in graph for details (can be extended)
- **Pan & Zoom**: Standard Cytoscape.js interactions
- **Reset View**: Return to full graph view

## 📋 Next Enhancements

### Potential Additions:
1. **Node Details Panel**: Show paper details when clicked
2. **Export Results**: Export query results as JSON/CSV
3. **Save Queries**: Save favorite queries
4. **Query History**: Track recent queries
5. **Advanced Filters**: Filter by category, date, etc.
6. **Multi-hop Queries**: Find papers N hops away
7. **Concept Evolution**: Show how concepts connect over time

## 🚀 Getting Started

1. **Start API Server:**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. **Open Visualization:**
   - Open `knowledge-map-interactive.html` in browser
   - Or serve via FastAPI static files

3. **Load Graph:**
   - Set max papers (start with 500 for testing)
   - Click "Load Graph"
   - Wait for graph to load

4. **Try Queries:**
   - Use sidebar to try different query types
   - Results appear in result panels
   - Click results to highlight in graph

## 📝 Files Created

1. **`services/knowledge_map_queries.py`** - Query service implementation
2. **`endpoints/knowledge_map/routes.py`** - Enhanced with query endpoints
3. **`knowledge-map-interactive.html`** - Interactive visualization interface

## ✅ Status

All interactive query features are **complete and ready to use**!

The interface is fully functional and waiting for the full dataset build to complete.

