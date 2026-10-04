"""Unit tests for the engine registry (architecture review Phase 2, gap 1)."""
import pytest

from config.engine_registry import (
    ENGINE_REGISTRY,
    ENGINE_IDS,
    ARRAY_CONTAINS_ANY_MAX_VALUES,
    is_valid_engine_id,
    engine_tags,
    engine_label,
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
