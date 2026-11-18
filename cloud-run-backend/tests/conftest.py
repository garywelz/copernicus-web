"""
Pytest configuration and shared fixtures
"""
import os

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator

# ---- NO TEST MAY REACH THE NETWORK (BULLETIN 050) ------------------------------------------------------------------------------------------------------
# Installed first, before any test module (and so any service module) is imported. See tests/no_network.py for what is refused and why. Every Python
# subprocess a test starts gets the same guard. A test marked `live` is skipped unless pytest is run with --run-live, and only then may it use the network.
# tests/test_no_real_network.py fails if this guard is removed.
from tests import no_network

pytest_plugins = ["pytester"]          # tests/test_no_real_network.py runs small suites of its own to show the guard failing a test
no_network.install()
no_network.install_for_subprocesses(os.environ, os.path.join(os.path.dirname(os.path.abspath(__file__)), "no_network_site"))

# ---- NO REAL SECRET MANAGER CLIENT ---------------------------------------------------------------------------------------------------------------------
# The suite used to read the real ElevenLabs and admin API keys from Secret Manager with the machine's own sign-in. The client class is replaced by a stand-in
# that refuses to be created; every caller (elevenlabs_voice_service.py, utils/auth.py, the research and generation services) already catches the failure and
# falls back to its environment variable, which is what happens on a machine with no credentials.
from google.cloud import secretmanager as _secretmanager

SECRET_MANAGER_ATTEMPTS = []


class RealSecretManagerRefused(RuntimeError):
    """Raised instead of creating a Secret Manager client inside the test suite."""


class _NoRealSecretManager:
    def __init__(self, *args, **kwargs):
        SECRET_MANAGER_ATTEMPTS.append(dict(kwargs))
        raise RealSecretManagerRefused("the test suite must never read a real secret; set the environment variable or patch the caller")


_secretmanager.SecretManagerServiceClient = _NoRealSecretManager
_secretmanager.SecretManagerServiceAsyncClient = _NoRealSecretManager


def pytest_addoption(parser):
    parser.addoption("--run-live", action="store_true", default=False,
                     help="also run the tests marked `live`, which read real services with the machine's own credentials (never run by default)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip = pytest.mark.skip(reason="live: reads real services; run only with --run-live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _no_real_network(request):
    """Fails any test during which the guard refused a DNS lookup, a connection, a Google sign-in or a gRPC channel. A `live` test (run only with --run-live)
    may use the network."""
    if "live" in request.keywords:
        with no_network.network_allowed():
            yield
        return
    start = len(no_network.ATTEMPTS)
    yield
    refused = [a for a in no_network.ATTEMPTS[start:] if not a["expected"]]
    if refused:
        pytest.fail("this test tried to reach the network, which the suite refuses: "
                    + "; ".join(f"{a['kind']} {a['target']}" for a in refused[:5]) + " (use a fake, or mark the test `live`)", pytrace=False)


def pytest_terminal_summary(terminalreporter):
    outside = [a for a in no_network.ATTEMPTS if not a["expected"]]
    if outside:
        terminalreporter.write_line(f"no_network: {len(outside)} network attempt(s) refused in this run (each in a failed test, or at import): "
                                    + "; ".join(sorted({f"{a['kind']} {a['target']}" for a in outside})[:10]))


# ---- NO REAL FIRESTORE CLIENT IN THE TEST SUITE (onboarding PR 4b-1) ----------------------------------------------------------------------------------
# config/database.py creates a Firestore client when it is first imported, and on a machine that is signed in to Google Cloud that client is REAL: it points at
# the production database. No test ever read or wrote through it, but nothing stopped one from doing so. From here on the client classes are replaced, before any
# test module is imported, by a stand-in that refuses to be created. config/database.py catches the refusal and leaves `db = None`, which is what it does on a
# machine with no credentials; every test that needs a database already supplies a fake one. tests/test_no_real_firestore.py fails if this guard is removed.
import google.cloud.firestore as _firestore
import google.cloud.firestore_v1 as _firestore_v1

REAL_FIRESTORE_CLASSES = (_firestore_v1.Client, _firestore_v1.AsyncClient)
FIRESTORE_ATTEMPTS = []          # one entry per attempt to create a client during the run: the keyword arguments it was called with


class RealFirestoreRefused(RuntimeError):
    """Raised instead of creating a Firestore client inside the test suite."""


class _NoRealFirestore:
    def __init__(self, *args, **kwargs):
        FIRESTORE_ATTEMPTS.append(dict(kwargs))
        raise RealFirestoreRefused("the test suite must never create a real Firestore client; use a fake (tests/fakes_pr2.py)")


for _module in (_firestore, _firestore_v1):
    _module.Client = _NoRealFirestore
    _module.AsyncClient = _NoRealFirestore


@pytest.fixture
def mock_db():
    """Mock Firestore database client"""
    db = MagicMock()
    
    # Mock collections
    db.collection = MagicMock(return_value=MagicMock())
    
    return db


@pytest.fixture
def mock_firestore_client(mock_db):
    """Mock Firestore client with database"""
    with patch('config.database.db', mock_db):
        yield mock_db


@pytest.fixture
def mock_gcs_bucket():
    """Mock GCS bucket"""
    bucket = MagicMock()
    blob = MagicMock()
    blob.public_url = "https://storage.googleapis.com/test-bucket/test-file.mp3"
    blob.upload_from_string = MagicMock()
    blob.make_public = MagicMock()
    bucket.blob = MagicMock(return_value=blob)
    return bucket


@pytest.fixture
def mock_gcs_client(mock_gcs_bucket):
    """Mock GCS client"""
    with patch('google.cloud.storage.Client') as mock_client:
        mock_instance = MagicMock()
        mock_instance.bucket = MagicMock(return_value=mock_gcs_bucket)
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_structured_logger():
    """Mock structured logger"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def sample_podcast_job():
    """Sample podcast job data"""
    return {
        'job_id': 'test-job-123',
        'status': 'completed',
        'created_at': '2025-12-03T12:00:00',
        'topic': 'Test Topic',
        'category': 'Physics',
        'result': {
            'audio_url': 'https://storage.googleapis.com/test/ever-phys-250001.mp3',
            'thumbnail_url': 'https://storage.googleapis.com/test/ever-phys-250001-thumb.jpg',
            'description_url': 'https://storage.googleapis.com/test/ever-phys-250001.md'
        }
    }


@pytest.fixture
def sample_episode():
    """Sample episode data"""
    return {
        'episode_id': 'test-episode-123',
        'title': 'Test Episode',
        'canonical_filename': 'ever-phys-250001',
        'category': 'phys',
        'audio_url': 'https://storage.googleapis.com/test/ever-phys-250001.mp3',
        'subscriber_id': 'test-subscriber@example.com',
        'created_at': '2025-12-03T12:00:00',
        'status': 'published'
    }

