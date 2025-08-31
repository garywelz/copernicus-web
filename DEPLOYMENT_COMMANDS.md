# Deployment Commands for Cursor Terminal

Copy and paste these commands directly into your Cursor terminal:

## Step 1: Navigate to Backend Directory
```bash
cd cloud-run-backend
```

## Step 2: Deploy Cloud Run Backend
```bash
./deploy.sh
```

## Step 3: Navigate to Cloud Function Directory  
```bash
cd ../cloud-function
```

## Step 4: Deploy Cloud Function
```bash
gcloud functions deploy generate-podcast \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region us-central1 \
  --source .
```

## Step 5: Test Deployment
```bash
# Test backend health
curl https://copernicus-podcast-api-204731194849.us-central1.run.app/health

# Test cloud function (replace YOUR_FUNCTION_URL with actual URL from deployment output)
curl -X POST https://us-central1-regal-scholar-453620-r7.cloudfunctions.net/generate-podcast \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Test Topic",
    "category": "Computer Science", 
    "duration": "10",
    "speakers": "interview",
    "difficulty": "Intermediate"
  }'
```

## Step 6: Monitor Logs (Optional)
```bash
# View Cloud Run logs
gcloud logs read --project=regal-scholar-453620-r7 --service=copernicus-podcast-api --limit=50

# View Cloud Function logs  
gcloud logs read --project=regal-scholar-453620-r7 --resource=cloud_function --filter="resource.labels.function_name=generate-podcast" --limit=50
```

## Expected Output
- Backend deployment should show service URL
- Function deployment should show trigger URL
- Health check should return JSON with status "healthy"
- Test request should return job_id and success message

## If Deployment Fails
1. Ensure you're authenticated: `gcloud auth login`
2. Set correct project: `gcloud config set project regal-scholar-453620-r7`
3. Check permissions: `gcloud projects get-iam-policy regal-scholar-453620-r7`