# Knowledge Map Troubleshooting

## Status

✅ **Embedding Service:** Working with OpenAI (1536 dimensions)
✅ **Header:** Fixed in code (needs frontend rebuild)
⚠️ **Knowledge Map:** Uses existing Firestore embeddings (should work)

## Header Fix

The header has been updated in `app/knowledge-engine/page.tsx` to:
**"CopernicusAI Knowledge Engine: Research Tools"**

**To see the change:**
- If using Next.js dev server: Restart it
- If deployed: Rebuild and redeploy the frontend

## Knowledge Map Issue

The knowledge map uses **existing embeddings** from Firestore for similarity search, so it should work regardless of which provider is active.

### Possible Issues:

1. **Dimension Mismatch (Unlikely)**
   - Existing embeddings in Firestore: 768 dimensions (Vertex AI)
   - New embeddings (if generated): 1536 dimensions (OpenAI)
   - **Impact:** Knowledge map uses existing embeddings, so this shouldn't matter

2. **Service Initialization**
   - Knowledge map service now handles missing embedding service gracefully
   - Should work even if embedding service fails

3. **Caching**
   - Knowledge map caches the graph in memory
   - Try clicking "Reload Map" button to force rebuild

4. **Timeout**
   - Knowledge map has 30-second timeout
   - Large graphs might take longer

## Testing

### Test Embedding Service
```python
from services.embedding_service import get_embedding_service
service = get_embedding_service()
print(f"Provider: {service.provider}")  # Should show "openai"
```

### Test Knowledge Map API
```bash
curl "https://copernicus-podcast-api-204731194849.us-central1.run.app/api/knowledge-map/graph?max_papers=10"
```

### Check Logs
```bash
gcloud run services logs read copernicus-podcast-api \
  --region=us-central1 \
  --project=regal-scholar-453620-r7 \
  --limit=50 | grep -i "knowledge"
```

## Next Steps

1. **Frontend:** Rebuild/redeploy to see header change
2. **Knowledge Map:** Check browser console for errors
3. **API:** Test the knowledge map endpoint directly
4. **Logs:** Check service logs for errors

---

**Note:** The knowledge map should work fine since it uses existing Firestore embeddings, not generating new ones.
