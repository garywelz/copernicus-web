"""
Pytest configuration and shared fixtures
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator


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

