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

# Build and deploy using Cloud Build
echo "🏗️  Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Get the deployed service URL
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🎉 Your Copernicus Podcast API is now live at:"
echo "   $SERVICE_URL"
echo ""
echo "🔧 Next steps:"
echo "1. Update your Vercel environment variable:"
echo "   CLOUD_RUN_URL=$SERVICE_URL"
echo ""
echo "2. Test the API health check:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "3. View available research sources:"
echo "   curl $SERVICE_URL/research-sources"
echo ""
echo "🎙️  Ready to generate your first research podcast!"
