# Knowledge Engine - Deployment Success! 🎉

**Date:** December 30, 2025  
**Status:** ✅ Successfully Deployed to Google Cloud Run

---

## Deployment Summary

### ✅ Backend API
- **Service:** `copernicus-podcast-api`
- **URL:** https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app
- **Status:** ✅ Running
- **Region:** us-central1

### ✅ Frontend Dashboard
- **Service:** `copernicus-frontend`
- **URL:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app
- **Status:** ✅ Running
- **Region:** us-central1
- **Public Access:** ✅ Enabled

---

## Access Your Knowledge Engine

### Main Dashboard
**URL:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine

### Features Available
1. **Knowledge Map** - Interactive graph visualization
2. **Search** - Semantic search across papers, podcasts, processes
3. **Ask Questions** - RAG-powered question answering
4. **Browse Content** - Explore papers, podcasts, and processes
5. **Statistics** - View system metrics

---

## Configuration

### Environment Variables
- **Frontend:** `NEXT_PUBLIC_API_URL=https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app`
- **Backend:** Configured with Firestore, Vertex AI, and Cloud Storage

### Service Settings
- **Frontend:**
  - Memory: 1Gi
  - CPU: 1
  - Port: 3000
  - Max Instances: 10
  - Timeout: 300s

- **Backend:**
  - Memory: 2Gi
  - CPU: 2 (with CPU boost)
  - Port: 8080
  - Max Instances: 5
  - Timeout: 900s

---

## Next Steps

### 1. Test the Knowledge Engine
Visit: https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine

### 2. Set Up Custom Domain (Optional)
```bash
gcloud run domain-mappings create \
  --service=copernicus-frontend \
  --domain=knowledge-engine.yourdomain.com \
  --region=us-central1
```

### 3. Monitor Usage
- **Cloud Console:** https://console.cloud.google.com/run
- **Logs:** `gcloud run services logs read copernicus-frontend --region=us-central1`

### 4. Update Deployment
To update the frontend:
```bash
cd /home/gdubs/copernicus-web-public
./deploy-frontend.sh
```

To update the backend:
```bash
cd cloud-run-backend
./deploy.sh
```

---

## Troubleshooting

### If Knowledge Engine doesn't load:
1. Check backend is running: `curl https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app/health`
2. Check frontend logs: `gcloud run services logs read copernicus-frontend --region=us-central1 --limit=50`
3. Verify environment variable: `gcloud run services describe copernicus-frontend --region=us-central1 --format="get(spec.template.spec.containers[0].env)"`

### If graph takes too long:
- First load builds the graph (2+ hours for full dataset)
- Subsequent loads use cache (< 1 second)
- Use `max_papers=10` for faster initial testing

---

## Success! 🚀

Your Knowledge Engine is now fully deployed and accessible 24/7 on Google Cloud Run. No local servers required!

