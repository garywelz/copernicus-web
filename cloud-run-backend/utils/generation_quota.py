"""Generation allowlist and monthly quota (security lockdown Step 2, 2026-10-01).

Fields live directly on each `subscribers` doc -- no names or emails in code,
no separate collection:
  - can_generate: bool
  - monthly_quota: int | None (None = unlimited)
  - generations_this_month: int
  - generation_month: str, "YYYY-MM" -- the month the count above belongs to;
    a stale month key means the count resets to 0 before this check runs.

The check-and-increment is a single Firestore transaction (read, check,
write) so two concurrent requests from the same subscriber near their quota
can't both slip through.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple

from google.cloud import firestore


class GenerationNotAllowed(Exception):
    """can_generate is false (or the subscriber doc doesn't exist)."""


class QuotaExceeded(Exception):
    """monthly_quota is set and generations_this_month has reached it."""


def current_month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _check_and_increment(transaction, subscriber_ref) -> Tuple[Optional[int], int]:
    snapshot = subscriber_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise GenerationNotAllowed("Subscriber not found")

    data = snapshot.to_dict() or {}
    if not data.get("can_generate", False):
        raise GenerationNotAllowed("Generation is by invitation")

    quota = data.get("monthly_quota")  # None = unlimited
    month_key = current_month_key()
    stored_month = data.get("generation_month")
    count = data.get("generations_this_month", 0) if stored_month == month_key else 0

    if quota is not None and count >= quota:
        raise QuotaExceeded(
            f"Monthly generation quota of {quota} reached for this account. "
            f"It resets at the start of next month."
        )

    transaction.update(subscriber_ref, {
        "generations_this_month": count + 1,
        "generation_month": month_key,
    })
    return quota, count + 1


def check_and_increment_quota(db, subscriber_id: str) -> Tuple[Optional[int], int]:
    """Raises GenerationNotAllowed (403) or QuotaExceeded (429) on failure.
    Returns (quota, new_count) on success -- quota is None for unlimited."""
    subscriber_ref = db.collection("subscribers").document(subscriber_id)
    transaction = db.transaction()
    transactional = firestore.transactional(_check_and_increment)
    return transactional(transaction, subscriber_ref)
