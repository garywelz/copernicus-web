# Knowledge Engine - Full Google Cloud Deployment Guide

**Date:** December 30, 2025  
**Purpose:** Deploy the entire Knowledge Engine to Google Cloud (no local servers required)

---

## Overview

This guide shows how to deploy both the **backend API** and **frontend dashboard** entirely to Google Cloud Run, eliminating the need for local servers.

### Architecture

```
┌─────────────────────────────────────────┐
│         Google Cloud Run                 │
│                                         │
│  ┌─────────────────┐  ┌──────────────┐ │
│  │  Frontend       │  │  Backend API │ │
│  │  (Next.js)      │──│  (FastAPI)   │ │
│  │  Port: 3000     │  │  Port: 8080   │ │
│  └─────────────────┘  └──────────────┘ │
│                                         │
│  ┌─────────────────────────────────────┐ │
│  │  Firestore (Database)               │ │
│  │  Vertex AI (Embeddings)             │ │
│  │  Cloud Storage (Files)              │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Prerequisites

1. **Google Cloud Project:** `regal-scholar-453620-r7`
2. **gcloud CLI:** Installed and authenticated
3. **Docker:** Not required (Cloud Build handles this)
4. **Billing:** Enabled on GCP project

---

## Part 1: Deploy Backend API

The backend is already configured for Cloud Run deployment.

### Option A: Quick Deploy (Recommended)

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
./deploy.sh
```

### Option B: Manual Deploy

```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
gcloud builds submit --config cloudbuild.yaml .
```

### Verify Backend

```bash
# Get the service URL
BACKEND_URL=$(gcloud run services describe copernicus-podcast-api \
  --region=us-central1 \
  --format="value(status.url)")

# Test health endpoint
curl $BACKEND_URL/health

# Test knowledge map endpoint
curl "$BACKEND_URL/api/knowledge-map/graph?max_papers=10"
```

**Expected Backend URL:** `https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`

---

## Part 2: Deploy Frontend

### Step 1: Update Configuration

The frontend components already use `NEXT_PUBLIC_API_URL` environment variable. This will be set during Cloud Run deployment.

### Step 2: Deploy to Cloud Run

```bash
cd /home/gdubs/copernicus-web-public
chmod +x deploy-frontend.sh
./deploy-frontend.sh
```

### Step 3: Verify Frontend

```bash
# Get the service URL
FRONTEND_URL=$(gcloud run services describe copernicus-frontend \
  --region=us-central1 \
  --format="value(status.url)")

# Test frontend
curl $FRONTEND_URL

# Access Knowledge Engine
echo "Knowledge Engine: $FRONTEND_URL/knowledge-engine"
```

---

## Part 3: Update Environment Variables

If you need to change the backend URL after deployment:

```bash
gcloud run services update copernicus-frontend \
  --region=us-central1 \
  --update-env-vars NEXT_PUBLIC_API_URL=https://your-backend-url.run.app
```

---

## Part 4: Custom Domain (Optional)

### Map Custom Domain to Frontend

```bash
gcloud run domain-mappings create \
  --service=copernicus-frontend \
  --domain=knowledge-engine.yourdomain.com \
  --region=us-central1
```

### Map Custom Domain to Backend (if needed)

```bash
gcloud run domain-mappings create \
  --service=copernicus-podcast-api \
  --domain=api.yourdomain.com \
  --region=us-central1
```

---

## Part 5: Monitoring & Logs

### View Frontend Logs

```bash
gcloud run services logs read copernicus-frontend \
  --region=us-central1 \
  --limit=50
```

### View Backend Logs

```bash
gcloud run services logs read copernicus-podcast-api \
  --region=us-central1 \
  --limit=50
```

### View in Cloud Console

- **Frontend:** https://console.cloud.google.com/run/detail/us-central1/copernicus-frontend
- **Backend:** https://console.cloud.google.com/run/detail/us-central1/copernicus-podcast-api

---

## Part 6: Cost Optimization

### Recommended Settings

**Frontend:**
- Memory: 1Gi (sufficient for Next.js)
- CPU: 1 (can scale to 2 if needed)
- Min instances: 0 (scale to zero when not in use)
- Max instances: 10

**Backend:**
- Memory: 2Gi (for graph building)
- CPU: 2 (with CPU boost)
- Min instances: 0 (scale to zero)
- Max instances: 5

### Estimated Costs

- **Frontend:** ~$0.10-0.50/month (light usage)
- **Backend:** ~$5-20/month (depending on graph building frequency)
- **Total:** ~$5-25/month for typical usage

---

## Troubleshooting

### Issue: Frontend can't connect to backend

**Solution:** Check `NEXT_PUBLIC_API_URL` environment variable:

```bash
gcloud run services describe copernicus-frontend \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

### Issue: CORS errors

**Solution:** Backend CORS is already configured. If issues persist, check backend logs:

```bash
gcloud run services logs read copernicus-podcast-api \
  --region=us-central1 \
  --filter="cors"
```

### Issue: Graph takes too long to load

**Solution:** This is expected on first load (2+ hours for full dataset). Use caching:

```bash
# Force rebuild (if needed)
curl "$BACKEND_URL/api/knowledge-map/graph?max_papers=10&force_rebuild=false"
```

### Issue: Build fails

**Solution:** Check Cloud Build logs:

```bash
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

---

## Quick Reference

### Deploy Both Services

```bash
# Deploy backend
cd cloud-run-backend && ./deploy.sh

# Deploy frontend
cd .. && ./deploy-frontend.sh
```

### Get Service URLs

```bash
# Backend
gcloud run services describe copernicus-podcast-api \
  --region=us-central1 \
  --format="value(status.url)"

# Frontend
gcloud run services describe copernicus-frontend \
  --region=us-central1 \
  --format="value(status.url)"
```

### Update Environment Variables

```bash
# Frontend
gcloud run services update copernicus-frontend \
  --region=us-central1 \
  --update-env-vars NEXT_PUBLIC_API_URL=<BACKEND_URL>
```

---

## Next Steps

1. ✅ Deploy backend API
2. ✅ Deploy frontend dashboard
3. ✅ Test Knowledge Engine at `$FRONTEND_URL/knowledge-engine`
4. ✅ Set up custom domain (optional)
5. ✅ Configure monitoring and alerts
6. ✅ Set up CI/CD for automatic deployments

---

## Support

For issues or questions:
- Check Cloud Run logs (see Part 5)
- Review deployment scripts: `deploy.sh`, `deploy-frontend.sh`
- Check Cloud Build history in GCP Console

