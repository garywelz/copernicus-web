# API URL Fix for Local Testing

## Issue

The Knowledge Map was trying to connect to `http://localhost:8000` but the API isn't running locally - it's on Cloud Run.

## Fix Applied

Updated the default API URL in `KnowledgeMapView.tsx` to use the production Cloud Run endpoint:
- **Before:** `http://localhost:8000` (default)
- **After:** `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app` (default)

## Next Steps

1. **Refresh the browser** (the dev server should auto-reload)
2. **Navigate to:** `http://localhost:3000/knowledge-engine`
3. **Test the React removeChild error fix**

The Knowledge Map should now connect to the production API and load correctly.
