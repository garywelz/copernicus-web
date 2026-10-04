"""Unit tests for the engine registry (architecture review Phase 2, gap 1)."""
import pytest

from unittest.mock import patch

from fastapi import HTTPException

from config.engine_registry import (
    ENGINE_REGISTRY,
    ENGINE_IDS,
    ALL_REGISTERED_TAGS,
    ARRAY_CONTAINS_ANY_MAX_VALUES,
    EngineTagLimitExceeded,
    is_valid_engine_id,
    engine_tags,
    engine_label,
    find_unregistered_tags,
    resolve_engine_tags_or_400,
)


def test_engine_ids_are_exactly_glmp_atap_tdap():
    assert set(ENGINE_IDS) == {"glmp", "atap", "tdap"}


def test_is_valid_engine_id_accepts_known_ids():
    assert is_valid_engine_id("glmp") is True
    assert is_valid_engine_id("atap") is True
    assert is_valid_engine_id("tdap") is True


def test_is_valid_engine_id_rejects_unknown_or_empty():
    assert is_valid_engine_id("biology") is False  # the exact confusion this registry exists to prevent
    assert is_valid_engine_id("") is False
    assert is_valid_engine_id(None) is False


def test_engine_tags_returns_nonempty_list_for_each_engine():
    for engine_id in ENGINE_IDS:
        tags = engine_tags(engine_id)
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert all(tag.startswith(f"{engine_id}-") for tag in tags)


def test_engine_tags_raises_keyerror_for_unknown_engine():
    with pytest.raises(KeyError):
        engine_tags("not-a-real-engine")


def test_every_engine_is_under_the_array_contains_any_limit():
    for engine_id in ENGINE_IDS:
        assert len(engine_tags(engine_id)) <= ARRAY_CONTAINS_ANY_MAX_VALUES


def test_glmp_has_exactly_twelve_tags():
    # Pinned to the live Firestore scan this registry was built from
    # (2026-10-02) -- a change here should be deliberate, not accidental.
    assert len(engine_tags("glmp")) == 12


def test_atap_has_exactly_nine_tags():
    assert len(engine_tags("atap")) == 9


def test_tdap_has_exactly_two_tags():
    assert len(engine_tags("tdap")) == 2


def test_engine_label_matches_known_display_names():
    assert engine_label("glmp") == "GLMP"
    assert engine_label("atap") == "ATAP"
    assert engine_label("tdap") == "TDAP"


def test_no_tag_is_shared_across_two_engines():
    all_tags = []
    for engine_id in ENGINE_IDS:
        all_tags.extend(engine_tags(engine_id))
    assert len(all_tags) == len(set(all_tags))


# --- PR #32 review, change 1: registry drift detection ---------------------

def test_find_unregistered_tags_empty_when_live_matches_registry():
    assert find_unregistered_tags(ALL_REGISTERED_TAGS) == set()


def test_find_unregistered_tags_catches_a_new_question_id():
    # The exact scenario named in the review: a new question (e.g. a
    # hypothetical tdap-q3) starts being tagged in production before the
    # registry is updated to know about it.
    live = set(ALL_REGISTERED_TAGS) | {"tdap-q3"}
    assert find_unregistered_tags(live) == {"tdap-q3"}


def test_find_unregistered_tags_catches_an_entirely_unknown_prefix():
    live = set(ALL_REGISTERED_TAGS) | {"newengine-q1"}
    assert find_unregistered_tags(live) == {"newengine-q1"}


def test_find_unregistered_tags_handles_multiple_drifted_tags():
    live = set(ALL_REGISTERED_TAGS) | {"tdap-q3", "tdap-q4", "atap-q5"}
    assert find_unregistered_tags(live) == {"tdap-q3", "tdap-q4", "atap-q5"}


def test_find_unregistered_tags_ignores_tags_missing_from_live_not_present():
    # A tag registered but never (yet) seen live is not drift in this
    # direction -- this check is specifically "live has something the
    # registry doesn't," not the reverse.
    live = set(ALL_REGISTERED_TAGS) - {"tdap-q2"}
    assert find_unregistered_tags(live) == set()


# --- PR #32 review, change 3: the 30-value limit is a caught error, not an
# unhandled assert ------------------------------------------------------

def test_engine_tags_raises_clean_error_past_the_firestore_limit():
    oversized = {
        "label": "Oversized",
        "full_name": "Hypothetical oversized engine",
        "tags": [f"oversized-q{i}" for i in range(ARRAY_CONTAINS_ANY_MAX_VALUES + 1)],
    }
    with patch.dict(ENGINE_REGISTRY, {"oversized": oversized}):
        with pytest.raises(EngineTagLimitExceeded) as exc_info:
            engine_tags("oversized")
        assert exc_info.value.engine_id == "oversized"
        assert exc_info.value.tag_count == ARRAY_CONTAINS_ANY_MAX_VALUES + 1
        assert "array_contains_any" in str(exc_info.value)


def test_engine_tags_at_exactly_the_limit_does_not_raise():
    at_limit = {
        "label": "AtLimit",
        "full_name": "Hypothetical engine at exactly the limit",
        "tags": [f"atlimit-q{i}" for i in range(ARRAY_CONTAINS_ANY_MAX_VALUES)],
    }
    with patch.dict(ENGINE_REGISTRY, {"atlimit": at_limit}):
        tags = engine_tags("atlimit")  # must not raise
        assert len(tags) == ARRAY_CONTAINS_ANY_MAX_VALUES


# --- resolve_engine_tags_or_400 (RAG + Search PR, 2026-10-04) --------------

def test_resolve_engine_tags_returns_none_when_engine_not_set():
    assert resolve_engine_tags_or_400(None, None) is None
    assert resolve_engine_tags_or_400("", None) is None


def test_resolve_engine_tags_returns_tags_for_valid_engine():
    assert resolve_engine_tags_or_400("glmp", None) == engine_tags("glmp")


def test_resolve_engine_tags_400_when_both_engine_and_question_given():
    with pytest.raises(HTTPException) as exc_info:
        resolve_engine_tags_or_400("glmp", "glmp-q1")
    assert exc_info.value.status_code == 400
    assert "either" in exc_info.value.detail.lower()


def test_resolve_engine_tags_400_for_invalid_engine_id():
    with pytest.raises(HTTPException) as exc_info:
        resolve_engine_tags_or_400("biology", None)
    assert exc_info.value.status_code == 400
    assert "Invalid engine" in exc_info.value.detail


def test_resolve_engine_tags_500_for_oversized_engine():
    oversized = {
        "label": "Oversized",
        "full_name": "Hypothetical oversized engine",
        "tags": [f"oversized-q{i}" for i in range(ARRAY_CONTAINS_ANY_MAX_VALUES + 1)],
    }
    with patch.dict(ENGINE_REGISTRY, {"oversized": oversized}):
        with pytest.raises(HTTPException) as exc_info:
            resolve_engine_tags_or_400("oversized", None)
        assert exc_info.value.status_code == 500
        assert "array_contains_any" in exc_info.value.detail


def test_resolve_engine_tags_works_for_every_real_engine():
    for engine_id in ENGINE_IDS:
        assert resolve_engine_tags_or_400(engine_id, None) == engine_tags(engine_id)
