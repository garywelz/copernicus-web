#!/bin/bash

# Copernicus Podcast API - Cloud Run Deployment Script
# This script deploys the comprehensive research podcast generation backend

set -e

echo "🚀 Deploying Copernicus Podcast API to Cloud Run..."

# Configuration
PROJECT_ID="regal-scholar-453620-r7"
SERVICE_NAME="copernicus-podcast-api"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Check if gcloud is authenticated
echo "📋 Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Please authenticate with Google Cloud first:"
    echo "   gcloud auth login"
    echo "   gcloud config set project $PROJECT_ID"
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build using Cloud Build. cloudbuild.yaml builds and pushes the image
# only -- it does not deploy. See cloud-run-backend/DEPLOY.md.
echo "🏗️  Building with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Get the currently live service URL (unaffected by this build -- nothing
# was deployed)
echo "🌐 Getting current service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Build submitted (build only; this script does not deploy)"
echo ""
echo "🔧 To deploy, follow cloud-run-backend/DEPLOY.md (gated: --no-traffic,"
echo "   revision diff, smoke test, approval before traffic moves)."
echo ""
echo "Currently live service (unchanged by this build):"
echo "1. Test the API health check:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "2. View available research sources:"
echo "   curl $SERVICE_URL/research-sources"
