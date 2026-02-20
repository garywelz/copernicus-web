#!/bin/bash

# Copernicus Frontend - Cloud Run Deployment Script
# This script deploys the Next.js frontend to Google Cloud Run

set -e

echo "🚀 Deploying Copernicus Frontend to Cloud Run..."

# Configuration
PROJECT_ID="regal-scholar-453620-r7"
SERVICE_NAME="copernicus-frontend"
REGION="us-central1"
BACKEND_URL="https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"

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
gcloud builds submit --config cloudbuild-frontend.yaml .

# Get the deployed service URL
echo "🌐 Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🎉 Your Copernicus Frontend is now live at:"
echo "   $SERVICE_URL"
echo ""
echo "🔧 Configuration:"
echo "   Backend API: $BACKEND_URL"
echo "   Frontend URL: $SERVICE_URL"
echo ""
echo "📝 Next steps:"
echo "1. Test the frontend:"
echo "   curl $SERVICE_URL"
echo ""
echo "2. Access Knowledge Engine:"
echo "   $SERVICE_URL/knowledge-engine"
echo ""
echo "3. Update custom domain (if needed):"
echo "   gcloud run domain-mappings create --service=$SERVICE_NAME --domain=your-domain.com --region=$REGION"
echo ""

