"""
Pytest configuration and shared fixtures
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator

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

