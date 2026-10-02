"""Unit tests for the generation allowlist/quota check (security lockdown Step 2)."""
from unittest.mock import MagicMock
import pytest

from utils.generation_quota import (
    check_and_increment_quota,
    current_month_key,
    GenerationNotAllowed,
    QuotaExceeded,
)


def _mock_db_for(doc_data: dict):
    """A minimal Firestore mock whose transaction decorator just calls the
    wrapped function directly (synchronously), and whose get() returns a
    snapshot carrying doc_data."""
    snapshot = MagicMock()
    snapshot.exists = True
    snapshot.to_dict.return_value = dict(doc_data)

    subscriber_ref = MagicMock()
    subscriber_ref.get.return_value = snapshot

    db = MagicMock()
    db.collection.return_value.document.return_value = subscriber_ref
    db.transaction.return_value = MagicMock()
    return db, subscriber_ref, snapshot


def test_not_found_raises_not_allowed():
    db, ref, snapshot = _mock_db_for({})
    snapshot.exists = False
    with pytest.raises(GenerationNotAllowed):
        check_and_increment_quota(db, "ghost")


def test_can_generate_false_raises_not_allowed():
    db, ref, snapshot = _mock_db_for({"can_generate": False})
    with pytest.raises(GenerationNotAllowed):
        check_and_increment_quota(db, "sub1")


def test_unlimited_quota_increments_without_limit():
    db, ref, snapshot = _mock_db_for({
        "can_generate": True,
        "monthly_quota": None,
        "generations_this_month": 999,
        "generation_month": current_month_key(),
    })
    quota, count = check_and_increment_quota(db, "sub1")
    assert quota is None
    assert count == 1000


def test_quota_remaining_increments_and_returns_new_count():
    db, ref, snapshot = _mock_db_for({
        "can_generate": True,
        "monthly_quota": 20,
        "generations_this_month": 5,
        "generation_month": current_month_key(),
    })
    quota, count = check_and_increment_quota(db, "sub1")
    assert quota == 20
    assert count == 6
    db.transaction.return_value.update.assert_called_once()


def test_quota_exhausted_raises_quota_exceeded():
    db, ref, snapshot = _mock_db_for({
        "can_generate": True,
        "monthly_quota": 20,
        "generations_this_month": 20,
        "generation_month": current_month_key(),
    })
    with pytest.raises(QuotaExceeded):
        check_and_increment_quota(db, "sub1")


def test_stale_month_key_resets_count_before_checking():
    db, ref, snapshot = _mock_db_for({
        "can_generate": True,
        "monthly_quota": 5,
        "generations_this_month": 5,  # would be exhausted for the OLD month
        "generation_month": "2020-01",  # stale -- a prior month
    })
    quota, count = check_and_increment_quota(db, "sub1")
    assert quota == 5
    assert count == 1  # reset, then incremented once
