"""Unit tests for generation subscriber attribution."""
from unittest.mock import MagicMock, patch


def test_resolve_generation_subscriber_id_explicit():
    from utils.subscriber_helpers import resolve_generation_subscriber_id
    assert resolve_generation_subscriber_id("abc123") == "abc123"
    assert resolve_generation_subscriber_id("  abc123  ") == "abc123"


def test_resolve_generation_subscriber_id_defaults_to_admin_hash():
    from utils.subscriber_helpers import generate_subscriber_id, resolve_generation_subscriber_id
    from config.constants import ADMIN_SUBSCRIBER_EMAIL

    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.get.return_value.exists = False
    with patch("utils.subscriber_helpers.db", mock_db):
        assert resolve_generation_subscriber_id(None) == generate_subscriber_id(ADMIN_SUBSCRIBER_EMAIL)
        assert ADMIN_SUBSCRIBER_EMAIL == "gwelz@gc.cuny.edu"


def test_resolve_generation_subscriber_id_uses_existing_admin_doc():
    from utils.subscriber_helpers import resolve_generation_subscriber_id

    existing = MagicMock()
    existing.exists = True
    existing.id = "legacy-admin-id"
    mock_db = MagicMock()
    mock_db.collection.return_value.document.return_value.get.return_value = existing
    with patch("utils.subscriber_helpers.db", mock_db):
        assert resolve_generation_subscriber_id("") == "legacy-admin-id"


# --- Passwords (security lockdown Step 2) ---------------------------------

def test_hash_password_is_scrypt_and_round_trips():
    from utils.subscriber_helpers import hash_password, verify_password
    stored = hash_password("correct horse battery staple")
    assert stored.startswith("scrypt$")
    matched, was_legacy = verify_password("correct horse battery staple", stored)
    assert matched is True
    assert was_legacy is False


def test_verify_password_rejects_wrong_password_scrypt():
    from utils.subscriber_helpers import hash_password, verify_password
    stored = hash_password("correct horse battery staple")
    matched, was_legacy = verify_password("wrong password", stored)
    assert matched is False
    assert was_legacy is False


def test_hash_password_is_salted_two_calls_differ():
    from utils.subscriber_helpers import hash_password
    a = hash_password("same password")
    b = hash_password("same password")
    assert a != b  # different random salts


def test_verify_password_accepts_legacy_hex_once_and_flags_it():
    from utils.subscriber_helpers import verify_password
    legacy_stored = "hello world".encode().hex()
    matched, was_legacy = verify_password("hello world", legacy_stored)
    assert matched is True
    assert was_legacy is True  # caller must rehash on this signal


def test_verify_password_rejects_wrong_legacy_password():
    from utils.subscriber_helpers import verify_password
    legacy_stored = "hello world".encode().hex()
    matched, was_legacy = verify_password("goodbye world", legacy_stored)
    assert matched is False


def test_verify_password_handles_empty_stored_value():
    from utils.subscriber_helpers import verify_password
    matched, was_legacy = verify_password("anything", "")
    assert matched is False
    assert was_legacy is False


# --- Session tokens (security lockdown Step 2) ----------------------------

def test_issue_and_verify_session_token_round_trip():
    from utils.subscriber_helpers import issue_session_token, verify_session_token
    raw, stored_hash, expires = issue_session_token()
    assert raw and stored_hash and expires
    doc = {"session_token_hash": stored_hash, "session_token_expires": expires}
    assert verify_session_token(doc, raw) is True


def test_verify_session_token_rejects_wrong_token():
    from utils.subscriber_helpers import issue_session_token, verify_session_token
    _, stored_hash, expires = issue_session_token()
    doc = {"session_token_hash": stored_hash, "session_token_expires": expires}
    assert verify_session_token(doc, "not-the-right-token") is False


def test_verify_session_token_rejects_missing_token():
    from utils.subscriber_helpers import verify_session_token
    doc = {"session_token_hash": "abc", "session_token_expires": "2099-01-01T00:00:00"}
    assert verify_session_token(doc, None) is False
    assert verify_session_token(doc, "") is False


def test_verify_session_token_rejects_expired_token():
    from utils.subscriber_helpers import issue_session_token, verify_session_token
    raw, stored_hash, _ = issue_session_token()
    doc = {"session_token_hash": stored_hash, "session_token_expires": "2000-01-01T00:00:00"}
    assert verify_session_token(doc, raw) is False


def test_verify_session_token_rejects_doc_with_no_token_at_all():
    from utils.subscriber_helpers import verify_session_token
    assert verify_session_token({}, "some-token") is False
