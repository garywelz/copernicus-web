# Content Ingestion Plan for Vector Search & RAG Testing

**Date:** December 2025  
**Status:** Planning  
**Goal:** Ingest sufficient content (500+ papers, 1000+ videos) to enable meaningful vector search and RAG testing

---

## Executive Summary

This plan addresses the need for more content in both the Research Paper Metadata Database and Science Video Database to enable comprehensive testing of the newly implemented vector search and RAG capabilities in CopernicusAI.

**Current State:**
- **Research Papers:** Unknown count (needs assessment)
- **Videos:** Unknown count (needs assessment)
- **CopernicusAI Firestore:** 45 podcasts indexed, likely 0 papers

**Target State:**
- **Research Papers:** 500+ mathematics papers from arXiv
- **Videos:** 1000+ science videos from YouTube
- **Integration:** Content synced to CopernicusAI Firestore for unified vector search

---

## Part 1: Current Content Assessment

### 1.1 Research Paper Metadata Database Assessment

**Location:** `/home/gdubs/copernicusai-research-metadata`  
**Database:** PostgreSQL (Cloud SQL)  
**GitHub:** https://github.com/garywelz/copernicusai-research-metadata  
**HuggingFace:** https://huggingface.co/spaces/garywelz/metadata_database

#### Assessment Tasks

1. **Check Current Paper Count**
   ```bash
   cd /home/gdubs/copernicusai-research-metadata
   python scripts/check_ingested_papers.py
   ```

2. **Check Category Distribution**
   - Run the check script to see math category breakdown
   - Identify gaps in coverage

3. **Check Database Connection**
   ```bash
   # Test API endpoint
   curl http://localhost:8000/api/v0/ingestion/arxiv/test
   ```

4. **Verify Ingestion Scripts**
   - Confirm `scripts/ingest_mathematics.py` is functional
   - Test with small batch (5 papers)

#### Expected Output
- Total paper count
- Mathematics paper count
- Category distribution (math.AT, math.NT, math.CO, etc.)
- Database health status

### 1.2 Science Video Database Assessment

**Location:** `/home/gdubs/scienceviddb`  
**Database:** PostgreSQL (Cloud SQL)  
**GitHub:** https://github.com/garywelz/sciencevideodb  
**HuggingFace:** https://huggingface.co/spaces/garywelz/sciencevideodb

#### Assessment Tasks

1. **Check Current Video Count**
   ```bash
   cd /home/gdubs/scienceviddb
   # Check database directly or use verification script
   npm run verify-ingestion --workspace=packages/ingestion
   ```

2. **Check Channel Registry**
   - Count active channels
   - Check last ingestion dates
   - Identify channels needing updates

3. **Check Ingestion Pipeline**
   ```bash
   # Test with single channel
   npm run ingest -- --channel <CHANNEL_ID>
   ```

4. **Check Embedding Status**
   - Verify embeddings are being generated
   - Check for videos without embeddings

#### Expected Output
- Total video count
- Videos per discipline (biology, chemistry, physics, mathematics, cs)
- Active channel count
- Embedding coverage percentage

### 1.3 CopernicusAI Firestore Assessment

**Location:** `/home/gdubs/copernicus-web-public/cloud-run-backend`  
**Database:** Firestore (`copernicusai` database)  
**Collections:** `research_papers`, `podcast_jobs`

#### Assessment Tasks

1. **Check Paper Count in Firestore**
   ```python
   # Use MCP tool or direct Firestore query
   from mcp_server.utils.firestore_client import get_firestore_client
   db = get_firestore_client()
   papers = db.collection('research_papers').stream()
   count = sum(1 for _ in papers)
   ```

2. **Check Podcast Count** (already known: 45)
   - Verify all have embeddings
   - Check embedding quality

3. **Check Vector Index Status**
   ```bash
   gcloud firestore indexes list --project=regal-scholar-453620-r7 --database=copernicusai
   ```

#### Expected Output
- Paper count in Firestore
- Podcast count (with embeddings)
- Vector index status (READY/PENDING)

---

## Part 2: Research Paper Ingestion Plan

### 2.1 Target: 500+ Mathematics Papers from arXiv

**Priority:** High (needed for vector search testing)  
**Timeline:** 1-2 days  
**Method:** Batch ingestion using existing `ingest_mathematics.py` script

#### Ingestion Strategy

**Phase 1: Initial Batch (200 papers)**
- Focus on diverse math subcategories
- Target: 50 papers per major category

**Phase 2: Expansion (300 papers)**
- Fill gaps in underrepresented categories
- Add recent papers (last 6 months)
- Include cross-category papers

#### Mathematics Categories to Ingest

| Category | Code | Target | Priority |
|----------|------|--------|----------|
| Algebra | math.RA | 50 | High |
| Analysis | math.CA | 50 | High |
| Combinatorics | math.CO | 50 | High |
| Geometry | math.DG | 50 | High |
| Topology | math.AT | 50 | High |
| Number Theory | math.NT | 50 | High |
| Probability | math.PR | 30 | Medium |
| Statistics | math.ST | 30 | Medium |
| Logic | math.LO | 30 | Medium |
| Algebraic Geometry | math.AG | 30 | Medium |
| Differential Equations | math.DS | 30 | Medium |
| Optimization | math.OC | 20 | Low |
| Numerical Analysis | math.NA | 20 | Low |
| **Total** | | **500** | |

#### Implementation Steps

1. **Prepare Ingestion Script**
   ```bash
   cd /home/gdubs/copernicusai-research-metadata
   # Review and update ingest_mathematics.py if needed
   ```

2. **Run Phase 1: Initial Batch**
   ```bash
   python scripts/ingest_mathematics.py
   # Select option: All categories (50 papers each)
   # This will ingest ~450 papers across 9 categories
   ```

3. **Verify Phase 1 Results**
   ```bash
   python scripts/check_ingested_papers.py
   ```

4. **Run Phase 2: Fill Gaps**
   ```bash
   # Custom queries for underrepresented categories
   python scripts/ingest_mathematics.py
   # Select: Custom query
   # Enter: cat:math.OC (Optimization)
   # Enter: 20 papers
   ```

5. **Final Verification**
   ```bash
   python scripts/check_ingested_papers.py
   # Should show 500+ papers total
   ```

#### Rate Limiting Considerations

- arXiv API: 3-second delay between batches (already in script)
- Batch size: 100 papers per batch
- Estimated time: ~2-3 hours for 500 papers

#### Quality Checks

- Verify all papers have abstracts
- Check for duplicate arXiv IDs
- Ensure categories are properly assigned
- Validate date ranges (include recent papers)

### 2.2 Additional Sources (Future)

**Priority:** Low (after mathematics ingestion)  
**Timeline:** Future phase

- **PubMed/PMC:** Biology and medical papers
- **CrossRef:** DOI-based paper discovery
- **OpenAlex:** Academic paper metadata
- **Semantic Scholar:** Citation networks

---

## Part 3: Science Video Ingestion Plan

### 3.1 Target: 1000+ Science Videos from YouTube

**Priority:** High (needed for comprehensive testing)  
**Timeline:** 2-3 days  
**Method:** Channel-based ingestion using existing pipeline

#### Current State Analysis

Based on `PROJECT_ASSESSMENT.md`:
- **Target:** Prototype phase (10-15 channels, ~2k videos)
- **Status:** Foundation complete, ready to scale

#### Ingestion Strategy

**Phase 1: Expand Channel Registry (50+ channels)**
- Add high-quality science channels
- Focus on research-level content
- Balance across disciplines

**Phase 2: Initial Ingestion (1000 videos)**
- Ingest all registered channels
- Process transcripts
- Generate embeddings

**Phase 3: Ongoing Updates**
- Set up periodic re-ingestion
- Track new videos from existing channels

#### Channel Categories to Add

**Mathematics Channels (10-15 channels)**
- 3Blue1Brown
- Numberphile
- Mathologer
- Stand-up Maths
- Khan Academy (math focus)
- MIT OpenCourseWare (math)
- Eddie Woo
- Professor Leonard

**Physics Channels (10-15 channels)**
- MinutePhysics
- Veritasium
- Physics Girl
- Sixty Symbols
- Fermilab
- PBS Space Time
- ScienceClic
- Dr. Becky

**Biology Channels (10-15 channels)**
- Amoeba Sisters
- iBiology
- Bozeman Science
- Khan Academy (biology)
- Crash Course Biology
- National Geographic
- SciShow

**Chemistry Channels (5-10 channels)**
- Periodic Videos
- Tyler DeWitt
- Professor Dave Explains
- Khan Academy (chemistry)
- Crash Course Chemistry

**Computer Science Channels (5-10 channels)**
- Computerphile
- 3Blue1Brown (CS content)
- MIT OpenCourseWare (CS)
- freeCodeCamp
- The Coding Train

#### Implementation Steps

1. **Add Channels to Registry**
   ```bash
   cd /home/gdubs/scienceviddb
   
   # Option 1: Use existing scripts
   npm run add-channels --workspace=packages/ingestion
   npm run add-biology-channels --workspace=packages/ingestion
   npm run add-research-channels --workspace=packages/ingestion
   
   # Option 2: Create new comprehensive script
   # Create: packages/ingestion/src/scripts/add-comprehensive-channels.ts
   ```

2. **Verify Channel Registry**
   ```bash
   # Check how many channels are registered
   # Query database or use verification script
   ```

3. **Run Initial Ingestion**
   ```bash
   # Ingest all channels
   npm run ingest:all
   
   # Or ingest in batches
   npm run ingest -- --channel <CHANNEL_ID>
   ```

4. **Monitor Ingestion Progress**
   - Check logs for errors
   - Verify videos are being added
   - Check transcript extraction success rate

5. **Generate Embeddings**
   - Verify embeddings are generated automatically
   - Check for videos without embeddings
   - Re-run embedding generation if needed

#### Rate Limiting Considerations

- YouTube API: 100ms delay between calls (already in code)
- Quota: 10,000 units per day (default)
- Estimated time: ~1-2 days for 1000 videos (depending on channel sizes)

#### Quality Checks

- Verify transcripts are extracted
- Check discipline detection accuracy
- Ensure embeddings are generated
- Validate video metadata completeness

### 3.2 Channel Discovery Resources

**Finding New Channels:**
1. YouTube search: "science education", "research talks"
2. Academic institutions: MIT, Stanford, Caltech channels
3. Science organizations: Nature, Science, AAAS
4. Educational platforms: Khan Academy, Coursera
5. Research labs: Janelia, CSHL, Salk Institute

---

## Part 4: Integration with CopernicusAI Firestore

### 4.1 Current Architecture

**Research Paper Metadata Database:**
- **Storage:** PostgreSQL (Cloud SQL)
- **Status:** Separate system, not integrated with Firestore
- **Connection:** None (standalone)

**Science Video Database:**
- **Storage:** PostgreSQL (Cloud SQL)
- **Status:** Separate system, not integrated with Firestore
- **Connection:** None (standalone)

**CopernicusAI Main System:**
- **Storage:** Firestore (`copernicusai` database)
- **Collections:** `research_papers`, `podcast_jobs`
- **Vector Search:** Implemented and ready
- **RAG:** Implemented and ready

### 4.2 Integration Options

#### Option A: Sync Content to Firestore (Recommended)

**Approach:** Create sync scripts that periodically copy content from PostgreSQL databases to Firestore.

**Pros:**
- Unified vector search across all content
- Leverages existing Firestore vector search
- Simple to implement
- Maintains separate systems for specialized use cases

**Cons:**
- Data duplication
- Need to keep systems in sync
- Additional storage costs

**Implementation:**
1. Create sync script for research papers
2. Create sync script for videos (metadata + transcripts)
3. Schedule periodic syncs (daily/weekly)
4. Generate embeddings during sync

#### Option B: Extend Vector Search to Query Multiple Sources

**Approach:** Modify vector search tools to query PostgreSQL databases directly.

**Pros:**
- No data duplication
- Single source of truth
- More complex to implement

**Cons:**
- Need to implement vector search in PostgreSQL (pgvector)
- More complex query logic
- Performance considerations

#### Option C: Hybrid Approach

**Approach:** Sync metadata to Firestore, keep full content in PostgreSQL.

**Pros:**
- Balance between options A and B
- Firestore for search, PostgreSQL for detailed queries

**Cons:**
- Most complex to implement
- Need to maintain two query paths

### 4.3 Recommended Approach: Option A (Sync to Firestore)

**Phase 1: Research Paper Sync**

1. **Create Sync Script**
   ```python
   # cloud-run-backend/scripts/sync_research_papers.py
   # - Query PostgreSQL for papers
   # - Generate embeddings using embedding_service
   # - Write to Firestore research_papers collection
   ```

2. **Schedule Sync**
   - Daily sync for new papers
   - Full sync on demand

3. **Handle Updates**
   - Track last sync timestamp
   - Only sync new/updated papers

**Phase 2: Video Sync**

1. **Create Sync Script**
   ```python
   # cloud-run-backend/scripts/sync_videos.py
   # - Query PostgreSQL for videos
   # - Generate embeddings from transcripts
   # - Write to Firestore (new collection: science_videos)
   ```

2. **Create Firestore Collection**
   - Collection: `science_videos`
   - Fields: video_id, title, description, transcript, disciplines, embedding, etc.

3. **Create Vector Index**
   ```bash
   gcloud firestore indexes composite create \
     --project=regal-scholar-453620-r7 \
     --database="copernicusai" \
     --collection-group=science_videos \
     --query-scope=COLLECTION \
     --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
   ```

**Phase 3: Update Vector Search Tools**

1. **Extend `search_semantic`**
   - Add `science_videos` to searchable content types
   - Include videos in results

2. **Update RAG Service**
   - Include video transcripts in context
   - Prioritize papers, then videos, then podcasts

---

## Part 5: Implementation Timeline

### Week 1: Assessment & Paper Ingestion

**Day 1-2: Assessment**
- [ ] Assess research paper database (count, categories)
- [ ] Assess video database (count, channels)
- [ ] Assess CopernicusAI Firestore (papers, podcasts)
- [ ] Document current state

**Day 3-4: Paper Ingestion**
- [ ] Run Phase 1: 200 mathematics papers
- [ ] Verify ingestion results
- [ ] Run Phase 2: 300 additional papers
- [ ] Final verification (500+ papers)

**Day 5: Paper Sync to Firestore**
- [ ] Create sync script for research papers
- [ ] Test sync with sample papers
- [ ] Run full sync
- [ ] Verify papers in Firestore with embeddings

### Week 2: Video Ingestion & Integration

**Day 1-2: Channel Expansion**
- [ ] Add 50+ channels to registry
- [ ] Verify channel registry
- [ ] Test ingestion with sample channels

**Day 3-4: Video Ingestion**
- [ ] Run initial ingestion (1000+ videos)
- [ ] Monitor progress and errors
- [ ] Verify transcripts and embeddings
- [ ] Quality checks

**Day 5: Video Sync & Integration**
- [ ] Create sync script for videos
- [ ] Create Firestore collection and index
- [ ] Run initial sync
- [ ] Update vector search tools
- [ ] Test unified search

### Week 3: Testing & Refinement

**Day 1-2: Vector Search Testing**
- [ ] Test semantic search across all content types
- [ ] Test similarity search
- [ ] Verify result quality
- [ ] Performance testing

**Day 3-4: RAG Testing**
- [ ] Test question answering with diverse queries
- [ ] Test concept explanation
- [ ] Test concept comparison
- [ ] Verify citation accuracy

**Day 5: Documentation & Cleanup**
- [ ] Document sync processes
- [ ] Create maintenance scripts
- [ ] Update documentation
- [ ] Plan ongoing ingestion schedule

---

## Part 6: Success Metrics

### Quantitative Metrics

- **Research Papers:** 500+ papers ingested
- **Videos:** 1000+ videos ingested
- **Embeddings:** 100% coverage for ingested content
- **Vector Search:** <2 second query latency
- **RAG Quality:** 80%+ relevant answers

### Qualitative Metrics

- **Search Relevance:** Results match query intent
- **RAG Accuracy:** Answers are factually correct
- **Content Diversity:** Good coverage across disciplines
- **System Stability:** No ingestion failures
- **Integration Quality:** Unified search works seamlessly

---

## Part 7: Maintenance & Ongoing Ingestion

### Research Papers

**Schedule:** Weekly
- Check for new papers in arXiv (mathematics)
- Ingest 50-100 new papers per week
- Sync to Firestore daily

### Videos

**Schedule:** Daily
- Check channels for new videos
- Ingest new videos from registered channels
- Sync to Firestore daily

### Monitoring

- Track ingestion success rates
- Monitor API quotas
- Check embedding generation success
- Verify sync completeness

---

## Part 8: Future Enhancements

### Additional Content Sources

1. **Scientific Images/Graphics**
   - Ingest figures from papers
   - Extract captions and metadata
   - Generate image embeddings (future)

2. **Additional Paper Sources**
   - PubMed/PMC (biology/medicine)
   - Semantic Scholar (all disciplines)
   - OpenAlex (comprehensive)

3. **Additional Video Sources**
   - Vimeo (academic content)
   - Academic conference recordings
   - Lecture series archives

### Advanced Features

1. **Cross-Modal Search**
   - Search papers by video content
   - Find videos related to papers
   - Unified knowledge graph

2. **Automated Quality Scoring**
   - Paper quality metrics
   - Video educational value
   - Content relevance scoring

3. **Personalization**
   - User-specific content recommendations
   - Learning path generation
   - Interest-based filtering

---

## Appendix: Commands Reference

### Research Paper Database

```bash
# Check current papers
cd /home/gdubs/copernicusai-research-metadata
python scripts/check_ingested_papers.py

# Ingest mathematics papers
python scripts/ingest_mathematics.py

# Test API
curl http://localhost:8000/api/v0/ingestion/arxiv/test
```

### Science Video Database

```bash
# Add channels
cd /home/gdubs/scienceviddb
npm run add-channels --workspace=packages/ingestion

# Ingest videos
npm run ingest:all

# Verify ingestion
npm run verify-ingestion --workspace=packages/ingestion
```

### CopernicusAI Firestore

```bash
# Check vector indexes
gcloud firestore indexes list --project=regal-scholar-453620-r7 --database=copernicusai

# Run sync scripts (after creation)
cd /home/gdubs/copernicus-web-public/cloud-run-backend
python scripts/sync_research_papers.py
python scripts/sync_videos.py
```

---

**Next Steps:**
1. Run assessment scripts to determine current state
2. Begin paper ingestion (500+ mathematics papers)
3. Expand video channel registry and ingest 1000+ videos
4. Create sync scripts to integrate with CopernicusAI Firestore
5. Test unified vector search and RAG

