# Deployment Commands

## Step 1: Review Changes

The following files have been modified:
- `cloud-run-backend/main.py` - 1139 lines changed (Gemini 3.0 config + print replacement)

Files deleted (will be archived):
- 27 one-off scripts
- 9 old main_*.py files

New files created:
- Documentation files (DEPLOYMENT_SUMMARY.md, etc.)
- Diagnostic scripts (check_latest_failure.py, diagnose_issues.py)
- Archive directory structure

## Step 2: Commit Changes

```bash
# Add all changes
git add .

# Commit with descriptive message
git commit -m "feat: Configure Gemini 3.0 priority and replace all print statements with structured logging

- Updated all model fallback chains to prioritize Gemini 3.0
- Fixed invalid model name references (gemini-1.5-flash)
- Replaced all ~170 print statements with structured logging
- Added comprehensive error handling and fallback chains
- Archived old main_*.py files and one-off scripts
- Added diagnostic tools and documentation

Breaking changes: None
This improves observability and ensures we're using the latest Gemini models."
```

## Step 3: Push to GitHub

```bash
git push origin main
```

## Step 4: Verify Deployment

After pushing, check:
1. GitHub Actions (if configured) - should trigger deployment
2. Cloud Run console - new revision should appear
3. Cloud Run logs - should show new structured log format
4. Test by creating a new podcast

## Step 5: Monitor After Deployment

Watch Cloud Logging for:
- "Using Vertex AI Gemini 3.0" messages
- Structured JSON log entries
- Any errors with model availability

---

## Alternative: Manual Cloud Run Deployment

If auto-deploy isn't configured, deploy manually:

```bash
# Build and deploy
gcloud run deploy copernicus-podcast-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --project regal-scholar-453620-r7
```

Or use Cloud Console:
1. Go to Cloud Run
2. Select `copernicus-podcast-api` service
3. Click "Deploy new revision"
4. Configure as needed
5. Deploy

