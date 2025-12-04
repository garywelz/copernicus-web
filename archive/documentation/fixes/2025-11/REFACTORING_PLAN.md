# Refactoring Plan for main.py (8,166 lines)

## 📊 Current Structure Analysis

- **Total lines**: 8,166
- **Endpoints**: ~49 endpoints
- **Admin endpoints**: 21
- **Subscriber endpoints**: ~8
- **Public endpoints**: ~5
- **Functions/Classes**: 118

## 🎯 Target Structure

```
cloud-run-backend/
├── main.py                           (~500 lines - FastAPI app setup only)
├── config/
│   ├── __init__.py
│   ├── constants.py                  (~200 lines - RSS config, voices, etc.)
│   └── database.py                   (~100 lines - Firestore setup)
├── utils/
│   ├── __init__.py
│   ├── logging.py                    (~100 lines - StructuredLogger)
│   ├── helpers.py                    (~500 lines - Helper functions)
│   └── auth.py                       (~100 lines - Auth functions)
├── services/
│   ├── __init__.py
│   ├── audio_service.py              (~500 lines - Audio generation)
│   ├── thumbnail_service.py          (~400 lines - Thumbnail generation)
│   └── rss_service.py                (~800 lines - RSS feed management)
├── endpoints/
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── podcasts.py               (~1500 lines - Podcast admin endpoints)
│   │   ├── subscribers.py            (~400 lines - Subscriber admin endpoints)
│   │   └── rss.py                    (~800 lines - RSS admin endpoints)
│   ├── subscriber/
│   │   ├── __init__.py
│   │   └── routes.py                 (~600 lines - Subscriber endpoints)
│   └── public/
│       ├── __init__.py
│       └── routes.py                 (~300 lines - Public endpoints)
└── core/
    ├── __init__.py
    └── podcast_generation.py         (~2000 lines - Main podcast generation logic)
```

## 📋 Refactoring Steps

### Phase 1: Extract Configuration & Utilities
1. Create `config/constants.py` - Move all constants
2. Create `utils/logging.py` - Move StructuredLogger
3. Create `utils/helpers.py` - Move helper functions
4. Create `utils/auth.py` - Move auth functions

### Phase 2: Extract Services
1. Create `services/audio_service.py` - Audio generation
2. Create `services/thumbnail_service.py` - Thumbnail generation
3. Create `services/rss_service.py` - RSS feed operations

### Phase 3: Extract Endpoints
1. Create `endpoints/admin/podcasts.py` - Admin podcast endpoints
2. Create `endpoints/admin/subscribers.py` - Admin subscriber endpoints
3. Create `endpoints/admin/rss.py` - Admin RSS endpoints
4. Create `endpoints/subscriber/routes.py` - Subscriber endpoints
5. Create `endpoints/public/routes.py` - Public endpoints

### Phase 4: Extract Core Logic
1. Create `core/podcast_generation.py` - Main generation logic

### Phase 5: Update main.py
1. Keep only FastAPI app setup
2. Import and register all endpoints
3. Keep middleware setup

## ⚠️ Important Considerations

1. **Maintain all imports** - Ensure all dependencies are available
2. **Keep functionality identical** - No behavior changes
3. **Test after each phase** - Verify nothing breaks
4. **Update imports in other files** - Check for dependencies

## ✅ Success Criteria

- [ ] main.py is < 500 lines
- [ ] All endpoints still work
- [ ] No functionality lost
- [ ] All imports resolved
- [ ] Code is more maintainable

