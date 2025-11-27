# Commit and Deploy Instructions

## Summary of Changes Ready to Commit

### Main Changes
1. **`cloud-run-backend/main.py`** - Major updates:
   - Gemini 3.0 configuration with proper fallbacks
   - All print statements replaced with structured logging
   - Better error handling

2. **Archive directory** - Old files organized:
   - `archive/old_main_files/` - 9 old main_*.py files
   - `archive/one_off_scripts/` - 27 one-off scripts moved

3. **Documentation** - Summary files created

4. **`.gitignore`** - Updated to exclude diagnostic scripts and build artifacts

---

## Step 1: Stage Changes

```bash
# Add the main changes
git add cloud-run-backend/main.py
git add archive/
git add *.md
git add .gitignore

# Remove deleted files (they're now in archive)
git add -u
```

---

## Step 2: Review What Will Be Committed

```bash
git status
```

You should see:
- Modified: `cloud-run-backend/main.py`
- Added: `archive/` directory
- Added: Documentation files (*.md)
- Modified: `.gitignore`
- Deleted: Old files (now in archive)

---

## Step 3: Commit

```bash
git commit -m "feat: Configure Gemini 3.0 priority and replace all print statements with structured logging

- Updated all model fallback chains to prioritize Gemini 3.0
  * Vertex AI: models/gemini-3.0-flash → 3.0-pro → 2.5-flash → 2.0-flash-exp
  * Google AI API: gemini-3.0-flash → 3.0-pro → 2.0-flash-exp → 1.5-pro
- Fixed invalid model name references (removed gemini-1.5-flash)
- Replaced all ~170 print statements with structured logging (255+ logger calls)
- Added comprehensive error handling with multiple fallback attempts
- Archived old main_*.py files to archive/old_main_files/
- Archived one-off scripts to archive/one_off_scripts/
- Added deployment documentation and diagnostic tools

Breaking changes: None
Improves observability and ensures we're using latest Gemini models."
```

---

## Step 4: Push to GitHub

```bash
git push origin main
```

This will trigger deployment if you have GitHub Actions or Cloud Build configured.

---

## Step 5: Deploy to Cloud Run

### Option A: Automatic (if configured)
- Push will automatically trigger Cloud Run deployment

### Option B: Manual via gcloud CLI
```bash
gcloud run deploy copernicus-podcast-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --project regal-scholar-453620-r7 \
  --allow-unauthenticated
```

### Option C: Manual via Cloud Console
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select `copernicus-podcast-api` service
3. Click "Deploy new revision"
4. Configure as needed
5. Click "Deploy"

---

## Step 6: Verify Deployment

After deployment, check:

1. **Cloud Run Logs:**
   ```bash
   gcloud run services logs read copernicus-podcast-api \
     --platform managed \
     --region us-central1 \
     --limit 50
   ```

2. **Look for:**
   - "Using Vertex AI Gemini 3.0" messages
   - Structured JSON log entries
   - Successful initialization

3. **Test:**
   - Create a new podcast
   - Verify it uses Gemini 3.0
   - Check logs are in structured format

---

## Rollback (if needed)

If issues occur:

```bash
# Option 1: Revert commit
git revert HEAD
git push

# Option 2: Rollback Cloud Run revision
# Use Cloud Console to select previous revision and route 100% traffic to it
```

---

## Post-Deployment Checklist

- [ ] Deployment successful
- [ ] Cloud Run logs show structured logging
- [ ] New podcast creation works
- [ ] Gemini 3.0 is being used (check logs)
- [ ] No errors in Cloud Run logs
- [ ] Monitor for 24 hours

---

## Questions?

Refer to `DEPLOYMENT_SUMMARY.md` for detailed information about all changes.

