# Minimal Deployment - Just Fix Podcast Generation

## Strategy: Deploy ONLY the Critical Fix

Instead of committing everything at once, let's do a **minimal, focused deployment** that:
- ✅ Fixes the Gemini 3.0 model issue (blocks podcast creation)
- ✅ Doesn't include archived files or documentation
- ✅ Keeps the change set small and reviewable

---

## Minimal Deployment Steps

### Step 1: Commit ONLY main.py (the fix)

```bash
cd /home/gdubs/copernicus-web-public

# Stage ONLY the main.py file with the Gemini 3.0 fix
git add cloud-run-backend/main.py

# Commit with focused message
git commit -m "fix: Update Gemini model to 3.0 to fix podcast generation

- Changes model priority to use Gemini 3.0 first
- Fixes 404 error with invalid model names
- Adds proper fallback chains"
```

### Step 2: Push

```bash
git push origin main
```

### Step 3: Deploy

If auto-deploy is configured, it will deploy automatically. Otherwise:
```bash
cd cloud-run-backend
gcloud run deploy copernicus-podcast-api --source . --platform managed --region us-central1
```

---

## What We're NOT Committing Yet

- ❌ Archive directory (old files)
- ❌ Documentation files (*.md)
- ❌ Print statement replacements (can do later)
- ❌ Other cleanup files

These can all wait for a separate, organized commit later.

---

## After This Minimal Deploy

Once podcast creation works again, we can:
1. Organize and commit the archived files separately
2. Commit documentation separately  
3. Continue with print statement replacements incrementally

---

**This way we fix the immediate problem with minimal risk and change.**



