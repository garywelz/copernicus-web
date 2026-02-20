# Deploy Script Length Validation Fix

## Changes Made

Updated script length validation to be more lenient to prevent failures when scripts are close to the minimum but slightly under.

### Files Modified:
1. **`utils/script_validation.py`**
   - Changed minimum word count from 90% to 80% of target
   - For "5-10 minutes": 675 words → 600 words minimum
   - This prevents failures for scripts like 603 words that are close but slightly under

2. **`podcast_research_integrator.py`**
   - Updated target calculation to divide by 0.8 instead of 0.9

3. **`services/podcast_generation_service.py`**
   - Updated target_words calculation to divide by 0.8 instead of 0.9

## Impact

- **Before**: Scripts needed 675+ words for "5-10 minutes" (90% of 750)
- **After**: Scripts need 600+ words for "5-10 minutes" (80% of 750)
- **Result**: Scripts that are close but slightly under will now pass validation

## Deployment

### Option 1: Use deploy.sh (Recommended)
```bash
cd cloud-run-backend
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Direct gcloud deploy
```bash
cd cloud-run-backend
gcloud builds submit --config cloudbuild.yaml .
```

### Option 3: Quick deploy (if already configured)
```bash
cd cloud-run-backend
gcloud run deploy copernicus-podcast-api \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout 900 \
  --memory 2Gi \
  --cpu 2
```

## Verification

After deployment, test with a podcast that previously failed:
- Topic: "AI for Scientific Discovery and Hypothesis Generation"
- Duration: "5-10 minutes"
- A script with 603 words should now pass (previously failed)

## Rollback

If needed, revert the changes:
```bash
cd cloud-run-backend
git checkout utils/script_validation.py podcast_research_integrator.py services/podcast_generation_service.py
# Then redeploy
```

