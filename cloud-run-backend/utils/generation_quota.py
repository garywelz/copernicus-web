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
from typing import Any, Callable, Dict, Optional, Tuple

from google.cloud import firestore

# The plain message an owner sees at 429 (design Q6, 2026-10-29). Nothing else goes in the response: no count, no quota, no date.
QUOTA_MESSAGE = "monthly limit reached"
MAX_MONTHLY_QUOTA = 200


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
        raise QuotaExceeded(QUOTA_MESSAGE)

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


# --- Admin: read and set the quota (PR 1, design 7.3) ----------------------------------------------------------------------------------------
def validate_quota_value(value: Any) -> Optional[int]:
    """An integer 0..MAX_MONTHLY_QUOTA, or None for unlimited. Booleans and floats are refused (True would otherwise pass as 1)."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > MAX_MONTHLY_QUOTA:
        raise ValueError(f"monthly_quota must be an integer from 0 to {MAX_MONTHLY_QUOTA}, or null for unlimited")
    return value


def read_quota(db, subscriber_id: str) -> Optional[Dict[str, Any]]:
    """The quota state of one subscriber, or None when there is no such subscriber. A count that belongs to an earlier month reads as 0."""
    snap = db.collection("subscribers").document(subscriber_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    month = current_month_key()
    used = data.get("generations_this_month", 0) if data.get("generation_month") == month else 0
    return {"subscriber_id": subscriber_id, "monthly_quota": data.get("monthly_quota"), "can_generate": bool(data.get("can_generate", False)),
            "generations_this_month": used, "generation_month": month,
            "refunds_this_month": data.get("refunds_this_month", 0) if data.get("refunds_month") == month else 0}


def set_quota(db, subscriber_id: str, value: Optional[int]) -> Optional[Dict[str, Any]]:
    """Set monthly_quota (None = unlimited). Returns {previous, current} or None when there is no such subscriber. Leaves can_generate and the count alone."""
    ref = db.collection("subscribers").document(subscriber_id)
    snap = ref.get()
    if not snap.exists:
        return None
    previous = (snap.to_dict() or {}).get("monthly_quota")
    ref.update({"monthly_quota": value})
    return {"previous": previous, "current": value}


# --- Refund of a generation that failed before anything was spent (PR 1, design Q6) ---------------------------------------------------------
def quota_stamp(auth: Optional[dict]) -> Dict[str, Any]:
    """Fields for a new job record, so a later failure can be refunded. Only a metered (subscriber) request is stamped; the admin key is unmetered."""
    if isinstance(auth, dict) and auth.get("via") == "subscriber":
        return {"quota_counted": True, "quota_month": current_month_key()}
    return {}


def _refund_in_transaction(transaction, subscriber_ref, month: str) -> bool:
    data = subscriber_ref.get(transaction=transaction).to_dict() or {}
    count = data.get("generations_this_month", 0)
    if data.get("generation_month") != month or count <= 0:
        return False                      # the count was reset (a new month) or is already zero: nothing to give back
    refunds = data.get("refunds_this_month", 0) if data.get("refunds_month") == month else 0
    transaction.update(subscriber_ref, {"generations_this_month": count - 1, "refunds_this_month": refunds + 1, "refunds_month": month})
    return True


def refund_one(db, subscriber_id: str, month: str, run: Optional[Callable] = None) -> bool:
    """Give one generation back, atomically, if the stored count still belongs to `month` and is above zero."""
    ref = db.collection("subscribers").document(subscriber_id)
    if run is None:
        return firestore.transactional(_refund_in_transaction)(db.transaction(), ref, month)
    return run(_refund_in_transaction, ref, month)


def _claim_refund(transaction, job_ref) -> Tuple[bool, str]:
    """Decide, inside one transaction on the job record, whether this job may be refunded, and mark it refunded so a second call cannot repeat it.

    A refund is SAFE only when ALL of these hold:
      1. the job was metered: it carries quota_counted (stamped when the request was accepted) and the month it was counted in;
      2. the job has failed (status == 'failed');
      3. no text-to-speech request was ever sent for it: the job has no tts_started_at mark (written before the first speech request) and no
         tts_segments / tts_characters (the usage record): nothing paid for was used;
      4. the job produced no result (no audio, no episode);
      5. it has not been refunded already (quota_refunded is absent).
    """
    job = job_ref.get(transaction=transaction).to_dict() or {}
    if not job.get("quota_counted") or not job.get("quota_month"):
        return False, "not_metered"
    if job.get("quota_refunded"):
        return False, "already_refunded"
    if job.get("status") != "failed":
        return False, "not_failed"
    if job.get("tts_started_at"):
        return False, "tts_started"       # the mark is written before the first speech request, so it survives a failed usage write
    if (job.get("tts_segments") or 0) > 0 or (job.get("tts_characters") or 0) > 0:
        return False, "tts_characters_spent"
    if job.get("result"):
        return False, "produced_a_result"
    transaction.update(job_ref, {"quota_refunded": True, "quota_refund_reason": "failed_before_any_tts"})
    return True, "ok"


def refund_failed_job(db, job_id: str, run: Optional[Callable] = None) -> Tuple[bool, str]:
    """Refund the quota unit a failed job used, when that is safe (see _claim_refund). Never raises: a refund problem must not hide the real failure.
    Returns (refunded, reason)."""
    try:
        job_ref = db.collection("podcast_jobs").document(job_id)
        if run is None:
            claimed, reason = firestore.transactional(_claim_refund)(db.transaction(), job_ref)
        else:
            claimed, reason = run(_claim_refund, job_ref)
        if not claimed:
            return False, reason
        job = job_ref.get().to_dict() or {}
        gave_back = refund_one(db, job.get("subscriber_id"), job.get("quota_month"), run)
        return (True, "ok") if gave_back else (False, "count_already_reset")
    except Exception as exc:                                    # noqa: BLE001 - see docstring
        return False, f"refund_error:{type(exc).__name__}"


def refund_unstarted(db, auth: Optional[dict], run: Optional[Callable] = None) -> bool:
    """Give back the unit when a request was counted but no job was ever created (the job write failed, or the service was unavailable). Never raises."""
    try:
        if isinstance(auth, dict) and auth.get("via") == "subscriber":
            return refund_one(db, auth["subscriber_id"], current_month_key(), run)
    except Exception:                                           # noqa: BLE001
        pass
    return False
