"""Unit tests for the Firestore-backed per-client rate limiter
(security lockdown Step 2, 2026-10-01)."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from utils.rate_limit import check_rate_limit, last_forwarded_ip


# --- last_forwarded_ip -------------------------------------------------------

def test_last_forwarded_ip_takes_last_of_several():
    assert last_forwarded_ip("1.2.3.4, 5.6.7.8, 9.10.11.12") == "9.10.11.12"


def test_last_forwarded_ip_single_value():
    assert last_forwarded_ip("1.2.3.4") == "1.2.3.4"


def test_last_forwarded_ip_missing_header():
    assert last_forwarded_ip(None) == "unknown"
    assert last_forwarded_ip("") == "unknown"


def test_last_forwarded_ip_ignores_spoofed_leading_entries():
    # A client can send any number of fabricated addresses before the one
    # Google's front end appends -- varying the FIRST entry on every
    # request must not change the key the limiter buckets on, or an
    # attacker evades the limit trivially by spoofing a new fake "first"
    # IP each time.
    real_client_appended_by_google = "203.0.113.7"
    header_attempt_1 = f"1.1.1.1, {real_client_appended_by_google}"
    header_attempt_2 = f"9.9.9.9, 8.8.8.8, {real_client_appended_by_google}"
    header_attempt_3 = f"evil-spoofed-value, {real_client_appended_by_google}"
    assert last_forwarded_ip(header_attempt_1) == real_client_appended_by_google
    assert last_forwarded_ip(header_attempt_2) == real_client_appended_by_google
    assert last_forwarded_ip(header_attempt_3) == real_client_appended_by_google


def test_last_forwarded_ip_handles_trailing_comma_or_whitespace():
    assert last_forwarded_ip("1.2.3.4, 5.6.7.8, ") == "5.6.7.8"
    assert last_forwarded_ip("  1.2.3.4  ,  5.6.7.8  ") == "5.6.7.8"


# --- check_rate_limit --------------------------------------------------------

def _mock_db_with_doc(doc_data):
    snapshot = MagicMock()
    snapshot.exists = bool(doc_data)
    snapshot.to_dict.return_value = dict(doc_data) if doc_data else None

    ref = MagicMock()
    ref.get.return_value = snapshot

    db = MagicMock()
    db.collection.return_value.document.return_value = ref
    db.transaction.return_value = MagicMock()
    return db


def test_fails_open_when_db_is_none():
    # Must not raise -- this is the whole point of fail-open.
    check_rate_limit(None, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)


def test_fails_open_when_firestore_errors():
    db = MagicMock()
    db.collection.side_effect = RuntimeError("Firestore is down")
    # Must not raise.
    check_rate_limit(db, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)


def test_first_request_in_a_new_window_is_allowed():
    db = _mock_db_with_doc({})  # no existing doc
    check_rate_limit(db, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)  # no raise


def test_under_limit_is_allowed():
    now = datetime.now(timezone.utc)
    db = _mock_db_with_doc({"window_start": now.isoformat(), "count": 10})
    check_rate_limit(db, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)  # no raise


def test_over_limit_raises_429():
    now = datetime.now(timezone.utc)
    db = _mock_db_with_doc({"window_start": now.isoformat(), "count": 20})
    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(db, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)
    assert exc_info.value.status_code == 429


def test_expired_window_resets_even_if_previously_over_limit():
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    db = _mock_db_with_doc({"window_start": old.isoformat(), "count": 999})
    check_rate_limit(db, "1.2.3.4", "rag_answer", limit=20, window_seconds=3600)  # no raise


def test_different_ips_are_independent_buckets():
    # Each client_key hashes to a different doc id -- just confirm the
    # bucket-id helper is sensitive to the client key.
    from utils.rate_limit import _bucket_doc_id
    a = _bucket_doc_id("1.2.3.4", "rag_answer")
    b = _bucket_doc_id("5.6.7.8", "rag_answer")
    assert a != b


def test_different_routes_are_independent_buckets():
    from utils.rate_limit import _bucket_doc_id
    a = _bucket_doc_id("1.2.3.4", "rag_answer")
    b = _bucket_doc_id("1.2.3.4", "some_other_route")
    assert a != b


def test_spoofed_leading_entries_still_land_in_the_same_bucket_end_to_end():
    # End-to-end: two requests that spoof a different FIRST address on
    # X-Forwarded-For, but share the same real (Google-appended) last
    # address, must bucket together -- i.e. the spoofing gains the caller
    # nothing against check_rate_limit itself, not just against the
    # last_forwarded_ip helper in isolation.
    from utils.rate_limit import _bucket_doc_id
    real_ip = "203.0.113.7"
    key_from_attempt_1 = last_forwarded_ip(f"1.1.1.1, {real_ip}")
    key_from_attempt_2 = last_forwarded_ip(f"9.9.9.9, 8.8.8.8, {real_ip}")
    assert key_from_attempt_1 == key_from_attempt_2 == real_ip
    assert _bucket_doc_id(key_from_attempt_1, "rag_answer") == _bucket_doc_id(key_from_attempt_2, "rag_answer")
