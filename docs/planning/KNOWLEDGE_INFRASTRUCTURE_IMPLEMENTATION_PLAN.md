# Complete Knowledge Infrastructure Implementation Plan
## Vector Search + Knowledge Graph + RAG

**Date:** December 24, 2024  
**Project:** CopernicusAI Knowledge Engine  
**Estimated Timeline:** 4-6 months (phased implementation)

---

## Executive Summary

This plan outlines the implementation of three complementary technologies that will create a complete, state-of-the-art knowledge infrastructure:

1. **Vector Search** - Semantic similarity search across all components
2. **Knowledge Graph** - Explicit relationship modeling and graph queries
3. **RAG (Retrieval-Augmented Generation)** - AI responses grounded in knowledge base

Together, these will enable:
- **Semantic discovery** - Find conceptually similar content across modalities
- **Relationship exploration** - Navigate connections between papers, processes, podcasts
- **Grounded AI responses** - Accurate answers backed by your knowledge base
- **Advanced queries** - "Find papers related to processes that use ATP"

---

## Part 1: Vector Search Implementation

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────┐
│         Existing Components             │
│  - Research Papers (Firestore)          │
│  - GLMP Processes (GCS JSON)            │
│  - Podcasts (Firestore)                 │
└──────────────┬──────────────────────────┘
               │
               │ Embedding Generation
               │
┌──────────────▼──────────────────────────┐
│     Vertex AI Embeddings Service         │
│  - text-embedding-004 (text)             │
│  - multimodalembedding (text+images)    │
└──────────────┬──────────────────────────┘
               │
               │ Store Embeddings
               │
┌──────────────▼──────────────────────────┐
│      Vertex AI Vector Search             │
│  - Index: copernicusai-knowledge         │
│  - Hybrid search (keyword + vector)       │
└──────────────┬──────────────────────────┘
               │
               │ Query Interface
               │
┌──────────────▼──────────────────────────┐
│         MCP Server + API                │
│  - search_semantic() tool                │
│  - find_similar_content() tool          │
└──────────────────────────────────────────┘
```

### 1.2 Technology Stack

**Embedding Model:**
- **Primary:** Vertex AI `text-embedding-004` (768 dimensions)
- **Multi-modal:** Vertex AI `multimodalembedding` (for diagrams + text)
- **Why:** Native GCP integration, high quality, managed service

**Vector Database:**
- **Primary:** Vertex AI Vector Search (managed, scales automatically)
- **Alternative:** Weaviate (if self-hosting needed)
- **Why:** Fully managed, integrates with existing GCP infrastructure

**Hybrid Search:**
- **Keyword:** Existing Firestore queries
- **Vector:** Vertex AI Vector Search
- **Combination:** Reciprocal Rank Fusion (RRF) or weighted combination

### 1.3 Implementation Phases

#### Phase 1.1: Embedding Generation Pipeline (Week 1-2)

**Objective:** Generate embeddings for all existing content

**Tasks:**

1. **Create Embedding Service Module**
   ```python
   # cloud-run-backend/services/embedding_service.py
   from google.cloud import aiplatform
   from vertexai.preview.language_models import TextEmbeddingModel
   
   class EmbeddingService:
       def __init__(self):
           self.text_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
           
       def embed_text(self, text: str) -> list[float]:
           """Generate embedding for text"""
           embeddings = self.text_model.get_embeddings([text])
           return embeddings[0].values
           
       def embed_batch(self, texts: list[str]) -> list[list[float]]:
           """Batch embedding generation"""
           embeddings = self.text_model.get_embeddings(texts)
           return [e.values for e in embeddings]
   ```

2. **Create Embedding Pipeline**
   ```python
   # cloud-run-backend/services/vector_indexing_pipeline.py
   async def index_research_papers():
       """Generate embeddings for all research papers"""
       papers = get_all_papers_from_firestore()
       
       texts = []
       metadata = []
       for paper in papers:
           # Combine title, abstract, keywords
           text = f"{paper['title']}\n{paper.get('abstract', '')}\n{' '.join(paper.get('keywords', []))}"
           texts.append(text)
           metadata.append({
               'id': paper['id'],
               'type': 'paper',
               'title': paper['title'],
               'doi': paper.get('doi'),
               'discipline': paper.get('discipline')
           })
       
       # Batch generate embeddings
       embeddings = embedding_service.embed_batch(texts)
       
       # Upload to Vector Search
       upload_to_vector_search(embeddings, metadata)
   ```

3. **GLMP Process Embedding**
   ```python
   async def index_glmp_processes():
       """Generate embeddings for GLMP processes"""
       processes = get_all_glmp_from_gcs()
       
       texts = []
       metadata = []
       for process in processes:
           # Combine title, description, entities, Mermaid text
           text = f"{process['title']}\n{process.get('description', '')}\n"
           text += f"Entities: {', '.join(process.get('entities', []))}\n"
           text += f"Mermaid: {process.get('mermaid', '')[:500]}"  # First 500 chars
           texts.append(text)
           metadata.append({
               'id': process['id'],
               'type': 'glmp_process',
               'title': process['title'],
               'category': process.get('category')
           })
       
       embeddings = embedding_service.embed_batch(texts)
       upload_to_vector_search(embeddings, metadata)
   ```

4. **Podcast Embedding**
   ```python
   async def index_podcasts():
       """Generate embeddings for podcasts"""
       podcasts = get_all_podcasts_from_firestore()
       
       texts = []
       metadata = []
       for podcast in podcasts:
           # Combine title, description, transcript
           text = f"{podcast['title']}\n{podcast.get('description', '')}\n"
           if podcast.get('transcript'):
               text += podcast['transcript'][:1000]  # First 1000 chars
           texts.append(text)
           metadata.append({
               'id': podcast['id'],
               'type': 'podcast',
               'title': podcast['title'],
               'discipline': podcast.get('discipline')
           })
       
       embeddings = embedding_service.embed_batch(texts)
       upload_to_vector_search(embeddings, metadata)
   ```

**Deliverables:**
- Embedding service module
- Batch indexing scripts
- Initial index of all existing content (papers, GLMP, podcasts)

#### Phase 1.2: Vector Search Index Setup (Week 2-3)

**Objective:** Create and configure Vertex AI Vector Search index

**Tasks:**

1. **Create Vector Search Index**
   ```python
   # cloud-run-backend/services/vector_search_setup.py
   from google.cloud import aiplatform
   from google.cloud.aiplatform import vector_search
   
   def create_vector_index():
       """Create Vertex AI Vector Search index"""
       index = aiplatform.MatchingEngineIndex.create(
           display_name="copernicusai-knowledge-index",
           description="Vector search index for all knowledge components",
           embedding_dim=768,  # text-embedding-004 dimension
           distance_measure_type="DOT_PRODUCT",
           index_update_method="STREAMING"
       )
       return index
   ```

2. **Index Configuration**
   - **Index Name:** `copernicusai-knowledge-index`
   - **Embedding Dimension:** 768 (text-embedding-004)
   - **Distance Metric:** Dot Product (for cosine similarity)
   - **Update Method:** Streaming (for real-time updates)

3. **Metadata Schema**
   ```json
   {
     "id": "string",
     "type": "paper|glmp_process|podcast",
     "title": "string",
     "discipline": "string",
     "category": "string",
     "doi": "string",
     "source_id": "string"  // Original ID in Firestore/GCS
   }
   ```

**Deliverables:**
- Vector Search index created
- Metadata schema defined
- Indexing pipeline tested

#### Phase 1.3: Query Interface (Week 3-4)

**Objective:** Add vector search to MCP server and API

**Tasks:**

1. **MCP Tool: Semantic Search**
   ```python
   # cloud-run-backend/mcp_server/tools/vector_search.py
   async def search_semantic(
       query: str,
       component_types: list[str] = None,
       limit: int = 10
   ) -> str:
       """Semantic search across all components"""
       # Generate query embedding
       query_embedding = embedding_service.embed_text(query)
       
       # Search vector index
       results = vector_search.find_neighbors(
           index_name="copernicusai-knowledge-index",
           query_embedding=query_embedding,
           num_neighbors=limit,
           filter={"type": {"$in": component_types}} if component_types else None
       )
       
       # Fetch full documents from source
       full_results = []
       for result in results:
           doc = fetch_document_by_id(result['id'], result['type'])
           full_results.append({
               'id': doc['id'],
               'type': result['type'],
               'title': doc['title'],
               'similarity_score': result['distance'],
               'metadata': doc
           })
       
       return json.dumps({'results': full_results, 'count': len(full_results)})
   ```

2. **MCP Tool: Find Similar Content**
   ```python
   async def find_similar_content(
       content_id: str,
       content_type: str,
       limit: int = 10
   ) -> str:
       """Find similar content to a given item"""
       # Get embedding for source content
       source_doc = fetch_document_by_id(content_id, content_type)
       source_text = extract_text_for_embedding(source_doc)
       source_embedding = embedding_service.embed_text(source_text)
       
       # Find similar
       results = vector_search.find_neighbors(
           index_name="copernicusai-knowledge-index",
           query_embedding=source_embedding,
           num_neighbors=limit,
           filter={"id": {"$ne": content_id}}  # Exclude self
       )
       
       return format_results(results)
   ```

3. **Hybrid Search (Keyword + Vector)**
   ```python
   async def hybrid_search(
       query: str,
       limit: int = 10
   ) -> str:
       """Combine keyword and vector search"""
       # Keyword search (existing Firestore)
       keyword_results = await query_research_papers(query=query, limit=limit)
       
       # Vector search
       vector_results = await search_semantic(query=query, limit=limit)
       
       # Combine using Reciprocal Rank Fusion
       combined = reciprocal_rank_fusion(keyword_results, vector_results)
       
       return json.dumps({'results': combined[:limit]})
   ```

**Deliverables:**
- MCP tools for semantic search
- Hybrid search implementation
- API endpoints for vector search

#### Phase 1.4: Real-Time Updates (Week 4-5)

**Objective:** Automatically update embeddings when content changes

**Tasks:**

1. **Firestore Triggers**
   ```python
   # cloud-functions/update_embeddings_trigger.py
   @functions_framework.http
   def on_paper_updated(data, context):
       """Triggered when paper is updated in Firestore"""
       paper_id = context.resource.split('/')[-1]
       paper = get_paper_from_firestore(paper_id)
       
       # Generate new embedding
       text = f"{paper['title']}\n{paper.get('abstract', '')}"
       embedding = embedding_service.embed_text(text)
       
       # Update vector index
       vector_search.upsert(
           index_name="copernicusai-knowledge-index",
           id=paper_id,
           embedding=embedding,
           metadata={'type': 'paper', 'title': paper['title'], ...}
       )
   ```

2. **GCS Triggers for GLMP**
   ```python
   @functions_framework.http
   def on_glmp_updated(data, context):
       """Triggered when GLMP file is updated in GCS"""
       file_path = data['name']
       process = get_glmp_from_gcs(file_path)
       
       # Generate embedding and update index
       ...
   ```

**Deliverables:**
- Cloud Functions for automatic updates
- Real-time embedding synchronization

---

## Part 2: Knowledge Graph Implementation

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────┐
│         Data Sources                    │
│  - Research Papers (Firestore)          │
│  - GLMP Processes (GCS)                │
│  - Podcasts (Firestore)                 │
└──────────────┬──────────────────────────┘
               │
               │ Extract Relationships
               │
┌──────────────▼──────────────────────────┐
│     Relationship Extraction Service      │
│  - Entity co-occurrence                 │
│  - Citation relationships               │
│  - Process-paper links                  │
│  - Entity relationships                 │
└──────────────┬──────────────────────────┘
               │
               │ Graph Data
               │
┌──────────────▼──────────────────────────┐
│         Neo4j Graph Database            │
│  - Nodes: Papers, Processes, Podcasts,  │
│           Entities, Authors             │
│  - Relationships: CITES, USES,          │
│                    MENTIONS, RELATED_TO  │
└──────────────┬──────────────────────────┘
               │
               │ Graph Queries
               │
┌──────────────▼──────────────────────────┐
│         MCP Server + API                │
│  - find_related_paths() tool            │
│  - get_entity_network() tool            │
│  - discover_connections() tool          │
└──────────────────────────────────────────┘
```

### 2.2 Technology Stack

**Graph Database:**
- **Primary:** Neo4j Aura (managed cloud service)
- **Alternative:** Amazon Neptune (if AWS preferred)
- **Why:** Most mature graph database, excellent tooling, Cypher query language

**Graph Client:**
- **Python:** `neo4j` driver
- **Integration:** FastAPI endpoints, MCP tools

### 2.3 Graph Schema Design

#### Node Types:

1. **Paper**
   - Properties: `id`, `title`, `doi`, `abstract`, `discipline`, `year`
   - Labels: `Paper`, `{Discipline}` (e.g., `Biology`, `Chemistry`)

2. **GLMP_Process**
   - Properties: `id`, `title`, `category`, `description`
   - Labels: `GLMP_Process`, `{Category}` (e.g., `DNA_Repair`, `Metabolism`)

3. **Podcast**
   - Properties: `id`, `title`, `discipline`, `description`
   - Labels: `Podcast`, `{Discipline}`

4. **Entity**
   - Properties: `id`, `name`, `type` (gene, protein, chemical, etc.)
   - Labels: `Entity`, `{Type}` (e.g., `Gene`, `Protein`, `Chemical`)

5. **Author**
   - Properties: `id`, `name`, `affiliation`
   - Labels: `Author`

#### Relationship Types:

1. **CITES** - Paper → Paper
   - Properties: `year`, `context`
   
2. **USES** - GLMP_Process → Entity
   - Properties: `role` (input, output, catalyst, etc.)
   
3. **MENTIONS** - Paper → Entity
   - Properties: `frequency`, `context`
   
4. **VISUALIZES** - GLMP_Process → Paper
   - Properties: `version`, `created_date`
   
5. **SOURCES** - Podcast → Paper
   - Properties: `order`, `relevance`
   
6. **RELATED_TO** - Generic relationship
   - Properties: `strength`, `type` (semantic, structural, etc.)
   
7. **AUTHORED_BY** - Paper → Author
   - Properties: `order`

### 2.4 Implementation Phases

#### Phase 2.1: Neo4j Setup & Schema (Week 5-6)

**Objective:** Set up Neo4j database and define schema

**Tasks:**

1. **Neo4j Aura Setup**
   - Create Neo4j Aura instance
   - Configure connection (URI, username, password)
   - Store credentials in GCP Secret Manager

2. **Graph Client Module**
   ```python
   # cloud-run-backend/services/graph_client.py
   from neo4j import GraphDatabase
   import os
   from google.cloud import secretmanager
   
   class GraphService:
       def __init__(self):
           # Get credentials from Secret Manager
           client = secretmanager.SecretManagerServiceClient()
           uri = client.access_secret_version(
               name="projects/regal-scholar-453620-r7/secrets/neo4j-uri/versions/latest"
           ).payload.data.decode('UTF-8')
           username = ...
           password = ...
           
           self.driver = GraphDatabase.driver(uri, auth=(username, password))
       
       def close(self):
           self.driver.close()
       
       def execute_query(self, query: str, parameters: dict = None):
           with self.driver.session() as session:
               return session.run(query, parameters or {})
   ```

3. **Schema Constraints**
   ```cypher
   // Create constraints for uniqueness
   CREATE CONSTRAINT paper_id IF NOT EXISTS
   FOR (p:Paper) REQUIRE p.id IS UNIQUE;
   
   CREATE CONSTRAINT process_id IF NOT EXISTS
   FOR (p:GLMP_Process) REQUIRE p.id IS UNIQUE;
   
   CREATE CONSTRAINT entity_id IF NOT EXISTS
   FOR (e:Entity) REQUIRE e.id IS UNIQUE;
   
   // Create indexes for performance
   CREATE INDEX paper_title IF NOT EXISTS
   FOR (p:Paper) ON (p.title);
   
   CREATE INDEX entity_name IF NOT EXISTS
   FOR (e:Entity) ON (e.name);
   ```

**Deliverables:**
- Neo4j instance running
- Graph client module
- Schema constraints and indexes

#### Phase 2.2: Relationship Extraction (Week 6-7)

**Objective:** Extract relationships from existing data

**Tasks:**

1. **Citation Relationships**
   ```python
   # cloud-run-backend/services/graph_builder.py
   async def extract_citations():
       """Extract citation relationships from papers"""
       papers = get_all_papers_from_firestore()
       
       for paper in papers:
           # Create Paper node
           create_paper_node(paper)
           
           # Extract citations from paper metadata
           citations = paper.get('citations', [])
           for cited_doi in citations:
               cited_paper = find_paper_by_doi(cited_doi)
               if cited_paper:
                   create_citation_relationship(paper['id'], cited_paper['id'])
   ```

2. **Entity Relationships**
   ```python
   async def extract_entity_relationships():
       """Extract entity relationships from papers and processes"""
       # Papers → Entities
       papers = get_all_papers_from_firestore()
       for paper in papers:
           entities = paper.get('preprocessing', {}).get('entities_extracted', [])
           for entity in entities:
               entity_node = get_or_create_entity(entity)
               create_relationship(
                   'MENTIONS',
                   paper['id'], 'Paper',
                   entity_node['id'], 'Entity',
                   {'frequency': entity.get('frequency', 1)}
               )
       
       # GLMP Processes → Entities
       processes = get_all_glmp_from_gcs()
       for process in processes:
           entities = process.get('entities', [])
           for entity in entities:
               entity_node = get_or_create_entity(entity)
               create_relationship(
                   'USES',
                   process['id'], 'GLMP_Process',
                   entity_node['id'], 'Entity',
                   {'role': 'participant'}
               )
   ```

3. **Cross-Component Relationships**
   ```python
   async def extract_cross_component_relationships():
       """Link papers, processes, and podcasts"""
       # GLMP Processes → Papers (if source paper exists)
       processes = get_all_glmp_from_gcs()
       for process in processes:
           source_paper = process.get('source')
           if source_paper:
               paper = find_paper_by_doi_or_title(source_paper)
               if paper:
                   create_relationship(
                       'VISUALIZES',
                       process['id'], 'GLMP_Process',
                       paper['id'], 'Paper',
                       {'version': process.get('version', '1.0')}
                   )
       
       # Podcasts → Papers
       podcasts = get_all_podcasts_from_firestore()
       for podcast in podcasts:
           source_papers = podcast.get('source_papers', [])
           for paper_id in source_papers:
               create_relationship(
                   'SOURCES',
                   podcast['id'], 'Podcast',
                   paper_id, 'Paper',
                   {'order': source_papers.index(paper_id)}
               )
   ```

4. **Semantic Relationships (from Vector Search)**
   ```python
   async def extract_semantic_relationships():
       """Create relationships based on semantic similarity"""
       # Use vector search to find similar content
       all_content = get_all_content_ids()
       
       for content_id, content_type in all_content:
           similar = await find_similar_content(content_id, content_type, limit=5)
           
           for similar_item in similar:
               if similar_item['similarity_score'] > 0.8:  # High similarity threshold
                   create_relationship(
                       'RELATED_TO',
                       content_id, content_type,
                       similar_item['id'], similar_item['type'],
                       {
                           'strength': similar_item['similarity_score'],
                           'type': 'semantic'
                       }
                   )
   ```

**Deliverables:**
- Relationship extraction scripts
- Initial graph populated with existing data
- ~10,000+ relationships extracted

#### Phase 2.3: Graph Query Tools (Week 7-8)

**Objective:** Add graph query capabilities to MCP server

**Tasks:**

1. **MCP Tool: Find Related Paths**
   ```python
   # cloud-run-backend/mcp_server/tools/graph_queries.py
   async def find_related_paths(
       source_id: str,
       target_id: str,
       max_depth: int = 3
   ) -> str:
       """Find paths between two nodes"""
       query = """
       MATCH path = shortestPath(
           (source)-[*1..%d]-(target)
       )
       WHERE id(source) = $source_id AND id(target) = $target_id
       RETURN path
       LIMIT 10
       """ % max_depth
       
       results = graph_service.execute_query(query, {
           'source_id': source_id,
           'target_id': target_id
       })
       
       paths = [format_path(r['path']) for r in results]
       return json.dumps({'paths': paths})
   ```

2. **MCP Tool: Get Entity Network**
   ```python
   async def get_entity_network(
       entity_name: str,
       depth: int = 2
   ) -> str:
       """Get network of entities connected to a given entity"""
       query = """
       MATCH (e:Entity {name: $entity_name})
       MATCH path = (e)-[*1..%d]-(connected)
       RETURN DISTINCT connected, relationships(path) as rels
       LIMIT 50
       """ % depth
       
       results = graph_service.execute_query(query, {'entity_name': entity_name})
       
       network = {
           'central_entity': entity_name,
           'connected_nodes': [format_node(r['connected']) for r in results],
           'relationships': [format_rels(r['rels']) for r in results]
       }
       
       return json.dumps(network)
   ```

3. **MCP Tool: Discover Connections**
   ```python
   async def discover_connections(
       paper_id: str,
       process_id: str = None,
       podcast_id: str = None
   ) -> str:
       """Discover all connections for a given item"""
       query = """
       MATCH (n)
       WHERE n.id = $item_id
       MATCH (n)-[r]-(connected)
       RETURN type(r) as relationship_type, connected, r
       LIMIT 100
       """
       
       results = graph_service.execute_query(query, {'item_id': paper_id or process_id or podcast_id})
       
       connections = group_by_relationship_type(results)
       return json.dumps(connections)
   ```

4. **MCP Tool: Find Bridge Entities**
   ```python
   async def find_bridge_entities(
       paper1_id: str,
       paper2_id: str
   ) -> str:
       """Find entities that connect two papers"""
       query = """
       MATCH (p1:Paper {id: $paper1_id})-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(p2:Paper {id: $paper2_id})
       RETURN e, count(*) as connection_strength
       ORDER BY connection_strength DESC
       LIMIT 20
       """
       
       results = graph_service.execute_query(query, {
           'paper1_id': paper1_id,
           'paper2_id': paper2_id
       })
       
       return json.dumps({
           'bridge_entities': [format_entity(r['e']) for r in results],
           'connection_strengths': [r['connection_strength'] for r in results]
       })
   ```

**Deliverables:**
- Graph query MCP tools
- API endpoints for graph queries
- Documentation and examples

#### Phase 2.4: Real-Time Graph Updates (Week 8-9)

**Objective:** Keep graph synchronized with data changes

**Tasks:**

1. **Firestore Triggers for Graph Updates**
   ```python
   # cloud-functions/update_graph_trigger.py
   @functions_framework.http
   def on_paper_created(data, context):
       """Update graph when new paper is created"""
       paper_id = context.resource.split('/')[-1]
       paper = get_paper_from_firestore(paper_id)
       
       # Create paper node
       graph_service.execute_query(
           "CREATE (p:Paper $props)",
           {'props': paper}
       )
       
       # Extract and create relationships
       extract_and_create_relationships(paper)
   ```

2. **Incremental Relationship Updates**
   ```python
   async def update_relationships_periodically():
       """Periodic job to update relationships"""
       # Check for new citations
       # Update semantic relationships
       # Refresh entity co-occurrence
   ```

**Deliverables:**
- Real-time graph synchronization
- Periodic relationship updates

---

## Part 3: RAG (Retrieval-Augmented Generation) Implementation

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────┐
│         User Query                       │
│  "What processes use ATP?"               │
└──────────────┬──────────────────────────┘
               │
               │ 1. Generate Query Embedding
               │
┌──────────────▼──────────────────────────┐
│     Vector Search                        │
│  - Find relevant context                 │
│  - Top-K retrieval (K=5-10)             │
└──────────────┬──────────────────────────┘
               │
               │ 2. Retrieve Context
               │
┌──────────────▼──────────────────────────┐
│     Context Assembly                     │
│  - Combine retrieved documents           │
│  - Add metadata                          │
│  - Format for LLM                        │
└──────────────┬──────────────────────────┘
               │
               │ 3. Grounded Prompt
               │
┌──────────────▼──────────────────────────┐
│     LLM (Gemini/GPT-4/Claude)           │
│  - Generate response                     │
│  - Cite sources                          │
│  - Provide references                   │
└──────────────┬──────────────────────────┘
               │
               │ 4. Response + Sources
               │
┌──────────────▼──────────────────────────┐
│         User                             │
└──────────────────────────────────────────┘
```

### 3.2 Technology Stack

**RAG Framework:**
- **Primary:** LangChain (most mature, great tooling)
- **Alternative:** LlamaIndex (simpler, good for specific use cases)
- **Why:** LangChain has excellent integration with Vertex AI and vector stores

**LLM:**
- **Primary:** Google Gemini 3 (you already use it)
- **Fallback:** GPT-4, Claude 3
- **Why:** Consistency with existing stack, good performance

**Vector Store:**
- **Use:** Vertex AI Vector Search (from Part 1)
- **Integration:** LangChain Vertex AI Vector Search connector

### 3.3 Implementation Phases

#### Phase 3.1: RAG Pipeline Setup (Week 9-10)

**Objective:** Create basic RAG pipeline

**Tasks:**

1. **Install Dependencies**
   ```bash
   pip install langchain langchain-google-vertexai langchain-community
   ```

2. **RAG Service Module**
   ```python
   # cloud-run-backend/services/rag_service.py
   from langchain.llms import VertexAI
   from langchain.embeddings import VertexAIEmbeddings
   from langchain.vectorstores import VertexAIVectorSearch
   from langchain.chains import RetrievalQA
   from langchain.prompts import PromptTemplate
   
   class RAGService:
       def __init__(self):
           self.llm = VertexAI(
               model_name="gemini-pro",
               temperature=0.1,
               max_output_tokens=1024
           )
           
           self.embeddings = VertexAIEmbeddings(
               model_name="text-embedding-004"
           )
           
           self.vector_store = VertexAIVectorSearch(
               index_name="copernicusai-knowledge-index",
               embedding=self.embeddings
           )
           
           # Custom prompt template
           self.qa_prompt = PromptTemplate(
               template="""
               You are a scientific research assistant with access to a knowledge base.
               
               Use the following context to answer the question. Cite specific sources.
               
               Context:
               {context}
               
               Question: {question}
               
               Answer:
               """,
               input_variables=["context", "question"]
           )
           
           self.qa_chain = RetrievalQA.from_chain_type(
               llm=self.llm,
               chain_type="stuff",
               retriever=self.vector_store.as_retriever(
                   search_kwargs={"k": 5}  # Top 5 results
               ),
               chain_type_kwargs={"prompt": self.qa_prompt},
               return_source_documents=True
           )
       
       def query(self, question: str) -> dict:
           """Query RAG system"""
           result = self.qa_chain({"query": question})
           
           return {
               "answer": result["result"],
               "sources": [
                   {
                       "id": doc.metadata.get("id"),
                       "type": doc.metadata.get("type"),
                       "title": doc.metadata.get("title"),
                       "relevance_score": doc.metadata.get("score", 0)
                   }
                   for doc in result["source_documents"]
               ]
           }
   ```

3. **MCP Tool: RAG Query**
   ```python
   # cloud-run-backend/mcp_server/tools/rag.py
   from services.rag_service import RAGService
   
   rag_service = RAGService()
   
   async def rag_query(question: str) -> str:
       """Answer question using RAG"""
       result = rag_service.query(question)
       
       return json.dumps({
           "answer": result["answer"],
           "sources": result["sources"],
           "confidence": calculate_confidence(result)
       })
   ```

**Deliverables:**
- RAG service module
- MCP tool for RAG queries
- Basic testing

#### Phase 3.2: Advanced RAG Features (Week 10-11)

**Objective:** Enhance RAG with advanced features

**Tasks:**

1. **Multi-Step RAG (ReAct Pattern)**
   ```python
   from langchain.agents import initialize_agent, Tool
   from langchain.agents import AgentType
   
   def create_rag_agent():
       """Create agent that can use multiple tools"""
       tools = [
           Tool(
               name="VectorSearch",
               func=vector_search_tool,
               description="Search knowledge base semantically"
           ),
           Tool(
               name="GraphQuery",
               func=graph_query_tool,
               description="Query knowledge graph for relationships"
           ),
           Tool(
               name="GetDocument",
               func=get_document_tool,
               description="Get full document by ID"
           )
       ]
       
       agent = initialize_agent(
           tools,
           llm,
           agent=AgentType.REACT_DESCRIPTION,
           verbose=True
       )
       
       return agent
   ```

2. **Hybrid Retrieval (Vector + Graph)**
   ```python
   async def hybrid_rag_query(question: str) -> dict:
       """RAG with both vector and graph retrieval"""
       # Step 1: Vector search
       vector_results = await search_semantic(question, limit=5)
       
       # Step 2: Extract entities and query graph
       entities = extract_entities(question)
       graph_results = []
       for entity in entities:
           network = await get_entity_network(entity, depth=2)
           graph_results.extend(network['connected_nodes'])
       
       # Step 3: Combine and rank
       combined_context = combine_and_rank(vector_results, graph_results)
       
       # Step 4: Generate answer
       answer = generate_answer(question, combined_context)
       
       return {
           "answer": answer,
           "sources": combined_context,
           "retrieval_method": "hybrid"
       }
   ```

3. **Citation and Source Attribution**
   ```python
   def format_answer_with_citations(answer: str, sources: list) -> str:
       """Format answer with inline citations"""
       formatted = answer
       
       for i, source in enumerate(sources, 1):
           citation = f"[{i}]"
           # Add citation markers in answer
           # Link to source metadata
       
       # Add references section
       references = "\n\nReferences:\n"
       for i, source in enumerate(sources, 1):
           references += f"[{i}] {source['title']} ({source['type']})\n"
       
       return formatted + references
   ```

**Deliverables:**
- Advanced RAG features
- Multi-step reasoning
- Citation formatting

#### Phase 3.3: RAG Optimization (Week 11-12)

**Objective:** Optimize RAG performance and accuracy

**Tasks:**

1. **Query Rewriting**
   ```python
   def rewrite_query(original_query: str) -> str:
       """Rewrite query for better retrieval"""
       # Expand abbreviations
       # Add synonyms
       # Disambiguate terms
       rewritten = llm.generate(
           f"Rewrite this scientific query for better search: {original_query}"
       )
       return rewritten
   ```

2. **Re-ranking**
   ```python
   from sentence_transformers import CrossEncoder
   
   def rerank_results(query: str, results: list, top_k: int = 5) -> list:
       """Re-rank results using cross-encoder"""
       model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
       
       pairs = [(query, result['text']) for result in results]
       scores = model.predict(pairs)
       
       # Sort by score
       ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
       
       return [r[0] for r in ranked[:top_k]]
   ```

3. **Context Window Management**
   ```python
   def select_best_context(query: str, retrieved_docs: list, max_tokens: int = 2000) -> list:
       """Select best documents that fit in context window"""
       # Score each document
       scored = [(doc, score_relevance(query, doc)) for doc in retrieved_docs]
       scored.sort(key=lambda x: x[1], reverse=True)
       
       # Greedily select documents that fit
       selected = []
       current_tokens = 0
       
       for doc, score in scored:
           doc_tokens = count_tokens(doc['text'])
           if current_tokens + doc_tokens <= max_tokens:
               selected.append(doc)
               current_tokens += doc_tokens
       
       return selected
   ```

**Deliverables:**
- Optimized RAG pipeline
- Better retrieval accuracy
- Performance improvements

---

## Part 4: Integration & Testing

### 4.1 Integration Points

1. **MCP Server Integration**
   - Add all new tools to MCP server
   - Update tool discovery
   - Document new capabilities

2. **API Integration**
   - REST endpoints for vector search
   - Graph query endpoints
   - RAG query endpoints

3. **Frontend Integration**
   - Search UI with semantic search
   - Graph visualization
   - RAG chat interface

### 4.2 Testing Strategy

1. **Unit Tests**
   - Embedding generation
   - Vector search queries
   - Graph queries
   - RAG responses

2. **Integration Tests**
   - End-to-end vector search
   - Graph traversal
   - RAG pipeline

3. **Performance Tests**
   - Query latency
   - Throughput
   - Scalability

### 4.3 Monitoring

1. **Metrics**
   - Query response times
   - Retrieval accuracy
   - Graph query performance
   - RAG answer quality

2. **Logging**
   - All queries logged
   - Performance metrics
   - Error tracking

---

## Timeline Summary

**Total Duration:** 12 weeks (3 months)

- **Weeks 1-5:** Vector Search (embedding pipeline, index setup, query interface)
- **Weeks 5-9:** Knowledge Graph (Neo4j setup, relationship extraction, graph queries)
- **Weeks 9-12:** RAG (pipeline setup, advanced features, optimization)
- **Week 12+:** Integration, testing, deployment

**Phased Rollout:**
- Each component can be deployed independently
- Start with vector search (highest immediate value)
- Add knowledge graph (enables advanced queries)
- Complete with RAG (full AI-powered knowledge system)

---

## Cost Estimates

### Vector Search (Vertex AI)
- **Embedding Generation:** ~$0.0001 per 1K tokens
- **Vector Search Index:** ~$200/month for 1M vectors
- **Query Costs:** ~$0.01 per 1K queries

### Knowledge Graph (Neo4j Aura)
- **Starter:** ~$65/month (up to 50K nodes)
- **Professional:** ~$330/month (up to 1M nodes)
- **Enterprise:** Custom pricing

### RAG (LLM Costs)
- **Gemini Pro:** ~$0.001 per 1K input tokens, $0.002 per 1K output tokens
- **Average query:** ~$0.01-0.05 per query

**Total Monthly Estimate:** $300-500/month (depending on scale)

---

## Success Metrics

1. **Vector Search:**
   - 95%+ retrieval accuracy (relevant results in top 10)
   - <500ms query latency
   - 100% content coverage (all papers, processes, podcasts indexed)

2. **Knowledge Graph:**
   - 10,000+ relationships extracted
   - <200ms graph query latency
   - 100% relationship coverage (all citations, entities linked)

3. **RAG:**
   - 80%+ answer accuracy (human evaluation)
   - <2s end-to-end response time
   - 100% source attribution

---

## Next Steps

1. **Week 1:** Set up Vertex AI Vector Search, create embedding service
2. **Week 2:** Begin indexing existing content
3. **Week 3:** Implement vector search MCP tools
4. **Week 4:** Set up Neo4j, design graph schema
5. **Week 5:** Begin relationship extraction
6. **Continue:** Follow phased implementation plan

---

## References

- Vertex AI Vector Search: https://cloud.google.com/vertex-ai/docs/vector-search/overview
- Neo4j Documentation: https://neo4j.com/docs/
- LangChain RAG: https://python.langchain.com/docs/use_cases/question_answering/
- Vertex AI Embeddings: https://cloud.google.com/vertex-ai/docs/generative-ai/embeddings/get-text-embeddings


