"""
Pytest configuration for MCP server tests
"""

import pytest
import os

# Set test environment variables
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("FIRESTORE_DATABASE", "test-database")
os.environ.setdefault("GCP_AUDIO_BUCKET", "test-bucket")

@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client for testing"""
    from unittest.mock import Mock
    return Mock()

@pytest.fixture
def mock_gcs_client():
    """Mock GCS client for testing"""
    from unittest.mock import Mock
    return Mock()



