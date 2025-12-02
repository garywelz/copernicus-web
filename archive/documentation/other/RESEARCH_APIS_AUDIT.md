# Research APIs Audit - What's Available & What's Used

## APIs Loaded from Secret Manager

From `load_all_api_keys_from_secret_manager()`:

1. ✅ **PUBMED_API_KEY** - Used in `_search_pubmed()`
2. ✅ **NASA_ADS_TOKEN** - Used in `_search_nasa_ads()` (only for space topics)
3. ✅ **ZENODO_API_KEY** - Used in `_search_zenodo()`
4. ✅ **NEWS_API_KEY** - Used in `_search_news_api()` (only if `include_social_trends=True`)
5. ⚠️ **YOUTUBE_API_KEY** - **NOT USED in research pipeline!**
6. ✅ **OPENROUTER_API_KEY** - Used for processing user links
7. ✅ **CORE_API_KEY** - Used in `_search_core()` (CORE aggregator from UK)

## Public APIs (No Key Needed)

1. ✅ **ArXiv** - Used in `_search_arxiv()` (just fixed!)
2. ✅ **bioRxiv** - Used in `_search_biorxiv()`

---

## Issues Found

### 1. YouTube API Not Used
**YOUTUBE_API_KEY** is loaded but never used in research. Could be useful for:
- Educational video transcripts
- Conference presentations
- Academic YouTube channels

### 2. CORE API Usage
**CORE is being used** but could be optimized:
- CORE aggregates from 10,000+ repositories worldwide
- Excellent for open access papers
- Should work great for mathematics topics
- Currently searches all fields - could add subject filtering

### 3. Missing Subject-Specific Logic
Currently:
- NASA ADS only used for space/astronomy
- Could add more subject-specific routing

---

## Recommendations

### 1. Optimize CORE for Mathematics
CORE supports subject filtering - we should use it:
```python
# Add subject filtering to CORE search
params = {
    "q": query,
    "limit": 20,
    "page": 1,
    "subject": "Mathematics"  # Filter by subject
}
```

### 2. Add Subject-Based Routing
Route to best APIs based on topic:
- Mathematics → ArXiv (math.NT, math.AC, etc.), CORE, Zenodo
- Biology → PubMed, bioRxiv, CORE
- Physics → ArXiv, NASA ADS, CORE
- etc.

### 3. Consider Adding YouTube (if useful)
Could search academic YouTube channels for:
- Conference presentations
- Lecture series
- Educational content

---

## Current Search Flow for "Number Theory"

1. ✅ PubMed (might not find much - biomedical focus)
2. ✅ ArXiv (should find lots - just fixed!)
3. ✅ bioRxiv (won't find much - biology preprints)
4. ✅ Zenodo (might find some)
5. ✅ CORE (should find lots - aggregates many math repositories)
6. ❌ NASA ADS (skipped - not space topic)

**Total: 5 sources searching, should get good results now!**

---

## Next Steps

1. ✅ Fix ArXiv (DONE)
2. 🔄 Optimize CORE for subject filtering
3. 🔄 Add better logging to see which APIs return results
4. ⚠️ Consider adding YouTube search
5. 🔄 Add subject-based routing for better results

---

**Would you like me to:**
1. Optimize CORE search for mathematics topics?
2. Add subject-based routing?
3. Add YouTube API integration?
4. Improve logging to see which APIs are actually returning results?



