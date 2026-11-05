"""Private-episode access for the episode's owner (onboarding PR 1, design 7.1 to 7.3).

Three small helpers shared by the owner routes and the admin routes:
  * session_owner_id: who, if anyone, the caller proves to be, for ONE episode record. The owner is read from the record (`subscriber_id`), then that
    subscriber's stored session-token hash is checked. A token for a different subscriber proves nothing.
  * private_access_enabled: the "ships dark" gate (design 8). The owner routes answer 404 to everyone not on the Firestore list, or an active member of an
    onboarding engine whose record has private_access_enabled true (PR 2, option (b)). Both live in Firestore, not in an environment variable.
  * write_audit: one record per make-public / unpublish / quota change. No addresses, no names: ids, a timestamp and the reason.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

CONFIG_COLLECTION = "system_config"
CONFIG_DOC = "private_episode_access"
AUDIT_COLLECTION = "episode_audit"
MEMBERS_COLLECTION = "onboarding_members"           # utils/onboarding.MEMBERS (kept as literals here: this module imports nothing from onboarding)
ENGINES_COLLECTION = "onboarding_engines"


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


def _valid_id(value: Any) -> bool:
    """A usable subscriber id: a non-empty, non-blank string. None, "" and anything else never identify a person."""
    return isinstance(value, str) and bool(value.strip())


def _listed(db, subscriber_id: str) -> bool:
    """The PR 1 manual list: system_config/private_episode_access names this subscriber, or sets enabled_for_all to true. Raises on a read error."""
    snap = db.collection(CONFIG_COLLECTION).document(CONFIG_DOC).get()
    if not snap.exists:
        return False
    cfg = snap.to_dict() or {}
    return cfg.get("enabled_for_all") is True or subscriber_id in (cfg.get("allowed_subscriber_ids") or [])


def _active_member_of_an_enabled_engine(db, subscriber_id: str) -> bool:
    """Onboarding PR 2, option (b): the subscriber has an ACTIVE membership in an onboarding engine whose record says `private_access_enabled: true`.
    The flag is per engine, absent or false by default, and must be exactly true; a membership that is not active (removed, pending, anything else) never
    passes; and a flag on engine X opens nothing for a member of only engine Y. Raises on a read error."""
    if not _valid_id(subscriber_id):
        return False                                           # before any lookup: a missing or empty id must never match a record that lacks one
    for m in db.collection(MEMBERS_COLLECTION).where("subscriber_id", "==", subscriber_id).stream():
        member = m.to_dict() or {}
        if member.get("subscriber_id") != subscriber_id or member.get("status") != "active" or not member.get("engine_id"):
            continue                                           # a record must carry THIS subscriber's id: one with the id missing never matches
        engine = db.collection(ENGINES_COLLECTION).document(member["engine_id"]).get()
        if engine.exists and (engine.to_dict() or {}).get("private_access_enabled") is True:
            return True
    return False


def private_access_enabled(db, subscriber_id: Optional[str]) -> bool:
    """The owner-features switch (private-episode access, PR 1), now with two ways in:
      1. the manual list in system_config/private_episode_access (unchanged), OR
      2. an active membership in an onboarding engine that has `private_access_enabled: true` (PR 2, option (b); the flag is set by a deliberate admin
         write to the engine record, and no route sets it).
    Everything else is False, and any read error is False (fail closed)."""
    if not _valid_id(subscriber_id) or db is None:
        return False
    try:
        return _listed(db, subscriber_id) or _active_member_of_an_enabled_engine(db, subscriber_id)
    except Exception:                                           # noqa: BLE001
        return False


def write_audit(db, action: str, episode_id: Optional[str] = None, actor: str = "", reason: Optional[str] = None, **details: Any) -> Dict[str, Any]:
    """Append one audit record. `actor` is "admin-key" (the admin key carries no personal identity) or "owner:<subscriber id>"."""
    record = {"action": action, "episode_id": episode_id, "actor": actor, "reason": reason, "at": datetime.now(timezone.utc).isoformat(), **details}
    db.collection(AUDIT_COLLECTION).document(uuid.uuid4().hex).set(record)
    return record
