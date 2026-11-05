"""Owner routes for private episodes (onboarding PR 1, design 7.1 and 7.2).

  GET  /api/subscribers/episodes/{episode_id}/media-links   short-lived signed links to the owner's own audio and artwork
  POST /api/subscribers/episodes/{episode_id}/make-public   the owner publishes their own episode to the website (NOT the feed; not reversible by the owner)

Both answer 404, never 401 or 403, to anyone who is not the episode's owner or an admin, whether or not they are signed in and whether or not the episode
exists, so the answer reveals nothing. Both also answer 404 to an owner who is not on the Firestore allow-list (the routes ship dark, design 8).
There is deliberately NO route here that makes a public episode private: only the admin `unpublish` route does that.
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException, Query
from fastapi.responses import JSONResponse

import media_store
from config.constants import EPISODE_COLLECTION_NAME
from config.database import db
from utils.episode_access import admin_key_ok, is_public_episode
from utils.logging import structured_logger
from utils.owner_access import private_access_enabled, session_owner_id, write_audit

router = APIRouter()

NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Episode not found")


def _viewer(record: Any, admin_key: Optional[str], token: Optional[str]) -> Optional[Dict[str, str]]:
    """Who the caller proves to be for this episode: the admin, the owner (allow-listed), or nobody. Nobody means the caller sees a 404."""
    if admin_key_ok(admin_key):
        return {"via": "admin"}
    owner = session_owner_id(db, record, token)
    if owner and private_access_enabled(db, owner):
        return {"via": "owner", "subscriber_id": owner}
    return None


def _load(episode_id: str):
    if not db:
        raise HTTPException(status_code=503, detail="Firestore service is unavailable")
    snap = db.collection(EPISODE_COLLECTION_NAME).document(episode_id).get()
    return snap.to_dict() if snap.exists else None


@router.get("/api/subscribers/episodes/{episode_id}/media-links")
async def owner_media_links(
    episode_id: str,
    minutes: int = Query(media_store.OWNER_LINK_DEFAULT_MINUTES, ge=1, le=media_store.OWNER_LINK_MAX_MINUTES),
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Signed links (default 15 minutes, at most 60) to the audio and artwork of the caller's own episode. Minted fresh on every call; never stored."""
    record = _load(episode_id)
    if record is None or _viewer(record, x_admin_api_key, x_subscriber_token) is None:
        raise _not_found()
    try:
        out = await asyncio.to_thread(media_store.owner_media_links, episode_id, minutes)
    except Exception as e:
        structured_logger.error("Could not build owner media links", episode_id=episode_id, error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Could not build media links")
    return JSONResponse(out, headers=NO_STORE)


@router.post("/api/subscribers/episodes/{episode_id}/make-public")
async def make_episode_public(
    episode_id: str,
    body: Dict[str, Any] = Body(default={}),
    x_admin_api_key: Optional[str] = Header(None, alias="X-Admin-API-Key"),
    x_subscriber_token: Optional[str] = Header(None, alias="X-Subscriber-Token"),
):
    """Publish the caller's own episode to the website: copy its files to the public bucket (verified, fail closed), then set visible_on_web.

    The same sequence and the same rollback as the admin `publish-site` route. It does NOT submit the episode to the podcast feed (that stays a separate,
    editor-controlled step) and the owner cannot undo it: only an admin can unpublish. The body must say `confirm_irreversible: true`."""
    record = _load(episode_id)
    viewer = _viewer(record, x_admin_api_key, x_subscriber_token) if record is not None else None
    if viewer is None:
        raise _not_found()
    if body.get("confirm_irreversible") is not True:
        raise HTTPException(status_code=400, detail="Publishing is permanent for you: only the site administrator can take an episode back. Send confirm_irreversible: true to continue.")
    if is_public_episode(record):
        return {"episode_id": episode_id, "visible_on_web": bool(record.get("visible_on_web")), "already_public": True, "in_feed": bool(record.get("submitted_to_rss"))}
    ref = db.collection(EPISODE_COLLECTION_NAME).document(episode_id)
    try:
        promotion = await asyncio.to_thread(media_store.promote, episode_id)
    except media_store.MediaError as e:
        structured_logger.error("Media promotion failed; episode not made public", episode_id=episode_id, error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail="Could not publish the episode's files; nothing was changed")
    actor = "admin-key" if viewer["via"] == "admin" else f"owner:{viewer['subscriber_id']}"
    try:
        ref.set({"visible_on_web": True, "visibility": "public", "media_state": "public", "made_public_by": actor,
                 "updated_at": datetime.utcnow().isoformat()}, merge=True)
    except Exception:
        await asyncio.to_thread(media_store.demote, promotion.get("objects", []))
        raise
    try:
        write_audit(db, "make_public", episode_id, actor, promoted_files=promotion.get("promoted", 0))
    except Exception as e:                                       # the episode is already public; do not turn that into an error
        structured_logger.error("Audit record for make-public was not written", episode_id=episode_id, error_type=type(e).__name__)
    return {"episode_id": episode_id, "visible_on_web": True, "already_public": False, "promoted_files": promotion.get("promoted", 0), "in_feed": False}
