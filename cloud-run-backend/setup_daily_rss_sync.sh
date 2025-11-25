#!/bin/bash
# Script to set up Cloud Scheduler job for daily RSS sync
# This will call the sync-rss-status API endpoint daily

PROJECT_ID="regal-scholar-453620-r7"
SERVICE_NAME="copernicus-podcast-api"
REGION="us-central1"
JOB_NAME="daily-rss-sync"
SCHEDULE="0 2 * * *"  # Daily at 2 AM UTC (adjust timezone as needed)
TIMEZONE="UTC"

# Get the Cloud Run service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.url)" \
  --project=$PROJECT_ID)

if [ -z "$SERVICE_URL" ]; then
  echo "❌ Error: Could not get service URL for $SERVICE_NAME"
  exit 1
fi

echo "🔧 Setting up Cloud Scheduler job for daily RSS sync..."
echo "   Service URL: $SERVICE_URL"
echo "   Schedule: $SCHEDULE ($TIMEZONE)"
echo ""

# Enable Cloud Scheduler API if not already enabled
echo "📋 Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Check if job already exists
if gcloud scheduler jobs describe $JOB_NAME \
  --location=$REGION \
  --project=$PROJECT_ID &>/dev/null; then
  echo "⚠️  Job $JOB_NAME already exists. Updating..."
  gcloud scheduler jobs update http $JOB_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --time-zone="$TIMEZONE" \
    --uri="$SERVICE_URL/api/admin/episodes/sync-rss-status" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --oidc-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" \
    --project=$PROJECT_ID
else
  echo "✅ Creating new Cloud Scheduler job..."
  gcloud scheduler jobs create http $JOB_NAME \
    --location=$REGION \
    --schedule="$SCHEDULE" \
    --time-zone="$TIMEZONE" \
    --uri="$SERVICE_URL/api/admin/episodes/sync-rss-status" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --oidc-service-account-email="$PROJECT_ID@appspot.gserviceaccount.com" \
    --description="Daily sync of RSS feed status with Firestore episodes" \
    --project=$PROJECT_ID
fi

echo ""
echo "✅ Cloud Scheduler job '$JOB_NAME' configured!"
echo ""
echo "🔍 To test the job manually:"
echo "   gcloud scheduler jobs run $JOB_NAME --location=$REGION --project=$PROJECT_ID"
echo ""
echo "📊 To view job details:"
echo "   gcloud scheduler jobs describe $JOB_NAME --location=$REGION --project=$PROJECT_ID"
echo ""
echo "📋 To list all scheduled jobs:"
echo "   gcloud scheduler jobs list --location=$REGION --project=$PROJECT_ID"

