"""Integration tests for the `engine` param on GET /api/content/browse
(architecture review Phase 2, gap 1, 2026-10-02)."""
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.content.routes import router
    from config.engine_registry import engine_tags

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _mock_scoped_db():
    """A db mock whose .where(...).count().get() and .order_by(...).stream()
    both return an empty-but-successful result, so the route runs its full
    engine-scoping branch without touching real Firestore."""
    count_snapshot = MagicMock()
    count_snapshot.value = 0
    db = MagicMock()
    chain = db.collection.return_value.where.return_value
    chain.count.return_value.get.return_value = [[count_snapshot]]
    chain.order_by.return_value.limit.return_value.offset.return_value.stream.return_value = []
    return db


def test_invalid_engine_returns_400():
    with patch('endpoints.content.routes.db', _mock_scoped_db()):
        response = client.get("/api/content/browse", params={"content_type": "papers", "engine": "biology"})
    assert response.status_code == 400
    assert "Invalid engine" in response.json()["detail"]


def test_engine_and_question_together_returns_400():
    with patch('endpoints.content.routes.db', _mock_scoped_db()):
        response = client.get(
            "/api/content/browse",
            params={"content_type": "papers", "engine": "glmp", "question": "glmp-q1"},
        )
    assert response.status_code == 400
    assert "either" in response.json()["detail"].lower()


def test_valid_engine_is_accepted_and_filters_by_array_contains_any():
    mock_db = _mock_scoped_db()
    with patch('endpoints.content.routes.db', mock_db):
        response = client.get("/api/content/browse", params={"content_type": "papers", "engine": "glmp"})
    assert response.status_code == 200
    where_call = mock_db.collection.return_value.where.call_args
    filter_obj = where_call.kwargs.get("filter") or where_call.args[0]
    assert filter_obj.op_string == "array_contains_any"
    assert filter_obj.field_path == "question_scope_ids"
    assert filter_obj.value == engine_tags("glmp")


def test_each_valid_engine_id_is_accepted():
    for engine_id in ("glmp", "atap", "tdap"):
        with patch('endpoints.content.routes.db', _mock_scoped_db()):
            response = client.get("/api/content/browse", params={"content_type": "papers", "engine": engine_id})
        assert response.status_code == 200, f"engine={engine_id} should be accepted"


def test_no_engine_param_is_unaffected_all_projects_default():
    # "All projects" (no engine param at all) must take the pre-existing
    # unscoped path, not the new engine branch -- this is the explicit
    # "stays exactly as today" requirement from Gary's decision.
    mock_db = _mock_scoped_db()
    mock_db.collection.return_value.count.return_value.get.return_value = [[MagicMock(value=0)]]
    mock_db.collection.return_value.order_by.return_value.order_by.return_value.limit.return_value.offset.return_value.stream.return_value = []
    with patch('endpoints.content.routes.db', mock_db):
        response = client.get("/api/content/browse", params={"content_type": "papers"})
    assert response.status_code == 200
    # The engine-scoping .where() must never be called when engine is absent.
    mock_db.collection.return_value.where.assert_not_called()


# --- PR #32 review, change 2: no silent ignores -----------------------------

def test_engine_and_keyword_together_returns_400_not_silent_ignore():
    with patch('endpoints.content.routes.db', _mock_scoped_db()):
        response = client.get(
            "/api/content/browse",
            params={"content_type": "papers", "engine": "glmp", "keyword": "CRP"},
        )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "keyword" in detail and "not yet supported" in detail


def test_engine_and_discipline_together_returns_400_not_silent_ignore():
    with patch('endpoints.content.routes.db', _mock_scoped_db()):
        response = client.get(
            "/api/content/browse",
            params={"content_type": "papers", "engine": "glmp", "discipline": "biology"},
        )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "discipline" in detail and "not yet supported" in detail


# --- PR #32 review, change 3: oversized engine is a clean 500, not a
# raw AssertionError ---------------------------------------------------------

def test_oversized_engine_returns_clean_500_not_raw_assertion_error():
    from config.engine_registry import ENGINE_REGISTRY, ARRAY_CONTAINS_ANY_MAX_VALUES
    oversized = {
        "label": "Oversized",
        "full_name": "Hypothetical oversized engine",
        "tags": [f"oversized-q{i}" for i in range(ARRAY_CONTAINS_ANY_MAX_VALUES + 1)],
    }
    with patch.dict(ENGINE_REGISTRY, {"oversized": oversized}), \
         patch('endpoints.content.routes.db', _mock_scoped_db()):
        response = client.get("/api/content/browse", params={"content_type": "papers", "engine": "oversized"})
    assert response.status_code == 500
    assert "array_contains_any" in response.json()["detail"]
