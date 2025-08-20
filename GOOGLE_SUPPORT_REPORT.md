# Google Cloud Support Report: Cloud Run Connectivity Issue

## Issue Summary
**Service**: Google Cloud Run  
**Project**: regal-scholar-453620-r7  
**Service Name**: copernicus-podcast-api  
**Region**: us-central1  
**Service URL**: https://copernicus-podcast-api-204731194849.us-central1.run.app

## Problem Description
Our Google Cloud Run service is experiencing connectivity issues when receiving requests from a Vercel-hosted frontend application. While the Cloud Run service functions correctly when tested directly (via curl commands), requests from the Vercel frontend are not reaching the backend, resulting in silent failures.

## Technical Details

### Current Configuration
- **Cloud Run Service**: Python FastAPI application
- **Frontend**: Next.js application hosted on Vercel (www.copernicusai.fyi)
- **Authentication**: Unauthenticated (--allow-unauthenticated)
- **Scaling**: min-instances=1, max-instances=5
- **Port**: 8080 (Cloud Run default)
- **CORS**: Configured to allow all origins

### Evidence of the Issue

#### 1. Backend Functionality Confirmed
Direct requests to the Cloud Run service work perfectly:
```bash
# Health check - SUCCESS
curl -s "https://copernicus-podcast-api-204731194849.us-central1.run.app/health"
# Returns: {"status": "healthy", "timestamp": "2025-08-20T03:04:59.825400", ...}

# Direct API call - SUCCESS
curl -X POST "https://copernicus-podcast-api-204731194849.us-central1.run.app/generate-legacy-podcast" \
  -H "Content-Type: application/json" \
  -d '{"subject": "Test", "duration": "5 minutes", "speakers": "2", "difficulty": "intermediate"}'
# Returns: {"job_id": "65cfd09c-c176-45b0-9410-4c8c680cced3", "status": "pending"}
```

#### 2. Frontend-to-Backend Communication Failing
When the frontend submits requests:
- Frontend shows "Podcast generated successfully!" message
- No POST requests appear in Cloud Run logs
- Job status checks return "Job not found in Firestore"
- No error messages in frontend console

#### 3. Cloud Run Logs Analysis
Recent logs show:
```
2025-08-20 03:24:47 GET 500 https://copernicus-podcast-api-204731194849.us-central1.run.app/status/job_1755660251969_u1czsrv25
2025-08-20 03:24:48 ❌ Error fetching job job_1755660251969_u1czsrv25 from Firestore: 404: Job 'job_1755660251969_u1czsrv25' not found in Firestore.
```

**Note**: Only GET requests for job status appear; no POST requests to create jobs are logged.

### Troubleshooting Steps Taken

#### 1. Network Connectivity
- ✅ Backend responds to direct requests
- ✅ Health endpoint accessible
- ✅ CORS properly configured
- ❌ Frontend requests not reaching backend

#### 2. Configuration Verification
- ✅ Service URL correct
- ✅ Endpoint paths correct
- ✅ Authentication settings correct
- ✅ Scaling configuration updated

#### 3. Debugging Enhancements
- Added comprehensive logging to frontend
- Added connectivity test endpoints
- Reduced timeout to 1 minute for faster failure detection
- Added cache-busting headers

#### 4. Service Stability
- Set min-instances=1 to prevent cold starts
- Service shows healthy status
- No application-level errors in logs

## Suspected Root Causes

### 1. Network Routing Issue
The most likely cause is a network routing problem between Vercel's infrastructure and Google Cloud Run. This could be:
- DNS resolution issues
- Network path problems
- Firewall/security group restrictions
- Load balancer configuration issues

### 2. Request Timeout
Frontend requests may be timing out before reaching Cloud Run, possibly due to:
- Network latency between Vercel and Google Cloud
- Request size or complexity
- Intermediate proxy timeouts

### 3. Silent Failure Mode
Requests may be failing silently due to:
- CORS preflight failures
- Network-level packet drops
- Intermediate proxy rejections

## Request for Google Support

### Primary Request
Please investigate the network connectivity between Vercel's infrastructure and our Cloud Run service in us-central1. Specifically:

1. **Network Path Analysis**: Verify the network path from Vercel to our Cloud Run service
2. **Request Tracing**: Enable request tracing to see where requests are failing
3. **DNS Resolution**: Check if there are any DNS resolution issues
4. **Load Balancer Logs**: Review load balancer logs for rejected requests

### Secondary Requests
1. **Enable Detailed Logging**: Enable more detailed network-level logging for our Cloud Run service
2. **Request Monitoring**: Set up monitoring to track failed requests
3. **Performance Analysis**: Analyze if there are performance bottlenecks causing timeouts

### Diagnostic Information Needed
1. **Network Latency**: Current latency between Vercel and our Cloud Run service
2. **Request Success Rate**: Percentage of requests that reach our service
3. **Error Patterns**: Any patterns in failed requests
4. **Infrastructure Status**: Status of intermediate infrastructure (load balancers, proxies)

## Technical Environment

### Cloud Run Service Details
- **Runtime**: Python 3.11
- **Framework**: FastAPI
- **Memory**: 2GB
- **CPU**: 1 vCPU
- **Concurrency**: 80
- **Timeout**: 300 seconds

### Frontend Details
- **Platform**: Vercel
- **Framework**: Next.js 14
- **Region**: Global (Vercel Edge Network)
- **Request Timeout**: 60 seconds (reduced from 300 for testing)

### Network Configuration
- **CORS**: Allow all origins, methods, and headers
- **Authentication**: Public (unauthenticated)
- **SSL**: HTTPS only
- **Headers**: Standard HTTP headers + custom User-Agent

## Contact Information
- **Project ID**: regal-scholar-453620-r7
- **Service Name**: copernicus-podcast-api
- **Region**: us-central1
- **Issue Duration**: Ongoing for several days
- **Impact**: Complete failure of frontend-to-backend communication

## Additional Context
This is a critical production issue affecting our podcast generation service. The backend is fully functional when accessed directly, but the frontend integration is completely broken. We have verified all application-level configurations and suspect a network infrastructure issue.

---

**Report Generated**: August 20, 2025  
**Issue Status**: Open  
**Priority**: High (Production Service Affected)
