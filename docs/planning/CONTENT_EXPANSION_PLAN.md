# Content Expansion Plan

## Quick Reference Guide for Adding Content

### 1. Research Papers

**Current:** 490 papers  
**Target:** 1000+ papers

**Steps:**
```bash
# 1. Ingest papers into PostgreSQL
cd /home/gdubs/copernicusai-research-metadata
source venv/bin/activate
python3 scripts/ingest_mathematics.py  # Or create new scripts for other categories

# 2. Sync to Firestore with embeddings
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/sync_research_papers.py
```

**Categories to Target:**
- Mathematics: `math.*` (all subcategories)
- Biology: `q-bio.*`, `q-bio.BM`, `q-bio.CB`
- Chemistry: `physics.chem-ph`
- Physics: `physics.bio-ph`, `cond-mat.*`

### 2. Videos

**Current:** 0 synced (100+ in database)  
**Target:** All videos synced

**Steps:**
```bash
# 1. Set up Cloud SQL Proxy (if needed)
cloud-sql-proxy regal-scholar-453620-r7:us-central1:scienceviddb

# 2. Sync videos
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/sync_videos.py
```

### 3. GLMP Processes

**Current:** 115 processes  
**Target:** 200+ processes

**Steps:**
1. Add JSON files to GCS: `gs://regal-scholar-453620-r7-podcast-storage/glmp-database/`
2. Run sync:
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source venv/bin/activate
python3 scripts/sync_glmp_processes.py
```

### 4. Podcasts

**Current:** 47 podcasts  
**Target:** 100+ podcasts

**Steps:**
- Use existing podcast generation pipeline
- Auto-embedding is already integrated
- New podcasts automatically get embeddings

---

## Fine-Tuning Content

### Improving Embeddings

**Current Approach:**
- Papers: Title + Abstract + Keywords
- GLMP: Title + Description + Entities + Mermaid snippet
- Podcasts: Title + Description + Transcript excerpt

**Improvements:**
1. **Better Text Extraction**
   - Papers: Include full text if available
   - GLMP: Include full Mermaid code (truncated currently)
   - Podcasts: Use full transcript

2. **Metadata Enhancement**
   - Add discipline tags
   - Add topic tags
   - Add relationship metadata

3. **Multi-Modal Embeddings**
   - Combine text + image embeddings (when images added)
   - Use specialized embeddings for different content types

---

## Future Content Types Roadmap

### Phase 1: Images (Next 2-3 Weeks)

**Tasks:**
1. Create `scripts/sync_images.py`
2. Create Firestore collection `images`
3. Add image embedding service (Vertex AI Vision)
4. Create vector index
5. Add image search to vector_search.py

**Image Sources:**
- Extract from papers (diagrams, charts)
- Extract from GLMP processes (flowchart images)
- External scientific image databases

### Phase 2: Animations (Next Month)

**Tasks:**
1. Create animation sync script
2. Key frame extraction
3. Multi-frame embedding
4. Temporal search

### Phase 3: Interactive Files (Next 2 Months)

**Tasks:**
1. Jupyter notebook integration
2. Interactive visualization storage
3. Code + data extraction
4. Embedding from extracted content

---

## Content Quality Checklist

For each content type, ensure:
- ✅ Unique ID
- ✅ Title
- ✅ Description/Abstract
- ✅ Source metadata
- ✅ Embedding generated
- ✅ Vector type (not list)
- ✅ Searchable in Firestore
- ✅ Proper categorization

