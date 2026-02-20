"""
Unit tests for Research Paper Tools
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from mcp_server.tools.papers import (
    query_research_papers,
    get_paper_by_id,
    get_paper_citations,
    search_papers_by_entity
)


@pytest.mark.asyncio
async def test_query_research_papers_basic():
    """Test basic paper query functionality"""
    with patch('mcp_server.tools.papers.query_collection') as mock_query:
        mock_query.return_value = [
            {
                "id": "test-paper-1",
                "paper_id": "test-paper-1",
                "title": "Test Paper",
                "abstract": "This is a test abstract",
                "discipline": "biology",
                "authors": ["Author 1", "Author 2"]
            }
        ]
        
        result = await query_research_papers(query="test", limit=10)
        result_data = json.loads(result)
        
        assert result_data["count"] == 1
        assert len(result_data["papers"]) == 1
        assert result_data["papers"][0]["title"] == "Test Paper"


@pytest.mark.asyncio
async def test_get_paper_by_id():
    """Test getting paper by ID"""
    with patch('mcp_server.tools.papers.get_document') as mock_get:
        mock_get.return_value = {
            "id": "test-paper-1",
            "paper_id": "test-paper-1",
            "title": "Test Paper",
            "doi": "10.1234/test"
        }
        
        result = await get_paper_by_id(paper_id="test-paper-1")
        result_data = json.loads(result)
        
        assert result_data["paper"] is not None
        assert result_data["paper"]["title"] == "Test Paper"


@pytest.mark.asyncio
async def test_search_papers_by_entity():
    """Test searching papers by entity"""
    with patch('mcp_server.tools.papers.query_collection') as mock_query:
        mock_query.return_value = [
            {
                "id": "test-paper-1",
                "paper_id": "test-paper-1",
                "title": "Test Paper",
                "preprocessing": {
                    "entities_extracted": {
                        "genes": ["p53", "BRCA1"]
                    }
                }
            }
        ]
        
        result = await search_papers_by_entity(entity="p53", limit=10)
        result_data = json.loads(result)
        
        assert result_data["count"] >= 0
        assert "papers" in result_data



