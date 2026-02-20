"""
Helper functions to retrieve API keys from Google Cloud Secret Manager.

These functions are used by the provider implementations to automatically
retrieve API keys from Secret Manager if they're not set as environment variables.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import Secret Manager (may not be available in all environments)
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    secretmanager = None
    SECRET_MANAGER_AVAILABLE = False


def get_secret_from_manager(secret_name: str, project_id: str = "regal-scholar-453620-r7") -> Optional[str]:
    """
    Get a secret from Google Cloud Secret Manager.
    
    Args:
        secret_name: Name of the secret in Secret Manager
        project_id: GCP project ID
    
    Returns:
        Secret value as string, or None if not found
    """
    if not SECRET_MANAGER_AVAILABLE:
        return None
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.debug(f"Could not retrieve secret {secret_name} from Secret Manager: {e}")
        return None


def get_openai_api_key() -> Optional[str]:
    """
    Get OpenAI API key from environment or Secret Manager.
    
    Returns:
        API key string, or None if not found
    """
    # Check environment first
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key.strip()
    
    # Try Secret Manager
    key = get_secret_from_manager("openai-api-key")
    if key:
        # Cache in environment for future use
        os.environ["OPENAI_API_KEY"] = key
        return key
    
    return None


def get_anthropic_api_key() -> Optional[str]:
    """
    Get Anthropic API key from environment or Secret Manager.
    
    Returns:
        API key string, or None if not found
    """
    # Check environment first
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key.strip()
    
    # Try Secret Manager
    key = get_secret_from_manager("anthropic-api-key")
    if key:
        # Cache in environment for future use
        os.environ["ANTHROPIC_API_KEY"] = key
        return key
    
    return None


def get_voyage_api_key() -> Optional[str]:
    """
    Get Voyage API key from environment or Secret Manager.
    
    Returns:
        API key string, or None if not found
    """
    # Check environment first
    key = os.getenv("VOYAGE_API_KEY")
    if key:
        return key.strip()
    
    # Try Secret Manager
    key = get_secret_from_manager("voyage-api-key")
    if key:
        # Cache in environment for future use
        os.environ["VOYAGE_API_KEY"] = key
        return key
    
    # Voyage can also use Anthropic API key
    return get_anthropic_api_key()
