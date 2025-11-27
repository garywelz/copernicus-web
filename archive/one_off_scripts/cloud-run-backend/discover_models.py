#!/usr/bin/env python3
"""
Discover available Vertex AI models for the project
"""
import os
import sys
from google.cloud import secretmanager
import vertexai
from vertexai.generative_models import GenerativeModel
import json

# Configuration
GCP_PROJECT_ID = "regal-scholar-453620-r7"
VERTEX_AI_REGION = "us-central1"
SECRET_ID = "vertex-ai-service-account-key"

def get_service_account_credentials_from_secret_manager():
    """Retrieve service account credentials from Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        credentials_json = response.payload.data.decode("UTF-8")
        
        # Parse and create credentials
        import json
        from google.oauth2 import service_account
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_info)
        return credentials
    except Exception as e:
        print(f"Error retrieving credentials: {e}")
        return None

def test_model_access(model_name):
    """Test if a specific model is accessible"""
    try:
        model = GenerativeModel(model_name)
        response = model.generate_content("Hello")
        return True, response.text[:50] if response.text else "Empty response"
    except Exception as e:
        return False, str(e)

def main():
    print("🔍 Discovering Available Vertex AI Models")
    print("=" * 50)
    
    # Initialize Vertex AI
    credentials = get_service_account_credentials_from_secret_manager()
    if not credentials:
        print("❌ Could not retrieve credentials")
        return
    
    vertexai.init(project=GCP_PROJECT_ID, location=VERTEX_AI_REGION, credentials=credentials)
    print(f"✅ Vertex AI initialized for {GCP_PROJECT_ID} in {VERTEX_AI_REGION}")
    
    # Test various model names
    models_to_test = [
        "gemini-pro",
        "gemini-1.0-pro", 
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "text-bison",
        "text-bison@001",
        "chat-bison",
        "chat-bison@001",
    ]
    
    print("\n🧪 Testing Model Access:")
    print("-" * 30)
    
    working_models = []
    for model_name in models_to_test:
        print(f"Testing {model_name}...", end=" ")
        success, result = test_model_access(model_name)
        if success:
            print(f"✅ WORKS - {result}")
            working_models.append(model_name)
        else:
            print(f"❌ FAILED - {result[:100]}")
    
    print("\n" + "=" * 50)
    if working_models:
        print(f"🎉 Working models found: {working_models}")
    else:
        print("❌ No working models found")
        print("\nThis confirms the project needs model access approval from Google.")

if __name__ == "__main__":
    main()
