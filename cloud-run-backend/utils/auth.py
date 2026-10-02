"""Authentication utilities for Copernicus Podcast API"""

import os
import secrets
from typing import Optional
from fastapi import Header, HTTPException
from .logging import structured_logger
from config.constants import GCP_PROJECT_ID

# NOTE: config.database and utils.subscriber_helpers/generation_quota are
# imported lazily, inside each function, rather than at module level.
# utils/__init__.py imports this module (.auth) eagerly; config.database
# imports utils.logging, which re-enters the still-initializing `utils`
# package and fails with a circular-import ImportError if pulled in here
# at the top. Matches the existing lazy-import style already used below
# for google.cloud.secretmanager.


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


def _admin_key_matches(provided: Optional[str]) -> bool:
    expected = get_admin_api_key()
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided.strip(), expected.strip())


async def verify_admin_api_key(
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
):
    """Verify admin API key from the X-Admin-API-Key header only.

    Security lockdown Step 2 (2026-10-01): the ?admin_key= query-parameter
    fallback was removed. A scan of this codebase and every suite repo found
    zero live callers using it -- every caller already sends the header.
    Query parameters land in access logs, proxy logs, and browser history;
    headers don't.
    """
    expected_key = get_admin_api_key()

    if not expected_key:
        structured_logger.warning("ADMIN_API_KEY not configured - admin endpoints will be inaccessible")
        raise HTTPException(status_code=503, detail="Admin authentication not configured")

    if not x_admin_api_key:
        raise HTTPException(
            status_code=401,
            detail="Admin API key required. Provide via X-Admin-API-Key header"
        )

    if not secrets.compare_digest(x_admin_api_key.strip(), expected_key.strip()):
        structured_logger.warning("Invalid admin API key attempt")
        raise HTTPException(status_code=403, detail="Invalid admin API key")

    return True


async def require_admin_or_subscriber_owner(
    subscriber_id: str,
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
) -> dict:
    """For routes keyed by {subscriber_id} in the path: admin key OR a
    session token that matches this exact subscriber_id."""
    from config.database import db
    from utils.subscriber_helpers import verify_session_token

    if _admin_key_matches(x_admin_api_key):
        return {"via": "admin"}
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    doc = db.collection('subscribers').document(subscriber_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    data = doc.to_dict() or {}
    if not verify_session_token(data, x_subscriber_token):
        raise HTTPException(status_code=401, detail="Admin key or a valid subscriber session token required")
    return {"via": "subscriber", "subscriber_id": subscriber_id}


def require_admin_or_podcast_owner(
    owner_subscriber_id: Optional[str],
    x_admin_api_key: Optional[str],
    x_subscriber_token: Optional[str],
) -> dict:
    """For routes keyed by a podcast/episode ID, where the owning
    subscriber_id has already been resolved from that record (DELETE and
    submit-to-rss -- their path/body param isn't a subscriber_id). Called
    directly from inside the route body, not via Depends, since the owner
    isn't known until the record is read."""
    from config.database import db
    from utils.subscriber_helpers import verify_session_token

    if _admin_key_matches(x_admin_api_key):
        return {"via": "admin"}
    if not owner_subscriber_id:
        raise HTTPException(status_code=400, detail="Record not associated with a subscriber")
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    doc = db.collection('subscribers').document(owner_subscriber_id).get()
    if not doc.exists or not verify_session_token(doc.to_dict() or {}, x_subscriber_token):
        raise HTTPException(status_code=401, detail="Admin key or the owning subscriber's session token required")
    return {"via": "subscriber", "subscriber_id": owner_subscriber_id}


def authorize_generation(
    subscriber_id: Optional[str],
    x_admin_api_key: Optional[str],
    x_subscriber_token: Optional[str],
) -> dict:
    """For the three /generate-podcast* routes: admin key (unmetered), or a
    subscriber with can_generate=true and quota remaining (metered, atomic
    increment). Raises 401 (no credential), 403 (not allowlisted), or 429
    (quota used up). Called directly from inside each route body, not via
    Depends, since subscriber_id comes from different places per route
    (query param vs. request body field)."""
    from config.database import db
    from utils.subscriber_helpers import verify_session_token
    from utils.generation_quota import (
        check_and_increment_quota,
        GenerationNotAllowed,
        QuotaExceeded,
    )

    if _admin_key_matches(x_admin_api_key):
        return {"via": "admin"}
    if not subscriber_id or not x_subscriber_token:
        raise HTTPException(
            status_code=401,
            detail="Admin key, or a subscriber_id with a valid X-Subscriber-Token, required"
        )
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    doc = db.collection('subscribers').document(subscriber_id).get()
    if not doc.exists:
        raise HTTPException(status_code=401, detail="Invalid subscriber")
    if not verify_session_token(doc.to_dict() or {}, x_subscriber_token):
        raise HTTPException(status_code=401, detail="Missing or invalid session token")
    try:
        quota, count = check_and_increment_quota(db, subscriber_id)
    except GenerationNotAllowed as e:
        raise HTTPException(status_code=403, detail=str(e))
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"via": "subscriber", "subscriber_id": subscriber_id, "quota": quota, "count": count}
