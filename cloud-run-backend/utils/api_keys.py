"""API key management utilities"""

import os
from google.cloud import secretmanager
from utils.logging import structured_logger
from config.constants import GCP_PROJECT_ID


def get_google_api_key():
    """Get Google AI API key from Secret Manager or environment"""
    # Check environment first (already loaded on startup)
    key = (os.environ.get("GOOGLE_AI_API_KEY") or 
           os.environ.get("GEMINI_API_KEY") or
           os.environ.get("GOOGLE_API_KEY"))
    
    if key:
        return key
    
    # Fallback: try Secret Manager directly
    try:
        structured_logger.debug("Retrieving Google AI API key from Secret Manager")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_AI_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        return key
    except Exception as e:
        structured_logger.warning("Could not retrieve Google AI API key", error=str(e))
        return None


def check_vertex_ai_available():
    """Check if Vertex AI dependencies are available"""
    try:
        from google import genai as google_genai_client
        import vertexai
        return True
    except ImportError:
        return False

