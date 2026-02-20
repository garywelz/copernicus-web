# Mathematics Knowledge Map Roadmap

## Current Status

### Mathematics Content
- **Papers:** ~490 total (need to verify how many are mathematics)
- **Math Processes:** 5 (from Programming Framework)
- **Total:** ~495 mathematics-related items

### Assessment
For a meaningful mathematics knowledge map, we need:
1. **More papers** - Current count is too low for rich graph visualization
2. **Citation data** - To build paper-to-paper relationships
3. **Concept extraction** - To identify mathematical concepts and their connections
4. **Graph structure** - To visualize relationships

---

## Recommended Next Steps

### Option A: Ingest More Papers First (Recommended) ✅

**Why:**
- More papers = more nodes in the knowledge graph
- More papers = more citation relationships
- Better demonstrates scale and value
- Easier to see patterns and clusters

**Target:** 10,000-20,000 mathematics papers from arXiv

**Benefits:**
- Rich citation networks
- Clear topic clusters
- More interesting visualization
- Better for demo purposes

**Timeline:** 1-2 weeks for ingestion + embedding

### Option B: Build Knowledge Map Infrastructure First

**Why:**
- Test with current content
- Validate approach
- Iterate on visualization

**Risks:**
- Limited content = less impressive demo
- Fewer relationships to visualize
- May need to rebuild when more content is added

---

## Recommended Approach: Ingest Papers First

### Step 1: Bulk Ingest Mathematics Papers (1-2 weeks)

**Target:** 10,000-20,000 papers

**Strategy:**
1. Focus on high-citation papers (2015-2025)
2. Cover all major math categories:
   - Algebra (math.RA, math.AC, math.GR)
   - Analysis (math.CA, math.FA, math.AP)
   - Geometry (math.DG, math.GT, math.AG)
   - Topology (math.AT, math.KT)
   - Number Theory (math.NT)
   - Logic (math.LO)
   - Combinatorics (math.CO)
   - Probability (math.PR)
   - And more...

**Implementation:**
- Create bulk ingestion script
- Use arXiv API + Semantic Scholar for citations
- Filter by citation count (10+ minimum, 50+ preferred)
- Generate embeddings during ingestion
- Sync to Firestore

**Expected Results:**
- 10,000-20,000 mathematics papers
- Citation relationships
- Rich topic coverage
- Ready for knowledge map construction

### Step 2: Extract Relationships (2-3 weeks)

**What to Extract:**
1. **Citation Relationships**
   - Paper A cites Paper B
   - Build citation graph

2. **Concept Relationships**
   - Extract mathematical concepts from papers
   - Link papers that share concepts
   - Link processes to concepts

3. **Topic Relationships**
   - Papers in same arXiv category
   - Papers with similar embeddings (already have this)
   - Papers citing same references

**Implementation:**
- Use LLM to extract concepts from abstracts/titles
- Parse citation data from papers
- Use vector similarity for implicit relationships
- Store relationships in Firestore or graph database

### Step 3: Build Graph Structure (1-2 weeks)

**Nodes:**
- Papers (with metadata: title, authors, category, citations)
- Concepts (extracted mathematical concepts)
- Processes (math processes from Programming Framework)
- Authors (if available)

**Edges:**
- Cites (paper → paper)
- Contains (paper → concept)
- Implements (process → concept)
- Similar (any → any, based on embeddings)
- Same Topic (paper → paper, based on category)

**Storage Options:**
- **Option 1:** Firestore with relationship documents
- **Option 2:** Neo4j graph database
- **Option 3:** In-memory graph (for visualization)

### Step 4: Create Visualization (2-3 weeks)

**Tools:**
- D3.js for web visualization
- Cytoscape.js for graph visualization
- NetworkX (Python) for analysis

**Features:**
- Interactive node-link diagram
- Filter by content type
- Filter by similarity threshold
- Highlight paths between concepts
- Show clusters of related content
- Search and highlight nodes

---

## Why Ingest Papers First?

### Advantages:
1. **Better Demo**
   - 10,000+ papers = impressive scale
   - Rich, complex knowledge graph
   - Clear patterns and clusters

2. **More Relationships**
   - More papers = more citations
   - More concepts to extract
   - More interesting connections

3. **Validates Approach**
   - Test knowledge map on real scale
   - See if relationships make sense
   - Identify issues early

4. **One-Time Effort**
   - Ingest once, use forever
   - Can add more papers later
   - Foundation for future work

### Timeline Comparison:

**Option A (Papers First):**
- Week 1-2: Ingest 10K-20K papers
- Week 3-5: Extract relationships
- Week 6-7: Build graph
- Week 8-10: Visualization
- **Total: 8-10 weeks**

**Option B (Infrastructure First):**
- Week 1-3: Build infrastructure with 490 papers
- Week 4-5: Test and iterate
- Week 6-7: Ingest 10K-20K papers (may need to rebuild)
- Week 8-10: Re-test and finalize
- **Total: 8-10 weeks (but may need rework)**

---

## Recommendation: Ingest Papers First ✅

**Next Steps:**
1. ✅ Create bulk paper ingestion script for arXiv mathematics
2. ✅ Ingest 10,000-20,000 mathematics papers
3. ✅ Extract citation data
4. ✅ Generate embeddings
5. ✅ Sync to Firestore
6. Then proceed with knowledge map construction

**Benefits:**
- One-time ingestion effort
- Better foundation for knowledge map
- More impressive demo
- Richer relationships to visualize

---

## Implementation Plan for Paper Ingestion

### Phase 1: Setup (2-3 days)
1. Create bulk ingestion script
2. Set up Semantic Scholar API for citations
3. Test with 100 papers

### Phase 2: Ingestion (1-2 weeks)
1. Ingest 10,000 papers (Week 1)
2. Monitor and optimize
3. Scale to 20,000 if needed (Week 2)

### Phase 3: Verification (2-3 days)
1. Verify embeddings
2. Check citation data
3. Validate search quality

**Total Time:** 2-3 weeks for paper ingestion

---

## After Paper Ingestion

Once we have 10,000-20,000 mathematics papers:

1. **Extract Relationships** (2-3 weeks)
   - Citation graph
   - Concept extraction
   - Topic clustering

2. **Build Knowledge Map** (3-4 weeks)
   - Graph structure
   - Visualization
   - Interactive features

3. **Demo Ready** (1 week)
   - Polish visualization
   - Create demo scenarios
   - Document usage

**Total Timeline:** 8-10 weeks from start to demo-ready knowledge map

---

## Answer: Yes, Ingest More Papers First! ✅

**Recommendation:** Start with bulk ingestion of 10,000-20,000 mathematics papers from arXiv. This will:
- Provide a solid foundation for the knowledge map
- Create rich citation networks
- Enable better visualization
- Make for a more impressive demo

Then proceed with relationship extraction and knowledge map construction.

