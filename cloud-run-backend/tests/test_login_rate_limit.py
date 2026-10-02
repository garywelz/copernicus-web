"""Integration tests for the login rate limit (security lockdown Step 2,
2026-10-01): POST /api/subscribers/login, 10 attempts/hour/client."""
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.subscriber.routes import router, LOGIN_RATE_LIMIT_PER_HOUR

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_login_rate_limit_is_ten_per_hour():
    assert LOGIN_RATE_LIMIT_PER_HOUR == 10


def test_login_blocked_with_429_once_rate_limit_raises():
    with patch('endpoints.subscriber.routes.check_rate_limit') as mock_limit:
        mock_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")
        response = client.post(
            "/api/subscribers/login",
            json={"email": "someone@example.com", "password": "whatever"},
        )
    assert response.status_code == 429


def test_login_rate_limit_checked_before_any_firestore_lookup():
    # The 429 must fire before get_subscriber_by_email is ever called --
    # otherwise a flood of login attempts still drives Firestore reads even
    # while "rate limited".
    with patch('endpoints.subscriber.routes.check_rate_limit') as mock_limit, \
         patch('endpoints.subscriber.routes.get_subscriber_by_email') as mock_lookup:
        mock_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")
        client.post(
            "/api/subscribers/login",
            json={"email": "someone@example.com", "password": "whatever"},
        )
    mock_lookup.assert_not_called()


def test_login_uses_last_forwarded_for_address_as_the_rate_limit_key():
    with patch('endpoints.subscriber.routes.check_rate_limit') as mock_limit, \
         patch('endpoints.subscriber.routes.get_subscriber_by_email', return_value=None):
        client.post(
            "/api/subscribers/login",
            json={"email": "someone@example.com", "password": "whatever"},
            headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.9"},
        )
    assert mock_limit.call_args is not None
    called_client_key = mock_limit.call_args[0][1]  # (db, client_key, route, ...)
    assert called_client_key == "203.0.113.9"  # last entry, not the spoofable first


def test_login_passes_through_normally_when_under_the_limit():
    # check_rate_limit returns None (no exception) when under the limit --
    # the route must proceed to its normal 404-subscriber-not-found path,
    # not swallow the call.
    with patch('endpoints.subscriber.routes.check_rate_limit', return_value=None), \
         patch('endpoints.subscriber.routes.get_subscriber_by_email', return_value=None):
        response = client.post(
            "/api/subscribers/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
    assert response.status_code == 404
