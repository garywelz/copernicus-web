"""Authentication utilities for Copernicus Podcast API"""

import os
from typing import Optional
from fastapi import Header, Query, HTTPException
from .logging import structured_logger
from config.constants import GCP_PROJECT_ID


def get_admin_api_key() -> Optional[str]:
    """Get admin API key from environment or Secret Manager"""
    admin_key = os.environ.get('ADMIN_API_KEY')
    if admin_key:
        return admin_key.strip()
    
    # Try to load from Secret Manager if not in environment
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/admin-api-key/versions/latest"
        response = client.access_secret_version(request={"name": name})
        key = response.payload.data.decode("UTF-8").strip()
        if key:
            os.environ['ADMIN_API_KEY'] = key
            return key
    except Exception as e:
        structured_logger.debug("Could not load admin API key from Secret Manager", error=str(e))
    
    return None


async def verify_admin_api_key(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    admin_key: Optional[str] = Query(None, alias="admin_key")
):
    """Verify admin API key from header or query parameter - FastAPI dependency"""
    expected_key = get_admin_api_key()
    
    if not expected_key:
        structured_logger.warning("ADMIN_API_KEY not configured - admin endpoints will be inaccessible")
        raise HTTPException(status_code=503, detail="Admin authentication not configured")
    
    # Check header first, then query parameter
    provided_key = x_admin_api_key or admin_key
    
    if not provided_key:
        raise HTTPException(
            status_code=401,
            detail="Admin API key required. Provide via X-Admin-API-Key header or admin_key query parameter"
        )
    
    if provided_key.strip() != expected_key.strip():
        structured_logger.warning("Invalid admin API key attempt")
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    
    return True


