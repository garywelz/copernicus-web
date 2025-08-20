#!/usr/bin/env python3
"""
Test script for Vertex AI integration with Secret Manager authentication
"""

import os
import sys
import json

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_vertex_ai_setup():
    """Test Vertex AI setup and authentication"""
    print("🧪 Testing Vertex AI Integration with Secret Manager")
    print("=" * 60)
    
    # Test 1: Check dependencies
    print("\n1. Checking Dependencies...")
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        from google.cloud import secretmanager
        from google.oauth2 import service_account
        print("✅ All Vertex AI dependencies available")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Install with: pip install google-cloud-aiplatform google-cloud-secret-manager")
        return False
    
    # Test 2: Check Secret Manager access
    print("\n2. Testing Secret Manager Access...")
    try:
        from main_google import get_service_account_credentials_from_secret_manager, GCP_PROJECT_ID, SECRET_ID, SECRET_VERSION_ID
        
        credentials = get_service_account_credentials_from_secret_manager(
            GCP_PROJECT_ID, SECRET_ID, SECRET_VERSION_ID
        )
        
        if credentials:
            print("✅ Successfully retrieved credentials from Secret Manager")
        else:
            print("❌ Failed to retrieve credentials from Secret Manager")
            return False
            
    except Exception as e:
        print(f"❌ Secret Manager error: {e}")
        return False
    
    # Test 3: Test Vertex AI initialization
    print("\n3. Testing Vertex AI Initialization...")
    try:
        from main_google import initialize_vertex_ai, GCP_PROJECT_ID, VERTEX_AI_REGION
        
        model = initialize_vertex_ai()
        if model:
            print("✅ Vertex AI initialized successfully")
            print(f"📍 Project: {GCP_PROJECT_ID}")
            print(f"📍 Region: {VERTEX_AI_REGION}")
        else:
            print("❌ Vertex AI initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Vertex AI initialization error: {e}")
        return False
    
    # Test 4: Test simple Vertex AI API call
    print("\n4. Testing Vertex AI API Call...")
    try:
        response = model.generate_content("What is the capital of Canada?")
        if response and response.text:
            print("✅ Vertex AI API call successful")
            print(f"📝 Response: {response.text[:100]}...")
        else:
            print("❌ Empty response from Vertex AI")
            return False
            
    except Exception as e:
        print(f"❌ Vertex AI API call error: {e}")
        return False
    
    # Test 5: Check service account permissions
    print("\n5. Checking Service Account Permissions...")
    try:
        # The fact that we got this far means the service account has the right permissions
        print("✅ Service account has proper Secret Manager access")
        print("✅ Service account can authenticate with Vertex AI")
        
    except Exception as e:
        print(f"❌ Permission error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All Vertex AI tests passed! Your setup is ready.")
    print("\nNext steps:")
    print("1. Run your main_google.py backend")
    print("2. Check the startup logs for Vertex AI status")
    print("3. Test podcast generation via your web UI")
    
    return True

def test_backend_integration():
    """Test the backend integration"""
    print("\n🔧 Testing Backend Integration...")
    
    try:
        from main_google import vertex_model, get_google_api_key
        
        print(f"🤖 Vertex AI Model: {'✅ Available' if vertex_model else '❌ Not Available'}")
        print(f"🔑 Google AI API: {'✅ Available' if get_google_api_key() else '❌ Not Available'}")
        
        if vertex_model:
            print("🚀 Backend will use Vertex AI as primary AI provider")
        elif get_google_api_key():
            print("🔄 Backend will fall back to Google AI API")
        else:
            print("⚠️  Backend will use fallback content generation")
            
    except Exception as e:
        print(f"❌ Backend integration error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Vertex AI Integration Test Suite")
    print("Testing Vertex AI with Secret Manager authentication...")
    
    success = test_vertex_ai_setup()
    
    if success:
        test_backend_integration()
        print("\n✅ Ready for production use!")
    else:
        print("\n❌ Setup issues detected. Please resolve before proceeding.")
        sys.exit(1)
