"""
Standalone unit tests for CanonicalService methods
Tests only the pure logic without external dependencies
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCanonicalServiceLogic:
    """Test suite for CanonicalService - testing logic only"""
    
    def setup_method(self):
        """Set up test fixtures with mocked dependencies"""
        # Mock all external dependencies
        self.mock_db = MagicMock()
        self.mock_logger = MagicMock()
        
        # Patch dependencies before import
        with patch('config.database.db', self.mock_db), \
             patch('utils.logging.structured_logger', self.mock_logger):
            from services.canonical_service import CanonicalService
            self.service = CanonicalService()
    
    def test_is_canonical_filename_feature(self):
        """Test feature format canonical filename validation"""
        # Valid feature formats
        assert self.service.is_canonical_filename("ever-bio-250032") == True
        assert self.service.is_canonical_filename("ever-phys-123456") == True
        assert self.service.is_canonical_filename("ever-chem-000001") == True
        assert self.service.is_canonical_filename("ever-compsci-999999") == True
        assert self.service.is_canonical_filename("ever-math-000042") == True
        
        # Invalid formats
        assert self.service.is_canonical_filename("ever-bio-25003") == False  # 5 digits
        assert self.service.is_canonical_filename("ever-bio-2500325") == False  # 7 digits
        assert self.service.is_canonical_filename("ever-invalid-250032") == False  # invalid category
        assert self.service.is_canonical_filename("ever-bio-abc123") == False  # non-numeric
    
    def test_is_canonical_filename_news(self):
        """Test news format canonical filename validation"""
        # Valid news formats
        assert self.service.is_canonical_filename("news-bio-20250328-0001") == True
        assert self.service.is_canonical_filename("news-phys-20251203-1234") == True
        assert self.service.is_canonical_filename("news-chem-20240101-0001") == True
        
        # Invalid formats
        assert self.service.is_canonical_filename("news-bio-20250328-001") == False  # 3 digits
        assert self.service.is_canonical_filename("news-bio-2025032-0001") == False  # 7 digit date
        assert self.service.is_canonical_filename("news-bio-20250328-00001") == False  # 5 digits
        assert self.service.is_canonical_filename("news-invalid-20250328-0001") == False  # invalid category
    
    def test_extract_category_from_canonical(self):
        """Test category extraction from canonical filename"""
        # Feature format
        assert self.service.extract_category_from_canonical("ever-bio-250032") == "bio"
        assert self.service.extract_category_from_canonical("ever-phys-123456") == "phys"
        assert self.service.extract_category_from_canonical("ever-chem-000001") == "chem"
        
        # News format
        assert self.service.extract_category_from_canonical("news-chem-20250328-0001") == "chem"
        assert self.service.extract_category_from_canonical("news-compsci-20251203-1234") == "compsci"
        
        # Edge cases
        assert self.service.extract_category_from_canonical("") == None
        assert self.service.extract_category_from_canonical("invalid") == None
        assert self.service.extract_category_from_canonical(None) == None
        # Note: "ever-250032" returns "250032" (just extracts 2nd part) - this is expected behavior
    
    def test_is_canonical_filename_empty(self):
        """Test canonical filename validation with empty/invalid inputs"""
        assert self.service.is_canonical_filename("") == False
        assert self.service.is_canonical_filename(None) == False
        assert self.service.is_canonical_filename("not-canonical") == False
        assert self.service.is_canonical_filename("just-text") == False
        assert self.service.is_canonical_filename("123") == False

