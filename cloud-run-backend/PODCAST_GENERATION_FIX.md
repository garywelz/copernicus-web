# Podcast Generation Failure Fix

## Issue Identified

**Problem:** All podcast generation jobs are failing with error:
```
404 models/gemini-pro is not found for API version v1beta, or is not supported for generateContent.
```

**Root Cause:** The code was using the deprecated `gemini-pro` model which is no longer available in Google's API.

**Affected Files:**
1. `cloud-run-backend/services/podcast_generation_service.py` (line 1161)
2. `cloud-run-backend/paper_processor.py` (line 89)

## Fix Applied

Updated both files to use current Gemini models:
- **Primary:** `gemini-1.5-flash` (faster, cheaper)
- **Fallback:** `gemini-1.5-pro` (if flash not available)

## Research Phase Status

✅ **Research phase is working correctly:**
- Found 25 research sources for "Topological Data Analysis"
- Found 25 research sources for "Applications of Topology in Data Science"
- Research quality scores: 5.0-6.0 (good)

The failure occurs **after** research completes, during content generation.

## Next Steps

1. **Deploy the fix** to Cloud Run:
   ```bash
   cd cloud-run-backend
   gcloud builds submit --config cloudbuild.yaml .
   ```

2. **Test with a new podcast request** on "Topological Data Analysis" or "Applications of Topology in Data Science"

3. **Monitor logs** to ensure the new model works correctly

## Additional Notes

- The Google AI API key is properly configured (research phase works)
- Vertex AI may be disabled (`DISABLE_VERTEX_AI=1`), which is why it's falling back to Google AI API
- The fallback chain should now work: Vertex AI → Google AI API with current models
