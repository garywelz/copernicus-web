# Endpoint Extraction Plan - December 2025

## 📊 Remaining Endpoints: 23 Total

### 1. Subscriber Endpoints (9) → `endpoints/subscriber/routes.py`
- ✅ POST `/api/subscribers/register` (already started)
- POST `/api/subscribers/login`
- GET `/api/subscribers/profile/{subscriber_id}`
- PUT `/api/subscribers/profile/{subscriber_id}`
- GET `/api/subscribers/podcasts/{subscriber_id}`
- POST `/api/subscribers/podcasts/submit-to-rss`
- POST `/api/subscribers/password-reset-request`
- POST `/api/subscribers/password-reset`
- DELETE `/api/subscribers/podcasts/{podcast_id}`

### 2. Podcast Generation Endpoints (2) → `endpoints/podcast/routes.py`
- POST `/generate-podcast`
- POST `/generate-podcast-with-subscriber`

### 3. Public/Episode Endpoints (4) → `endpoints/public/routes.py`
- GET `/api/public/podcasts`
- GET `/api/episodes`
- GET `/api/episodes/search`
- GET `/api/episodes/{episode_id}`

### 4. Papers Endpoints (4) → `endpoints/papers/routes.py`
- POST `/api/papers/upload`
- GET `/api/papers/{paper_id}`
- POST `/api/papers/query`
- POST `/api/papers/{paper_id}/link-podcast/{podcast_id}`

### 5. GLMP Endpoints (3) → `endpoints/glmp/routes.py`
- GET `/api/glmp/processes`
- GET `/api/glmp/processes/{process_id}`
- GET `/api/glmp/processes/{process_id}/preview`

### 6. Test Endpoint (1) → `endpoints/public/debug.py` or new `endpoints/test/routes.py`
- GET `/api/test`

---

## 🎯 Extraction Order

1. **Subscriber endpoints** (9) - Already partially started
2. **Public/Episode endpoints** (4) - Logical grouping
3. **Podcast generation endpoints** (2) - Core functionality
4. **Papers endpoints** (4) - Feature group
5. **GLMP endpoints** (3) - Feature group
6. **Test endpoint** (1) - Quick win

---

## ✅ Success Criteria

- main.py reduced to ~500-800 lines
- All endpoints in dedicated routers
- All routers registered in main.py
- No functionality broken
- Clean, maintainable structure

---

*Plan created: December 2025*

