# Knowledge Map Fix Plan

## Issue Summary

1. **Backend Filtering Not Implemented** (Priority: HIGH)
   - User tried to search for "rhinovirus" papers from PubMed since Dec 1, 2025
   - Got default cached math graph instead
   - Backend API ignores filtering parameters

2. **React removeChild Error** (Priority: MEDIUM)
   - Error occurs but map does load
   - React DOM reconciliation conflict with Cytoscape
   - Not blocking functionality but annoying

## Fix Strategy

### Phase 1: Backend Filtering Implementation (HIGH PRIORITY)

**Current State:**
- Frontend sends: `content_types`, `disciplines`, `sources`, `date_start`, `date_end`, `keyword`
- Backend endpoint accepts: `max_papers`, `include_concepts`, `include_similarity`, `include_categories`, `format`, `force_rebuild`
- Backend ignores all filtering parameters

**Required Changes:**

1. **Update API Endpoint** (`endpoints/knowledge_map/routes.py`):
   - Add query parameters for filtering
   - Pass parameters to `build_graph()` method

2. **Update Service Method** (`services/knowledge_map_service.py`):
   - Add filtering parameters to `build_graph()` signature
   - Implement Firestore query filtering
   - Filter by:
     - Content types (papers/processes/videos/podcasts)
     - Disciplines (biology/chemistry/physics/math/cs/interdisciplinary)
     - Sources (pubmed/arxiv/nasa_ads/crossref/youtube/rss)
     - Date range (date_start, date_end)
     - Keywords (search in title/abstract/description)

3. **Paper Metadata Fields:**
   - Verify papers have: `source`, `discipline`, `publication_date`, `title`, `abstract`
   - Check Firestore collection structure

### Phase 2: React Error Fix (MEDIUM PRIORITY)

**Options:**
1. Iframe isolation (most isolated)
2. Error suppression (if error doesn't break functionality)
3. react-cytoscapejs wrapper (React-friendly alternative)
4. Accept error if functionality works (document as known issue)

## Implementation Order

1. ✅ Analyze current backend structure
2. ⏳ Implement backend filtering API parameters
3. ⏳ Implement Firestore query filtering
4. ⏳ Test backend filtering
5. ⏳ Deploy backend changes
6. ⏳ Test frontend with new backend
7. ⏳ Address React error (if still needed)
