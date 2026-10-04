"""Integration tests for the `engine` param on GET /api/vector-search/semantic
(architecture review Phase 2, gap 1, RAG + Search, 2026-10-04)."""
import json
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.vector_search.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _mock_search_semantic_result():
    async def _search_semantic(**kwargs):
        _search_semantic.last_kwargs = kwargs
        return json.dumps({
            "query": kwargs.get("query"),
            "papers": [], "podcasts": [], "glmp_processes": [], "math_processes": [],
            "chemistry_processes": [], "physics_processes": [],
            "computer_science_processes": [], "biology_processes": [], "videos": [],
            "content_types_searched": [], "search_method": "vector_semantic",
        })
    return _search_semantic


def test_invalid_engine_returns_400():
    response = client.get("/api/vector-search/semantic", params={"query": "test", "engine": "biology"})
    assert response.status_code == 400
    assert "Invalid engine" in response.json()["detail"]


def test_valid_engine_resolves_tags_and_reaches_search_semantic():
    mock_fn = _mock_search_semantic_result()
    with patch('endpoints.vector_search.routes.search_semantic', mock_fn):
        response = client.get("/api/vector-search/semantic", params={"query": "test", "engine": "tdap"})
    assert response.status_code == 200
    from config.engine_registry import engine_tags
    assert mock_fn.last_kwargs["engine_tags"] == engine_tags("tdap")


def test_no_engine_param_passes_none_through_unchanged():
    mock_fn = _mock_search_semantic_result()
    with patch('endpoints.vector_search.routes.search_semantic', mock_fn):
        response = client.get("/api/vector-search/semantic", params={"query": "test"})
    assert response.status_code == 200
    assert mock_fn.last_kwargs["engine_tags"] is None


def test_each_valid_engine_id_is_accepted():
    for engine_id in ("glmp", "atap", "tdap"):
        mock_fn = _mock_search_semantic_result()
        with patch('endpoints.vector_search.routes.search_semantic', mock_fn):
            response = client.get("/api/vector-search/semantic", params={"query": "test", "engine": engine_id})
        assert response.status_code == 200, f"engine={engine_id} should be accepted"
