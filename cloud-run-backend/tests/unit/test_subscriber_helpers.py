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
