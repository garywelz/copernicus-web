"""Private-episode access for the episode's owner (onboarding PR 1, design 7.1 to 7.3).

Three small helpers shared by the owner routes and the admin routes:
  * session_owner_id: who, if anyone, the caller proves to be, for ONE episode record. The owner is read from the record (`subscriber_id`), then that
    subscriber's stored session-token hash is checked. A token for a different subscriber proves nothing.
  * private_access_enabled: the "ships dark" gate (design 8). The owner routes answer 404 to everyone not on a Firestore allow-list, so PR 1 can be
    deployed and tested before any real owner can use it. The list lives in a Firestore document, not an environment variable.
  * write_audit: one record per make-public / unpublish / quota change. No addresses, no names: ids, a timestamp and the reason.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

CONFIG_COLLECTION = "system_config"
CONFIG_DOC = "private_episode_access"
AUDIT_COLLECTION = "episode_audit"


def session_owner_id(db, record: Any, session_token: Optional[str]) -> Optional[str]:
    """The owner's subscriber id when `session_token` is a valid session for the subscriber who owns `record`; otherwise None."""
    from utils.subscriber_helpers import verify_session_token
    if not session_token or not isinstance(record, dict):
        return None
    owner = record.get("subscriber_id")
    if not owner or db is None:
        return None
    snap = db.collection("subscribers").document(owner).get()
    if not snap.exists:
        return None
    return owner if verify_session_token(snap.to_dict() or {}, session_token) else None


def private_access_enabled(db, subscriber_id: Optional[str]) -> bool:
    """True only when system_config/private_episode_access lists this subscriber in `allowed_subscriber_ids`, or sets `enabled_for_all` to true.
    A missing document, a missing field or any read error means False (fail closed)."""
    if not subscriber_id or db is None:
        return False
    try:
        snap = db.collection(CONFIG_COLLECTION).document(CONFIG_DOC).get()
        if not snap.exists:
            return False
        cfg = snap.to_dict() or {}
        return cfg.get("enabled_for_all") is True or subscriber_id in (cfg.get("allowed_subscriber_ids") or [])
    except Exception:                                           # noqa: BLE001
        return False


def write_audit(db, action: str, episode_id: Optional[str] = None, actor: str = "", reason: Optional[str] = None, **details: Any) -> Dict[str, Any]:
    """Append one audit record. `actor` is "admin-key" (the admin key carries no personal identity) or "owner:<subscriber id>"."""
    record = {"action": action, "episode_id": episode_id, "actor": actor, "reason": reason, "at": datetime.now(timezone.utc).isoformat(), **details}
    db.collection(AUDIT_COLLECTION).document(uuid.uuid4().hex).set(record)
    return record
