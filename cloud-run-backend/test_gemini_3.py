#!/usr/bin/env python3
"""
Test script to check if Gemini 3.0 models are available in Vertex AI.
"""
import os
import sys
from google.cloud import secretmanager
from google import genai as google_genai
import vertexai

# Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7")
VERTEX_AI_REGION = os.getenv("VERTEX_AI_REGION", "us-central1")

def test_model_availability(model_name):
    """Test if a specific Gemini model is available"""
    try:
        print(f"Testing {model_name}...", end=" ")
        client = google_genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=VERTEX_AI_REGION)
        
        # Try to generate content with the model
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Hello' if you can read this."
        )
        
        if response and response.text:
            print(f"✅ AVAILABLE - Response: {response.text[:50]}")
            return True
        else:
            print("❌ NOT AVAILABLE - Empty response")
            return False
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            print(f"❌ NOT AVAILABLE - {error_msg[:80]}")
        else:
            print(f"⚠️  ERROR - {error_msg[:80]}")
        return False

def main():
    print("🔍 Testing Gemini 3.0 Model Availability in Vertex AI")
    print("=" * 60)
    
    # Models to test - Gemini 3.0 variants
    models_to_test = [
        'models/gemini-3.0-flash',
        'models/gemini-3.0-flash-exp',
        'models/gemini-3.0-pro',
        'models/gemini-3.0-pro-exp',
        'gemini-3.0-flash',
        'gemini-3.0-pro',
        # Also check current models for comparison
        'models/gemini-2.5-flash',
        'models/gemini-2.0-flash-exp',
    ]
    
    print("\nTesting model availability:\n")
    available_models = []
    for model_name in models_to_test:
        if test_model_availability(model_name):
            available_models.append(model_name)
        print()
    
    print("=" * 60)
    if available_models:
        print(f"\n✅ Available models: {', '.join(available_models)}")
        print(f"\n🎯 Recommended model for podcast generation: {available_models[0]}")
    else:
        print("\n❌ No Gemini 3.0 models found. Current models (2.5/2.0) may still work.")
    
    return available_models

if __name__ == "__main__":
    available = main()
    sys.exit(0 if available else 1)

