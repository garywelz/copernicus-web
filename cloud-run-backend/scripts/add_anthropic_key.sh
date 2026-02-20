#!/bin/bash
# Script to add Anthropic API key to Google Cloud Secret Manager

set -e

PROJECT_ID="regal-scholar-453620-r7"
SECRET_NAME="anthropic-api-key"

echo "🔑 Adding Anthropic API key to Secret Manager"
echo "Project: $PROJECT_ID"
echo "Secret: $SECRET_NAME"
echo ""

# Check if secret already exists
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "⚠️  Secret '$SECRET_NAME' already exists."
    read -p "Do you want to add a new version? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Prompt for API key
echo "Enter your Anthropic API key (starts with 'sk-ant-'):"
read -s API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ Error: API key cannot be empty"
    exit 1
fi

# Validate format
if [[ ! "$API_KEY" =~ ^sk-ant- ]]; then
    echo "⚠️  Warning: API key doesn't start with 'sk-ant-'. Are you sure this is correct?"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
fi

# Create or update secret
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "📝 Adding new version to existing secret..."
    echo -n "$API_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"
else
    echo "✨ Creating new secret..."
    echo -n "$API_KEY" | gcloud secrets create "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"
fi

echo ""
echo "✅ Success! Anthropic API key has been added to Secret Manager."
echo ""
echo "Next steps:"
echo "1. The key will be automatically loaded on next service restart"
echo "2. Or restart your Cloud Run service to load it immediately"
echo "3. The system will automatically use Claude for RAG once the key is available"
