"""Integration tests for the `engine` param on GET /api/rag/answer
(architecture review Phase 2, gap 1, RAG + Search, 2026-10-04)."""
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.rag.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _no_rate_limit_and_mocked_rag():
    """Patch the rate limiter out (not what this file tests) and the RAG
    service so no real LLM/Firestore call happens."""
    mock_result = {
        "answer": "stub answer",
        "citations": [],
        "sources": [],
        "metadata": {},
    }
    mock_service = MagicMock()

    async def _answer_question(**kwargs):
        _answer_question.last_kwargs = kwargs
        return mock_result

    mock_service.answer_question = _answer_question
    return mock_service


def test_engine_and_question_scope_together_returns_400():
    with patch('endpoints.rag.routes.check_rate_limit'):
        response = client.get(
            "/api/rag/answer",
            params={"question": "what is X?", "engine": "glmp", "question_scope": "glmp-q1"},
        )
    assert response.status_code == 400
    assert "either" in response.json()["detail"].lower()


def test_invalid_engine_returns_400():
    with patch('endpoints.rag.routes.check_rate_limit'):
        response = client.get(
            "/api/rag/answer",
            params={"question": "what is X?", "engine": "biology"},
        )
    assert response.status_code == 400
    assert "Invalid engine" in response.json()["detail"]


def test_valid_engine_resolves_tags_and_reaches_rag_service():
    mock_service = _no_rate_limit_and_mocked_rag()
    with patch('endpoints.rag.routes.check_rate_limit'), \
         patch('endpoints.rag.routes.get_rag_service', return_value=mock_service):
        response = client.get(
            "/api/rag/answer",
            params={"question": "what is CRP?", "engine": "glmp"},
        )
    assert response.status_code == 200
    from config.engine_registry import engine_tags
    assert mock_service.answer_question.last_kwargs["engine_tags"] == engine_tags("glmp")
    assert mock_service.answer_question.last_kwargs["question_scope"] is None


def test_no_engine_param_passes_none_through_unchanged():
    mock_service = _no_rate_limit_and_mocked_rag()
    with patch('endpoints.rag.routes.check_rate_limit'), \
         patch('endpoints.rag.routes.get_rag_service', return_value=mock_service):
        response = client.get("/api/rag/answer", params={"question": "what is CRP?"})
    assert response.status_code == 200
    assert mock_service.answer_question.last_kwargs["engine_tags"] is None


def test_question_scope_alone_still_works_unchanged():
    mock_service = _no_rate_limit_and_mocked_rag()
    with patch('endpoints.rag.routes.check_rate_limit'), \
         patch('endpoints.rag.routes.get_rag_service', return_value=mock_service):
        response = client.get(
            "/api/rag/answer",
            params={"question": "what is CRP?", "question_scope": "glmp-q1"},
        )
    assert response.status_code == 200
    assert mock_service.answer_question.last_kwargs["question_scope"] == "glmp-q1"
    assert mock_service.answer_question.last_kwargs["engine_tags"] is None
