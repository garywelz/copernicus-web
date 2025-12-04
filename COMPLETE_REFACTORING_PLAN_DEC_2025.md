# Complete Refactoring Plan - Final 23 Endpoints

## Overview

We're 98% complete with refactoring. This document outlines the systematic extraction of the final 23 endpoints to reach 100% completion.

## Remaining Endpoints: 23 Total

### Phase 1: Subscriber Endpoints (9) → `endpoints/subscriber/routes.py`
**Status:** 1/9 already in router (register)

1. ✅ POST `/api/subscribers/register` (already in router)
2. ⏳ POST `/api/subscribers/login`
3. ⏳ GET `/api/subscribers/profile/{subscriber_id}`
4. ⏳ PUT `/api/subscribers/profile/{subscriber_id}`
5. ⏳ GET `/api/subscribers/podcasts/{subscriber_id}`
6. ⏳ POST `/api/subscribers/podcasts/submit-to-rss`
7. ⏳ POST `/api/subscribers/password-reset-request`
8. ⏳ POST `/api/subscribers/password-reset`
9. ⏳ DELETE `/api/subscribers/podcasts/{podcast_id}`

### Phase 2: Podcast Generation Endpoints (2) → `endpoints/podcast/routes.py`
**Status:** 0/2 extracted

1. ⏳ POST `/generate-podcast`
2. ⏳ POST `/generate-podcast-with-subscriber`

### Phase 3: Public/Episode Endpoints (4) → `endpoints/public/routes.py`
**Status:** 0/4 extracted

1. ⏳ GET `/api/public/podcasts`
2. ⏳ GET `/api/episodes`
3. ⏳ GET `/api/episodes/search`
4. ⏳ GET `/api/episodes/{episode_id}`

### Phase 4: Papers Endpoints (4) → `endpoints/papers/routes.py`
**Status:** 0/4 extracted

1. ⏳ POST `/api/papers/upload`
2. ⏳ GET `/api/papers/{paper_id}`
3. ⏳ POST `/api/papers/query`
4. ⏳ POST `/api/papers/{paper_id}/link-podcast/{podcast_id}`

### Phase 5: GLMP Endpoints (3) → `endpoints/glmp/routes.py`
**Status:** 0/3 extracted

1. ⏳ GET `/api/glmp/processes`
2. ⏳ GET `/api/glmp/processes/{process_id}`
3. ⏳ GET `/api/glmp/processes/{process_id}/preview`

### Phase 6: Test Endpoint (1) → `endpoints/public/debug.py` or keep in main
**Status:** 0/1 extracted

1. ⏳ GET `/api/test`

---

## Extraction Strategy

### Approach
1. **One router at a time** - Complete each router before moving to next
2. **Maintain functionality** - All endpoints work identically
3. **Update imports** - Register routers in main.py
4. **Remove from main.py** - Clean up after each router is complete
5. **Test as we go** - Verify imports work after each phase

### Order of Execution
1. **Phase 1: Subscriber** (8 remaining endpoints)
2. **Phase 2: Podcast Generation** (2 endpoints)
3. **Phase 3: Public/Episode** (4 endpoints)
4. **Phase 4: Papers** (4 endpoints)
5. **Phase 5: GLMP** (3 endpoints)
6. **Phase 6: Test** (1 endpoint)
7. **Final Cleanup:** Remove old endpoints from main.py

---

## Success Criteria

✅ All 23 endpoints extracted to routers  
✅ All routers registered in main.py  
✅ main.py reduced to ~500-800 lines (just app setup)  
✅ No functionality broken  
✅ Clean, maintainable structure  

---

## Current Status

- **main.py:** 3,412 lines
- **Target:** ~500-800 lines
- **Remaining:** ~23 endpoints (~2,500-2,700 lines)
- **Progress:** 98% → 100%

---

*Plan created: December 2025*

