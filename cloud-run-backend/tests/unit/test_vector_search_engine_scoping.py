"""Unit tests for search_semantic()'s engine_tags scoping (architecture
review Phase 2, gap 1, RAG + Search, 2026-10-04).

Focused on the three papers-branch code paths (engine_tags / question /
unscoped) and content-type skipping -- not a full re-test of every
content type search_semantic() touches."""
import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest


def _mock_embedding_service():
    svc = MagicMock()
    svc.embed_text.return_value = [0.1] * 1536
    return svc


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@patch("mcp_server.tools.vector_search.get_embedding_service")
@patch("mcp_server.tools.vector_search.get_firestore_client")
def test_engine_tags_uses_where_then_find_nearest_not_in_memory_rerank(mock_get_db, mock_get_embed):
    from mcp_server.tools.vector_search import search_semantic

    mock_get_embed.return_value = _mock_embedding_service()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    where_result = mock_db.collection.return_value.where.return_value
    where_result.find_nearest.return_value.stream.return_value = []

    result_json = _run(search_semantic(
        query="test query",
        content_types=["papers"],
        engine_tags=["glmp-q1", "glmp-q2"],
    ))
    result = json.loads(result_json)

    # The engine path must go through .where(...).find_nearest(...), not a
    # bare .stream() over the whole matched set (that's the old in-memory
    # rerank pattern, deliberately not used for engine scope).
    where_call = mock_db.collection.return_value.where.call_args
    filter_obj = where_call.kwargs.get("filter") or where_call.args[0]
    assert filter_obj.op_string == "array_contains_any"
    assert filter_obj.field_path == "question_scope_ids"
    assert filter_obj.value == ["glmp-q1", "glmp-q2"]
    where_result.find_nearest.assert_called_once()
    assert result["papers"] == []


@patch("mcp_server.tools.vector_search.get_embedding_service")
@patch("mcp_server.tools.vector_search.get_firestore_client")
def test_engine_tags_skips_non_paper_content_types(mock_get_db, mock_get_embed):
    from mcp_server.tools.vector_search import search_semantic

    mock_get_embed.return_value = _mock_embedding_service()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.collection.return_value.where.return_value.find_nearest.return_value.stream.return_value = []

    result_json = _run(search_semantic(
        query="test query",
        content_types=["papers", "podcasts", "videos"],
        engine_tags=["glmp-q1"],
    ))
    result = json.loads(result_json)

    assert result["content_types_searched"] == ["papers"]
    assert set(result["question_scope_skipped_content_types"]) == {"podcasts", "videos"}


@patch("mcp_server.tools.vector_search.get_embedding_service")
@patch("mcp_server.tools.vector_search.get_firestore_client")
def test_question_alone_still_uses_in_memory_rerank_unchanged(mock_get_db, mock_get_embed):
    # Regression: the pre-existing single-tag `question` path must be
    # completely untouched by this change -- still a plain .stream() over
    # the array_contains-matched set (no find_nearest at all), per Gary's
    # "keep the existing single-tag question parameter working as it does
    # today."
    from mcp_server.tools.vector_search import search_semantic

    mock_get_embed.return_value = _mock_embedding_service()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.collection.return_value.where.return_value.stream.return_value = []

    result_json = _run(search_semantic(
        query="test query",
        content_types=["papers"],
        question="glmp-q1",
    ))
    result = json.loads(result_json)

    where_call = mock_db.collection.return_value.where.call_args
    filter_obj = where_call.kwargs.get("filter") or where_call.args[0]
    assert filter_obj.op_string == "array_contains"
    assert filter_obj.value == "glmp-q1"
    # find_nearest must never be called on this path.
    mock_db.collection.return_value.where.return_value.find_nearest.assert_not_called()
    assert result["papers"] == []


@patch("mcp_server.tools.vector_search.get_embedding_service")
@patch("mcp_server.tools.vector_search.get_firestore_client")
def test_neither_engine_nor_question_uses_unscoped_find_nearest(mock_get_db, mock_get_embed):
    from mcp_server.tools.vector_search import search_semantic

    mock_get_embed.return_value = _mock_embedding_service()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.collection.return_value.find_nearest.return_value.stream.return_value = []

    result_json = _run(search_semantic(
        query="test query",
        content_types=["papers"],
    ))
    result = json.loads(result_json)

    # Unscoped: find_nearest() called directly on the collection, no .where()
    # pre-filter involved at all.
    mock_db.collection.return_value.where.assert_not_called()
    mock_db.collection.return_value.find_nearest.assert_called_once()
    assert result["question_scope_skipped_content_types"] == []
    assert result["papers"] == []


@patch("mcp_server.tools.vector_search.get_embedding_service")
@patch("mcp_server.tools.vector_search.get_firestore_client")
def test_engine_tags_takes_priority_if_both_somehow_present(mock_get_db, mock_get_embed):
    # Defensive: the route layer enforces mutual exclusion, but if both
    # arrive here anyway, engine_tags must win deterministically rather
    # than the behavior being undefined.
    from mcp_server.tools.vector_search import search_semantic

    mock_get_embed.return_value = _mock_embedding_service()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.collection.return_value.where.return_value.find_nearest.return_value.stream.return_value = []

    _run(search_semantic(
        query="test query",
        content_types=["papers"],
        question="glmp-q1",
        engine_tags=["glmp-q1", "glmp-q2"],
    ))

    where_call = mock_db.collection.return_value.where.call_args
    filter_obj = where_call.kwargs.get("filter") or where_call.args[0]
    assert filter_obj.op_string == "array_contains_any"
    mock_db.collection.return_value.where.return_value.find_nearest.assert_called_once()
