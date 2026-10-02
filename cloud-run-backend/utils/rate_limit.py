"""Per-client rate limiting (security lockdown Step 2, 2026-10-01).

Firestore-backed so the limit holds across Cloud Run instances, rather than
per-instance in-memory counters that reset on every cold start and don't
share state with sibling instances.

Fails OPEN: if Firestore is unavailable, misconfigured, or errors for any
reason, the call is allowed through rather than taking down the feature the
limiter is meant to protect. A rate limiter that can 500 the public "Ask
Questions" feature is a worse outcome than a limiter that occasionally lets
a burst through.
"""

from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

RATE_LIMIT_COLLECTION = "rate_limits"


def last_forwarded_ip(x_forwarded_for: Optional[str]) -> str:
    """The LAST address in X-Forwarded-For is the one Google's front end
    appends itself, not something the client sent -- the client fully
    controls every entry before it, including the first, so keying on the
    first address lets anyone evade the limit by sending a fabricated
    X-Forwarded-For with a different fake "first" IP on every request.
    The last entry is the only one in the header the caller can't forge."""
    if not x_forwarded_for:
        return "unknown"
    parts = [p.strip() for p in x_forwarded_for.split(",") if p.strip()]
    return parts[-1] if parts else "unknown"


def _bucket_doc_id(client_key: str, route: str) -> str:
    # Hash the identifying key before using it as a Firestore document ID,
    # so a raw client IP never appears as a literal, human-readable doc ID
    # in the collection.
    import hashlib
    return hashlib.sha256(f"{route}:{client_key}".encode()).hexdigest()


def _check_and_increment(transaction, ref, now: datetime, window_seconds: int):
    snapshot = ref.get(transaction=transaction)
    data = snapshot.to_dict() if snapshot.exists else {}
    window_start_str = data.get("window_start")
    count = data.get("count", 0)

    window_start = None
    if window_start_str:
        try:
            window_start = datetime.fromisoformat(window_start_str)
        except ValueError:
            window_start = None

    if not window_start or (now - window_start).total_seconds() >= window_seconds:
        transaction.set(ref, {"window_start": now.isoformat(), "count": 1})
        return 1

    new_count = count + 1
    transaction.set(ref, {"window_start": window_start_str, "count": new_count})
    return new_count


def check_rate_limit(db, client_key: str, route: str, limit: int, window_seconds: int) -> None:
    """Raises fastapi.HTTPException(429) if `client_key` has exceeded `limit`
    requests to `route` within the trailing `window_seconds`. Fails open
    (returns normally, no exception) on any Firestore error, including
    `db` being None -- by design, see module docstring."""
    from fastapi import HTTPException  # local import: keep this module
                                        # importable without a FastAPI app

    if not db:
        return
    try:
        ref = db.collection(RATE_LIMIT_COLLECTION).document(_bucket_doc_id(client_key, route))
        now = datetime.now(timezone.utc)
        transaction = db.transaction()
        transactional = firestore.transactional(_check_and_increment)
        new_count = transactional(transaction, ref, now, window_seconds)
    except Exception:
        # Fail open.
        return

    if new_count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests per hour. Please try again later."
        )
