"""Subscriber helper functions for authentication and database operations"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from config.database import db
from config.constants import ADMIN_SUBSCRIBER_EMAIL
from utils.logging import structured_logger

SESSION_TOKEN_TTL_HOURS = 24 * 14  # 14 days

# scrypt parameters. n=2**14 (16384), r=8, p=1 is the libsodium-recommended
# "interactive" cost -- fast enough for a login request, well above the old
# hex-encoding's zero cost.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1


def generate_subscriber_id(email: str) -> str:
    """Generate a unique subscriber ID from email"""
    # Use full SHA256 hash to avoid collisions
    return hashlib.sha256(email.encode()).hexdigest()


def get_subscriber_by_email(email: str):
    """Get subscriber by email, trying both old and new ID formats"""
    if not db:
        return None

    # Try new format first (full hash)
    new_id = generate_subscriber_id(email)
    subscriber_doc = db.collection('subscribers').document(new_id).get()
    if subscriber_doc.exists:
        return subscriber_doc

    # Try old format (16 chars) for backward compatibility
    old_id = hashlib.sha256(email.encode()).hexdigest()[:16]
    subscriber_doc = db.collection('subscribers').document(old_id).get()
    if subscriber_doc.exists:
        return subscriber_doc

    return None


def resolve_generation_subscriber_id(subscriber_id: Optional[str] = None) -> str:
    """Use an explicit subscriber, else Gary's admin account (gwelz@gc.cuny.edu).

    System-generated test episodes must not land as 'unknown subscriber'.
    """
    if subscriber_id and str(subscriber_id).strip():
        return str(subscriber_id).strip()
    doc = get_subscriber_by_email(ADMIN_SUBSCRIBER_EMAIL)
    if doc:
        return doc.id
    return generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL)


# --- Session tokens (security lockdown Step 2, 2026-10-01) ---------------
#
# Issued once at login. Only sha256(token) plus an expiry is ever stored on
# the subscriber doc -- the raw token is returned to the client exactly once
# and never persisted server-side. Comparison uses secrets.compare_digest to
# avoid a timing side-channel.

def issue_session_token() -> Tuple[str, str, str]:
    """Returns (raw_token_for_client, sha256_to_store, iso_expiry)."""
    raw = secrets.token_urlsafe(32)
    stored_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.utcnow() + timedelta(hours=SESSION_TOKEN_TTL_HOURS)).isoformat()
    return raw, stored_hash, expires


def verify_session_token(subscriber_doc_dict: dict, provided_raw_token: Optional[str]) -> bool:
    """Check a caller-supplied raw token against the sha256 stored on the doc."""
    if not provided_raw_token:
        return False
    stored_hash = subscriber_doc_dict.get('session_token_hash')
    expires = subscriber_doc_dict.get('session_token_expires')
    if not stored_hash or not expires:
        return False
    provided_hash = hashlib.sha256(provided_raw_token.encode()).hexdigest()
    if not secrets.compare_digest(provided_hash, stored_hash):
        return False
    try:
        return datetime.fromisoformat(expires) >= datetime.utcnow()
    except ValueError:
        return False


# --- Passwords (security lockdown Step 2, 2026-10-01) ---------------------
#
# Replaces the old password.encode().hex() "hash" (reversible, not a hash)
# with salted hashlib.scrypt. A legacy hex-encoded value is accepted exactly
# once on login, then immediately rehashed to scrypt and rewritten -- the
# caller (login_subscriber) is responsible for doing that rewrite using the
# `was_legacy` flag this returns.

def hash_password(password: str) -> str:
    """scrypt hash, salted, stored as 'scrypt$<salt-hex>$<hash-hex>'."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, stored: str) -> Tuple[bool, bool]:
    """Returns (matches, was_legacy). was_legacy=True means the caller should
    rehash and persist the new value immediately -- this function only
    verifies, it never writes."""
    if not stored:
        return False, False
    if stored.startswith("scrypt$"):
        try:
            _, salt_hex, dk_hex = stored.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            dk = hashlib.scrypt(plain_password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
            return secrets.compare_digest(dk.hex(), dk_hex), False
        except (ValueError, IndexError):
            structured_logger.warning("Malformed scrypt password_hash on subscriber doc")
            return False, False
    # Legacy format: password.encode().hex(). Still checked with
    # compare_digest even though it isn't a real hash, since there's no
    # reason to skip the timing hygiene while it's still in use.
    legacy_ok = secrets.compare_digest(plain_password.encode().hex(), stored)
    return legacy_ok, legacy_ok
