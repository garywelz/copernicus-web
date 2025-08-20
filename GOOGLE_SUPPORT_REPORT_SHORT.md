# Google Cloud Run Connectivity Issue - Support Request

## Issue Summary
**Service**: Google Cloud Run  
**Project**: regal-scholar-453620-r7  
**Service**: copernicus-podcast-api  
**Region**: us-central1  
**URL**: https://copernicus-podcast-api-204731194849.us-central1.run.app

## Problem
Cloud Run service works perfectly when accessed directly, but requests from Vercel frontend are not reaching the backend. Frontend shows "success" but no POST requests appear in Cloud Run logs.

## Evidence

### Backend Works (Direct Access)
```bash
# Health check - SUCCESS
curl "https://copernicus-podcast-api-204731194849.us-central1.run.app/health"
# Returns: {"status": "healthy", "timestamp": "2025-08-20T03:04:59.825400"}

# Direct API call - SUCCESS  
curl -X POST "https://copernicus-podcast-api-204731194849.us-central1.run.app/generate-legacy-podcast" \
  -H "Content-Type: application/json" \
  -d '{"subject": "Test", "duration": "5 minutes", "speakers": "2", "difficulty": "intermediate"}'
# Returns: {"job_id": "65cfd09c-c176-45b0-9410-4c8c680cced3", "status": "pending"}
```

### Frontend-to-Backend Failing
- Frontend shows "Podcast generated successfully!"
- No POST requests in Cloud Run logs
- Only GET requests for job status appear
- Job status checks return "Job not found in Firestore"

## Configuration
- **Cloud Run**: Python FastAPI, unauthenticated, min-instances=1, max-instances=5
- **Frontend**: Next.js on Vercel (www.copernicusai.fyi)
- **CORS**: Allow all origins, methods, headers
- **Port**: 8080 (Cloud Run default)
- **Timeout**: 60 seconds (reduced for testing)

## Troubleshooting Completed
✅ Backend responds to direct requests  
✅ Health endpoint accessible  
✅ CORS properly configured  
✅ Service URL and endpoints correct  
✅ Scaling configuration updated  
✅ Added comprehensive logging  
❌ Frontend requests still not reaching backend  

## Suspected Root Cause
Network connectivity issue between Vercel infrastructure and Google Cloud Run in us-central1.

## Request for Support
Please investigate:
1. Network path from Vercel to Cloud Run service
2. Request tracing to see where requests fail
3. DNS resolution issues
4. Load balancer logs for rejected requests
5. Network latency between Vercel and Cloud Run

## Technical Environment
- **Runtime**: Python 3.11, FastAPI
- **Memory**: 2GB, CPU: 1 vCPU
- **Concurrency**: 80, Timeout: 300 seconds
- **Frontend**: Next.js 14 on Vercel Edge Network

## Impact
Critical production issue - complete failure of frontend-to-backend communication. Backend fully functional when accessed directly.

**Priority**: High (Production Service Affected)  
**Duration**: Several days  
**Status**: Backend works, frontend integration broken
