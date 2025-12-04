# Extraction Status - December 2025

## ✅ Completed (2/6 Phases)

### Phase 1: Subscriber Endpoints ✅
- **Status**: Complete
- **Router**: `endpoints/subscriber/routes.py`
- **Endpoints**: 9 endpoints
- **Registered**: Yes

### Phase 2: Podcast Generation Endpoints ✅
- **Status**: Complete  
- **Router**: `endpoints/podcast/routes.py`
- **Endpoints**: 2 endpoints
- **Registered**: Yes

## ⏳ Remaining (4 Phases + Cleanup)

### Phase 3: Public/Episode Endpoints (4 endpoints)
- GET `/api/public/podcasts`
- GET `/api/episodes`
- GET `/api/episodes/search`
- GET `/api/episodes/{episode_id}`

### Phase 4: Papers Endpoints (4 endpoints)
- POST `/api/papers/upload`
- GET `/api/papers/{paper_id}`
- POST `/api/papers/query`
- POST `/api/papers/{paper_id}/link-podcast/{podcast_id}`

### Phase 5: GLMP Endpoints (3 endpoints)
- GET `/api/glmp/processes`
- GET `/api/glmp/processes/{process_id}`
- GET `/api/glmp/processes/{process_id}/preview`

### Phase 6: Test Endpoint (1 endpoint)
- GET `/api/test`

### Final Cleanup
- Remove all old endpoints from main.py
- Remove duplicate helper functions
- Verify router registrations
- Test all endpoints

---

**Progress**: 2/6 phases complete (33%)
**Remaining**: ~12 endpoints + cleanup

*Status: Continuing systematically...*

