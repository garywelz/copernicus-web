"""
Unit tests for CanonicalService
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# Mock dependencies at module level before imports
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Auto-use fixture to mock external dependencies"""
    with patch('config.database.db', MagicMock()), \
         patch('utils.logging.structured_logger', MagicMock()):
        yield


class TestCanonicalService:
    """Test suite for CanonicalService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Import after mocking
        with patch('config.database.db', MagicMock()), \
             patch('utils.logging.structured_logger', MagicMock()):
            from services.canonical_service import CanonicalService
            self.service = CanonicalService()
    
    def test_is_canonical_filename_feature(self):
        """Test feature format canonical filename validation"""
        # Valid feature formats
        assert self.service.is_canonical_filename("ever-bio-250032") == True
        assert self.service.is_canonical_filename("ever-phys-123456") == True
        assert self.service.is_canonical_filename("ever-chem-000001") == True
        
        # Invalid formats
        assert self.service.is_canonical_filename("ever-bio-25003") == False  # 5 digits
        assert self.service.is_canonical_filename("ever-bio-2500325") == False  # 7 digits
        assert self.service.is_canonical_filename("ever-invalid-250032") == False  # invalid category
    
    def test_is_canonical_filename_news(self):
        """Test news format canonical filename validation"""
        # Valid news formats
        assert self.service.is_canonical_filename("news-bio-20250328-0001") == True
        assert self.service.is_canonical_filename("news-phys-20251203-1234") == True
        
        # Invalid formats
        assert self.service.is_canonical_filename("news-bio-20250328-001") == False  # 3 digits
        assert self.service.is_canonical_filename("news-bio-2025032-0001") == False  # 7 digit date
    
    def test_extract_category_from_canonical(self):
        """Test category extraction from canonical filename"""
        assert self.service.extract_category_from_canonical("ever-bio-250032") == "bio"
        assert self.service.extract_category_from_canonical("ever-phys-123456") == "phys"
        assert self.service.extract_category_from_canonical("news-chem-20250328-0001") == "chem"
        
        # Edge cases
        assert self.service.extract_category_from_canonical("") == None
        assert self.service.extract_category_from_canonical("invalid") == None
        assert self.service.extract_category_from_canonical(None) == None
    
    def test_is_canonical_filename_empty(self):
        """Test canonical filename validation with empty/invalid inputs"""
        assert self.service.is_canonical_filename("") == False
        assert self.service.is_canonical_filename(None) == False
        assert self.service.is_canonical_filename("not-canonical") == False
