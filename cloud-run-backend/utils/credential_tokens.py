"""Single-use, expiring credential tokens that prove control of a mailbox.

A token is emailed to the address on an account and later presented to set a new password. Only sha256(token) is ever
stored (the raw value exists in the email and in the request that redeems it); a token works once; it expires; an
account has at most one outstanding token. The same mechanism serves any later credential change: add a purpose to
PURPOSE_TTL_MINUTES.

The state changes run inside one Firestore transaction (all reads, then all writes), so two simultaneous redemptions of
one token cannot both succeed.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.cloud import firestore

from utils.logging import structured_logger

CREDENTIAL_TOKENS = "credential_tokens"          # document id = sha256(token)
CREDENTIAL_TOKEN_INDEX = "credential_token_index"  # document id = subscriber id: its one outstanding token's hash

PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_TTL_MINUTES = {PURPOSE_PASSWORD_RESET: 30}

# Where the emailed link points. The token travels in the URL fragment, which browsers never send to a server.
PASSWORD_RESET_PAGE_URL = "https://www.copernicusai.fyi/subscriber-reset-password.html"

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
MAX_TOKEN_LENGTH = 200


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _run_in_transaction(db, fn, *args):
    """Run fn(transaction, *args) in a Firestore transaction (retried on contention). Tests replace this."""
    return firestore.transactional(fn)(db.transaction(), *args)


def _issue_in(transaction, db, subscriber_id: str, purpose: str, token_hash: str, now: datetime, expires: datetime):
    index_ref = db.collection(CREDENTIAL_TOKEN_INDEX).document(subscriber_id)
    previous = index_ref.get(transaction=transaction)
    previous_hash = previous.to_dict().get("token_hash") if previous.exists else None
    # All reads are done; writes follow.
    if previous_hash:
        transaction.delete(db.collection(CREDENTIAL_TOKENS).document(previous_hash))
    transaction.set(db.collection(CREDENTIAL_TOKENS).document(token_hash), {
        "subscriber_id": subscriber_id,
        "purpose": purpose,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "used_at": None,
    })
    transaction.set(index_ref, {"token_hash": token_hash})


def issue_token(db, subscriber_id: str, purpose: str = PURPOSE_PASSWORD_RESET, now: Optional[datetime] = None) -> str:
    """Create a token for the account and return the raw value (to be emailed, never stored or logged). Any earlier
    outstanding token for the account stops working."""
    now = now or _utcnow()
    raw = secrets.token_urlsafe(32)
    expires = now + timedelta(minutes=PURPOSE_TTL_MINUTES[purpose])
    _run_in_transaction(db, _issue_in, db, subscriber_id, purpose, hash_token(raw), now, expires)
    structured_logger.info("Credential token issued", subscriber_id=subscriber_id, purpose=purpose)
    return raw


def _redeem_password_in(transaction, db, token_hash: str, purpose: str, new_password_hash: str, now: datetime) -> Optional[str]:
    token_ref = db.collection(CREDENTIAL_TOKENS).document(token_hash)
    token_snap = token_ref.get(transaction=transaction)
    if not token_snap.exists:
        return None
    token = token_snap.to_dict()
    if token.get("used_at") or token.get("purpose") != purpose:
        return None
    try:
        if datetime.fromisoformat(token["expires_at"]) < now:
            return None
    except (KeyError, ValueError):
        return None
    subscriber_id = token.get("subscriber_id")
    subscriber_ref = db.collection("subscribers").document(subscriber_id)
    if not subscriber_ref.get(transaction=transaction).exists:
        return None
    index_ref = db.collection(CREDENTIAL_TOKEN_INDEX).document(subscriber_id)
    # All reads are done; writes follow.
    transaction.update(token_ref, {"used_at": now.isoformat()})
    transaction.delete(index_ref)
    transaction.update(subscriber_ref, {
        "password_hash": new_password_hash,
        "password_changed_at": now.isoformat(),
        # A password change ends every existing session.
        "session_token_hash": firestore.DELETE_FIELD,
        "session_token_expires": firestore.DELETE_FIELD,
    })
    return subscriber_id


def redeem_password_token(db, raw_token: str, new_password_hash: str, purpose: str = PURPOSE_PASSWORD_RESET,
                          now: Optional[datetime] = None) -> Optional[str]:
    """Spend the token and set the account's password in one transaction. Returns the subscriber id, or None when the
    token is unknown, already used, expired or for another purpose (the caller cannot and must not tell which)."""
    if not isinstance(raw_token, str) or not raw_token or len(raw_token) > MAX_TOKEN_LENGTH:
        return None
    now = now or _utcnow()
    subscriber_id = _run_in_transaction(db, _redeem_password_in, db, hash_token(raw_token), purpose, new_password_hash, now)
    if subscriber_id:
        structured_logger.info("Credential token redeemed", subscriber_id=subscriber_id, purpose=purpose)
    return subscriber_id
