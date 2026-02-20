# MCP Server Implementation Plan
## CopernicusAI Knowledge Engine

**Date:** December 24, 2025  
**Status:** Planning Phase  
**Estimated Total Time:** 3-4 weeks (part-time) or 1-2 weeks (full-time)

---

## Executive Summary

This plan outlines the implementation of a Model Context Protocol (MCP) server for the CopernicusAI Knowledge Engine. The MCP server will expose all five components (CopernicusAI, GLMP, Programming Framework, Research Paper Metadata Database, Science Video Database) as queryable tools for AI assistants like Cursor, Claude Desktop, and other MCP-compatible clients.

**Key Benefits:**
- Direct AI assistant access to all knowledge engine data
- Real-time queries across all components
- Enhanced development workflow
- Better integration between components
- Support for NSF/DOE proposal goals

---

## Current Infrastructure Analysis

### Existing Stack
- **Backend:** FastAPI (Python) on Google Cloud Run
- **Database:** Google Cloud Firestore (NoSQL)
- **Storage:** Google Cloud Storage (GCS)
- **Collections:** `subscribers`, `podcast_jobs`, `research_papers`, `episodes`
- **GCS Buckets:** `audio/`, `transcripts/`, `descriptions/`, `glmp-v2/`
- **API Base:** `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`

### Data Sources to Expose
1. **Research Paper Metadata Database** (Firestore: `research_papers`)
2. **GLMP Process Database** (GCS: `glmp-v2/*.json`)
3. **CopernicusAI Podcasts** (Firestore: `podcast_jobs`, `episodes`)
4. **Science Video Database** (Future: transcript search)
5. **Programming Framework Processes** (Future: cross-domain processes)

---

## Implementation Phases

### Phase 1: Foundation & Setup (2-3 days)

**Objectives:**
- Set up MCP server infrastructure
- Create basic server structure
- Configure authentication
- Set up development environment

**Tasks:**
1. **Install MCP Python SDK**
   ```bash
   pip install mcp
   ```
   - Time: 30 minutes

2. **Create MCP Server Module Structure**
   ```
   cloud-run-backend/
   ├── mcp_server/
   │   ├── __init__.py
   │   ├── server.py          # Main MCP server
   │   ├── tools/
   │   │   ├── __init__.py
   │   │   ├── papers.py      # Research paper queries
   │   │   ├── glmp.py        # GLMP process queries
   │   │   ├── podcasts.py    # Podcast queries
   │   │   └── videos.py      # Video database queries (future)
   │   ├── models/
   │   │   └── mcp_models.py  # Pydantic models for MCP
   │   └── config.py          # Configuration
   ```
   - Time: 2-3 hours

3. **Set Up Authentication**
   - Use existing GCP service account credentials
   - Configure Firestore and GCS access
   - Time: 1-2 hours

4. **Create Basic Server Skeleton**
   - Initialize MCP server with basic tools
   - Test server startup
   - Time: 2-3 hours

**Deliverables:**
- ✅ MCP server module structure
- ✅ Basic server running locally
- ✅ Authentication configured

**Estimated Time:** 6-8 hours (1 day)

---

### Phase 2: Research Paper Metadata Tools (2-3 days)

**Objectives:**
- Expose Research Paper Metadata Database via MCP tools
- Enable querying by DOI, title, keywords, entities
- Support citation network queries

**MCP Tools to Implement:**

1. **`query_research_papers`**
   - **Parameters:** `query` (string), `limit` (int, default 10), `filters` (dict)
   - **Returns:** List of papers with metadata
   - **Use Cases:** "Find papers about CRISPR", "Get papers by DOI"
   - Time: 4-5 hours

2. **`get_paper_by_id`**
   - **Parameters:** `paper_id` (string)
   - **Returns:** Full paper metadata with preprocessing
   - **Use Cases:** "Get paper details for DOI:10.1038/..."
   - Time: 2-3 hours

3. **`get_paper_citations`**
   - **Parameters:** `paper_id` (string)
   - **Returns:** List of papers that cite this paper
   - **Use Cases:** "What papers cite this paper?"
   - Time: 3-4 hours

4. **`search_papers_by_entity`**
   - **Parameters:** `entity` (string), `entity_type` (string: "gene", "protein", "chemical", etc.)
   - **Returns:** Papers mentioning the entity
   - **Use Cases:** "Find papers about p53 gene"
   - Time: 3-4 hours

**Implementation Details:**
- Use existing Firestore `research_papers` collection
- Leverage existing `endpoints/papers/routes.py` logic
- Add MCP tool wrappers

**Deliverables:**
- ✅ 4 MCP tools for research papers
- ✅ Integration with Firestore
- ✅ Error handling and validation

**Estimated Time:** 12-16 hours (2-3 days)

---

### Phase 3: GLMP Process Database Tools (2-3 days)

**Objectives:**
- Expose GLMP biological processes via MCP tools
- Enable querying by category, process name, entities
- Support Mermaid diagram retrieval

**MCP Tools to Implement:**

1. **`list_glmp_processes`**
   - **Parameters:** `category` (optional: "Central Dogma", "Metabolism", etc.), `limit` (int)
   - **Returns:** List of processes with metadata
   - **Use Cases:** "List all GLMP processes", "Get processes in Central Dogma category"
   - Time: 3-4 hours

2. **`get_glmp_process`**
   - **Parameters:** `process_id` (string) or `process_name` (string)
   - **Returns:** Full process JSON with Mermaid diagram
   - **Use Cases:** "Get beta-galactosidase regulation process"
   - Time: 2-3 hours

3. **`search_glmp_by_entity`**
   - **Parameters:** `entity` (string: gene, protein, molecule)
   - **Returns:** Processes involving the entity
   - **Use Cases:** "Find GLMP processes involving p53"
   - Time: 3-4 hours

4. **`get_glmp_categories`**
   - **Parameters:** None
   - **Returns:** List of all categories with process counts
   - **Use Cases:** "What categories are in GLMP?"
   - Time: 1-2 hours

**Implementation Details:**
- Read from GCS bucket: `gs://regal-scholar-453620-r7-podcast-storage/glmp-v2/`
- Parse JSON files (100+ processes)
- Cache metadata for faster queries

**Deliverables:**
- ✅ 4 MCP tools for GLMP
- ✅ GCS integration
- ✅ JSON parsing and caching

**Estimated Time:** 9-13 hours (2-3 days)

---

### Phase 4: CopernicusAI Podcast Tools (2-3 days)

**Objectives:**
- Expose podcast metadata via MCP tools
- Enable querying by topic, discipline, source papers
- Support episode retrieval

**MCP Tools to Implement:**

1. **`list_podcasts`**
   - **Parameters:** `discipline` (optional), `limit` (int), `subscriber_id` (optional)
   - **Returns:** List of podcasts with metadata
   - **Use Cases:** "List all biology podcasts", "Get my podcasts"
   - Time: 3-4 hours

2. **`get_podcast_details`**
   - **Parameters:** `podcast_id` (string)
   - **Returns:** Full podcast metadata, source papers, transcript link
   - **Use Cases:** "Get details for podcast XYZ"
   - Time: 2-3 hours

3. **`get_podcast_source_papers`**
   - **Parameters:** `podcast_id` (string)
   - **Returns:** List of source papers used in podcast
   - **Use Cases:** "What papers were used in this podcast?"
   - Time: 2-3 hours

4. **`search_podcasts_by_topic`**
   - **Parameters:** `topic` (string), `limit` (int)
   - **Returns:** Podcasts matching topic
   - **Use Cases:** "Find podcasts about quantum computing"
   - Time: 3-4 hours

**Implementation Details:**
- Use Firestore collections: `podcast_jobs`, `episodes`
- Leverage existing `endpoints/podcast/routes.py` logic
- Include GCS links to audio/transcripts

**Deliverables:**
- ✅ 4 MCP tools for podcasts
- ✅ Integration with Firestore and GCS
- ✅ Source paper linking

**Estimated Time:** 10-15 hours (2-3 days)

---

### Phase 5: Cross-Component Integration Tools (2-3 days)

**Objectives:**
- Enable cross-modal queries
- Link components together
- Support knowledge graph queries

**MCP Tools to Implement:**

1. **`find_related_content`**
   - **Parameters:** `paper_id` (optional), `podcast_id` (optional), `process_id` (optional)
   - **Returns:** Related content across all components
   - **Use Cases:** "What podcasts and GLMP processes relate to this paper?"
   - Time: 4-5 hours

2. **`get_paper_visualizations`**
   - **Parameters:** `paper_id` (string)
   - **Returns:** GLMP processes and Programming Framework diagrams related to paper
   - **Use Cases:** "Get visualizations for this paper"
   - Time: 3-4 hours

3. **`search_across_components`**
   - **Parameters:** `query` (string), `components` (list: ["papers", "podcasts", "glmp"])
   - **Returns:** Results from specified components
   - **Use Cases:** "Search for CRISPR across all components"
   - Time: 4-5 hours

**Implementation Details:**
- Cross-reference entities across components
- Use entity extraction for linking
- Cache relationship mappings

**Deliverables:**
- ✅ 3 cross-component MCP tools
- ✅ Entity-based linking
- ✅ Unified search interface

**Estimated Time:** 11-14 hours (2-3 days)

---

### Phase 6: Testing & Validation (2-3 days)

**Objectives:**
- Test all MCP tools
- Validate data accuracy
- Performance testing
- Integration with Cursor/Claude Desktop

**Tasks:**

1. **Unit Testing**
   - Test each MCP tool individually
   - Validate input/output formats
   - Error handling tests
   - Time: 4-5 hours

2. **Integration Testing**
   - Test with Cursor IDE
   - Test with Claude Desktop
   - Verify data accuracy
   - Time: 3-4 hours

3. **Performance Testing**
   - Query response times
   - Concurrent request handling
   - Cache effectiveness
   - Time: 2-3 hours

4. **Documentation**
   - Tool descriptions
   - Usage examples
   - Configuration guide
   - Time: 2-3 hours

**Deliverables:**
- ✅ Test suite for all tools
- ✅ Integration verified with Cursor
- ✅ Performance benchmarks
- ✅ Documentation complete

**Estimated Time:** 11-15 hours (2-3 days)

---

### Phase 7: Deployment & Production (1-2 days)

**Objectives:**
- Deploy MCP server to production
- Configure for Cloud Run or standalone service
- Set up monitoring
- Create deployment documentation

**Tasks:**

1. **Deployment Options**
   - **Option A:** Standalone MCP server (stdin/stdout for Cursor)
   - **Option B:** HTTP MCP server (if supported)
   - **Option C:** Integrate into existing FastAPI app
   - Time: 2-3 hours

2. **Configuration**
   - Environment variables
   - GCP credentials
   - Firestore/GCS access
   - Time: 1-2 hours

3. **Monitoring**
   - Logging setup
   - Error tracking
   - Usage metrics
   - Time: 1-2 hours

4. **Documentation**
   - Setup instructions
   - Configuration guide
   - Usage examples
   - Time: 2-3 hours

**Deliverables:**
- ✅ MCP server deployed
- ✅ Configuration documented
- ✅ Monitoring in place
- ✅ User guide complete

**Estimated Time:** 6-10 hours (1-2 days)

---

## Total Time Estimate

### By Phase:
- **Phase 1:** Foundation (1 day) - 6-8 hours
- **Phase 2:** Research Papers (2-3 days) - 12-16 hours
- **Phase 3:** GLMP (2-3 days) - 9-13 hours
- **Phase 4:** Podcasts (2-3 days) - 10-15 hours
- **Phase 5:** Cross-Component (2-3 days) - 11-14 hours
- **Phase 6:** Testing (2-3 days) - 11-15 hours
- **Phase 7:** Deployment (1-2 days) - 6-10 hours

### Total Estimates:
- **Part-time (4-6 hours/day):** 3-4 weeks
- **Full-time (8 hours/day):** 1.5-2 weeks
- **Focused sprint (10+ hours/day):** 1 week

### Conservative Estimate: **3-4 weeks (part-time)**

---

## Technical Architecture

### MCP Server Structure
```
mcp_server/
├── server.py              # Main MCP server (stdin/stdout or HTTP)
├── tools/
│   ├── papers.py          # Research paper tools (4 tools)
│   ├── glmp.py            # GLMP process tools (4 tools)
│   ├── podcasts.py        # Podcast tools (4 tools)
│   └── cross_component.py # Cross-component tools (3 tools)
├── models/
│   └── mcp_models.py      # Pydantic models
├── utils/
│   ├── firestore_client.py
│   ├── gcs_client.py
│   └── cache.py
└── config.py
```

### Dependencies
```python
# requirements_mcp.txt
mcp>=0.1.0
google-cloud-firestore>=2.0.0
google-cloud-storage>=2.0.0
pydantic>=2.0.0
```

### Integration Points
- **Firestore:** Existing `firestore.Client()` instances
- **GCS:** Existing `storage.Client()` instances
- **API Endpoints:** Reuse logic from `endpoints/` modules
- **Models:** Reuse existing Pydantic models where possible

---

## Risk Assessment & Mitigation

### Risks:
1. **MCP SDK Changes:** MCP is relatively new, API may change
   - **Mitigation:** Pin version, monitor updates, use stable releases

2. **Performance:** Querying Firestore/GCS may be slow
   - **Mitigation:** Implement caching, optimize queries, use indexes

3. **Authentication:** GCP credentials management
   - **Mitigation:** Use existing service account setup, environment variables

4. **Data Consistency:** Multiple data sources may have inconsistencies
   - **Mitigation:** Validate data, handle errors gracefully, log issues

---

## Success Criteria

### Functional Requirements:
- ✅ All 15 MCP tools implemented and working
- ✅ Integration with Cursor IDE successful
- ✅ Queries return accurate data
- ✅ Error handling robust

### Performance Requirements:
- ✅ Query response time < 2 seconds for simple queries
- ✅ Query response time < 5 seconds for complex cross-component queries
- ✅ Server startup time < 5 seconds

### Usability Requirements:
- ✅ Clear tool descriptions
- ✅ Helpful error messages
- ✅ Documentation complete

---

## Future Enhancements (Post-MVP)

1. **Science Video Database Integration**
   - Transcript search tools
   - Video metadata queries
   - Time: 2-3 days

2. **Programming Framework Tools**
   - Cross-domain process queries
   - Process comparison tools
   - Time: 2-3 days

3. **Advanced Features**
   - Streaming responses for large queries
   - Query result caching
   - Usage analytics
   - Time: 3-5 days

---

## Next Steps

1. **Review and Approve Plan** - Confirm approach and timeline
2. **Set Up Development Environment** - Install MCP SDK, create module structure
3. **Begin Phase 1** - Foundation and setup
4. **Iterate Through Phases** - Complete each phase before moving to next
5. **Test Continuously** - Test with Cursor after each phase

---

## Questions to Consider

1. **Deployment Model:** Standalone server or integrated into FastAPI?
   - **Recommendation:** Start with standalone for simplicity

2. **Authentication:** How to handle Cursor authentication?
   - **Recommendation:** Use existing GCP service account

3. **Caching Strategy:** What to cache and for how long?
   - **Recommendation:** Cache GLMP metadata, paper lists (5-10 min TTL)

4. **Error Handling:** How verbose should error messages be?
   - **Recommendation:** Detailed for development, sanitized for production

---

**Document Version:** 1.0  
**Last Updated:** December 24, 2025  
**Author:** AI Assistant (Auto)  
**Status:** Ready for Review


