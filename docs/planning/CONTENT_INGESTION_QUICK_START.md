# Content Ingestion Quick Start Guide

**Goal:** Ingest 500+ papers and 1000+ videos to enable vector search and RAG testing

---

## Step 1: Assess Current State (5 minutes)

Run the assessment script to see what you currently have:

```bash
cd /home/gdubs/copernicus-web-public
python scripts/assess_content_status.py
```

This will show:
- Current paper count in PostgreSQL
- Current paper count in Firestore
- Current podcast count
- Embedding coverage

**Expected Output:**
- Research papers: Likely <100 (need 500+)
- Videos: Unknown (need 1000+)
- Podcasts: 45 (already indexed)

---

## Step 2: Ingest Research Papers (1-2 days)

### Quick Start: Ingest 500 Mathematics Papers

```bash
cd /home/gdubs/copernicusai-research-metadata

# Option 1: Interactive script (recommended)
python scripts/ingest_mathematics.py
# Select: "All categories (small batch each)"
# This will ingest ~450 papers across 9 categories

# Option 2: API endpoint (if server is running)
curl -X POST "http://localhost:8000/api/v0/ingestion/arxiv?search_query=cat:math.*&max_results=100"
```

### Verify Results

```bash
python scripts/check_ingested_papers.py
```

**Target:** 500+ papers total, with good distribution across math categories

---

## Step 3: Sync Papers to Firestore (30 minutes)

After ingesting papers, sync them to CopernicusAI Firestore for vector search:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend

# Create sync script (see CONTENT_INGESTION_PLAN.md for details)
# Then run:
python scripts/sync_research_papers.py
```

This will:
- Query PostgreSQL for all papers
- Generate embeddings using Vertex AI
- Write to Firestore `research_papers` collection

---

## Step 4: Expand Video Channels (1 day)

### Add Channels to Registry

```bash
cd /home/gdubs/scienceviddb

# Add curated channels
npm run add-channels --workspace=packages/ingestion
npm run add-biology-channels --workspace=packages/ingestion
npm run add-research-channels --workspace=packages/ingestion

# Or create comprehensive channel list (see CONTENT_INGESTION_PLAN.md)
```

**Target:** 50+ channels across all disciplines

### Verify Channels

Check that channels were added successfully (query database or use verification script)

---

## Step 5: Ingest Videos (1-2 days)

```bash
cd /home/gdubs/scienceviddb

# Ingest all registered channels
npm run ingest:all

# Or ingest specific channels
npm run ingest -- --channel <CHANNEL_ID>
```

**Target:** 1000+ videos with transcripts and embeddings

### Verify Results

```bash
npm run verify-ingestion --workspace=packages/ingestion
```

---

## Step 6: Sync Videos to Firestore (30 minutes)

After ingesting videos, sync them to Firestore:

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend

# Create sync script (see CONTENT_INGESTION_PLAN.md)
# Create Firestore collection and index
# Then run:
python scripts/sync_videos.py
```

This will:
- Query PostgreSQL for all videos
- Generate embeddings from transcripts
- Write to Firestore `science_videos` collection

**Don't forget to create the vector index:**

```bash
gcloud firestore indexes composite create \
  --project=regal-scholar-453620-r7 \
  --database="copernicusai" \
  --collection-group=science_videos \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
```

---

## Step 7: Test Vector Search & RAG (30 minutes)

Once content is synced, test the new capabilities:

### Test Semantic Search

```python
# In MCP client (Cursor/Claude Desktop)
search_semantic(query="Lac Operon", limit=5)
search_semantic(query="quantum mechanics", limit=10)
```

### Test RAG

```python
# In MCP client
answer_with_rag(question="What is the Lac Operon?")
explain_concept(concept="quantum entanglement")
compare_concepts(concept1="classical mechanics", concept2="quantum mechanics")
```

**Expected Results:**
- Relevant papers, videos, and podcasts returned
- Answers are accurate and well-cited
- Response time <2 seconds

---

## Timeline Summary

| Task | Time | Priority |
|------|------|----------|
| Assess current state | 5 min | High |
| Ingest 500 papers | 1-2 days | High |
| Sync papers to Firestore | 30 min | High |
| Expand video channels | 1 day | High |
| Ingest 1000 videos | 1-2 days | High |
| Sync videos to Firestore | 30 min | High |
| Test vector search & RAG | 30 min | High |
| **Total** | **4-6 days** | |

---

## Troubleshooting

### Papers Not Ingesting

- Check database connection
- Verify arXiv API is accessible
- Check rate limiting (3-second delays)
- Review error logs

### Videos Not Ingesting

- Check YouTube API key
- Verify channel registry
- Check API quota limits
- Review ingestion logs

### Embeddings Not Generating

- Verify Vertex AI is initialized
- Check API credentials
- Review embedding service logs
- Test with small batch first

### Sync Failures

- Verify Firestore connection
- Check embedding service availability
- Review sync script logs
- Test with single item first

---

## Next Steps After Ingestion

1. **Set Up Ongoing Ingestion**
   - Schedule weekly paper ingestion
   - Schedule daily video updates
   - Automate sync processes

2. **Monitor Quality**
   - Track ingestion success rates
   - Monitor embedding generation
   - Verify search result quality

3. **Expand Content Sources**
   - Add more paper sources (PubMed, Semantic Scholar)
   - Add more video sources (Vimeo, academic channels)
   - Plan for image/graphics ingestion

---

## Reference Documents

- **Full Plan:** `docs/planning/CONTENT_INGESTION_PLAN.md`
- **Assessment Script:** `scripts/assess_content_status.py`
- **Research Metadata DB:** `/home/gdubs/copernicusai-research-metadata`
- **Science Video DB:** `/home/gdubs/scienceviddb`

---

**Ready to start?** Begin with Step 1 (assessment) to see your current state!

