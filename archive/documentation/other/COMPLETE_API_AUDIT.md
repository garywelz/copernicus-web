# Complete Research API Audit

## ✅ APIs Loaded from Secret Manager

### Research APIs (Currently Used)
1. **PUBMED_API_KEY** ✅ Used - Biomedical literature
2. **NASA_ADS_TOKEN** ✅ Used - Astronomy/astrophysics (space topics only)
3. **ZENODO_API_KEY** ✅ Used - Open research data repository
4. **NEWS_API_KEY** ✅ Used - News articles (if `include_social_trends=True`)
5. **CORE_API_KEY** ✅ Used - UK's CORE aggregator (10,000+ repositories!)
6. **OPENROUTER_API_KEY** ✅ Used - For processing user links

### APIs Loaded But NOT Used
7. **YOUTUBE_API_KEY** ⚠️ NOT USED - Could search academic YouTube channels

### LLM APIs
8. **GOOGLE_AI_API_KEY** ✅ Used - Content generation
9. **OPENAI_API_KEY** ✅ Used - Image generation (DALL-E)

---

## 🔍 Public APIs (No Key Needed)

1. **ArXiv** ✅ Used - Preprints (just fixed!)
2. **bioRxiv** ✅ Used - Biology preprints
3. **PubMed** ✅ Used - Public API (key might help with rate limits)

---

## 📊 CORE Aggregator - Deep Dive

**CORE** is the UK's aggregator that searches:
- 10,000+ institutional repositories worldwide
- Open access papers from major publishers
- Institutional repositories (universities, research centers)
- Subject-specific repositories

### CORE API Capabilities (per docs)
- Subject filtering
- Repository filtering  
- Full-text search
- Metadata extraction
- **Excellent for mathematics!**

### Current Implementation
```python
# Currently searches all repositories
params = {
    "q": query,
    "limit": 20,
    "page": 1
}
```

### Could Optimize For:
- Subject-based filtering
- Repository filtering (e.g., math-specific repos)
- Date filtering for recent papers

---

## 🔧 Optimizations Needed

### 1. CORE Subject Filtering
Add subject filter for better results:
```python
# For mathematics topics
params = {
    "q": query,
    "limit": 20,
    "page": 1,
    "subject": "Mathematics"  # CORE supports subject filtering
}
```

### 2. Subject-Based Routing
Route to best APIs based on topic:
- **Mathematics** → ArXiv (math.NT, etc.), CORE, Zenodo
- **Biology** → PubMed, bioRxiv, CORE
- **Physics** → ArXiv, NASA ADS, CORE
- **Space** → NASA ADS, ArXiv, CORE

### 3. Better Logging
Track which APIs return results:
- Log source counts per API
- Identify which APIs are working
- Debug when 0 sources found

### 4. YouTube Integration (Optional)
If YOUTUBE_API_KEY is available, could search:
- Conference presentations
- Lecture series
- Academic channels

---

## 📈 Expected Results After Fixes

For **"number theory"** query:
1. ✅ ArXiv `math.NT` category → 50+ papers
2. ✅ CORE (mathematics filter) → 20+ papers  
3. ✅ Zenodo → 5-10 papers
4. ❌ PubMed → 0-2 papers (biomedical focus)
5. ❌ bioRxiv → 0 papers (biology preprints)
6. ❌ NASA ADS → Skipped (not space)

**Total Expected: 75+ sources!**

---

## 🎯 Immediate Actions

1. ✅ Fix ArXiv search (DONE)
2. 🔄 Optimize CORE for subject filtering
3. 🔄 Add subject-based routing
4. 🔄 Improve logging per API
5. ⚠️ Consider YouTube search

---

**CORE is already working - let's just optimize it for mathematics!**



