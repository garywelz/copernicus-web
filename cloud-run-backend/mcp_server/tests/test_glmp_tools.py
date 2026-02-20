"""
Unit tests for GLMP Tools
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from mcp_server.tools.glmp import (
    list_glmp_processes,
    get_glmp_process,
    search_glmp_by_entity,
    get_glmp_categories
)


@pytest.mark.asyncio
async def test_list_glmp_processes():
    """Test listing GLMP processes"""
    with patch('mcp_server.tools.glmp.search_glmp_files') as mock_search:
        mock_search.return_value = [
            {
                "id": "test-process-1",
                "title": "Test Process",
                "category": "Metabolism",
                "description": "A test process"
            }
        ]
        
        result = await list_glmp_processes(category="Metabolism", limit=10)
        result_data = json.loads(result)
        
        assert result_data["count"] == 1
        assert len(result_data["processes"]) == 1


@pytest.mark.asyncio
async def test_get_glmp_process():
    """Test getting GLMP process by ID"""
    with patch('mcp_server.tools.glmp.list_glmp_files') as mock_list:
        mock_list.return_value = ["glmp-v2/processes/test-process-1.json"]
        
        with patch('mcp_server.tools.glmp.get_glmp_file') as mock_get:
            mock_get.return_value = {
                "id": "test-process-1",
                "title": "Test Process",
                "mermaid": "flowchart TD\n    A[Start] --> B[End]"
            }
            
            result = await get_glmp_process(process_id="test-process-1")
            result_data = json.loads(result)
            
            assert result_data["process"] is not None
            assert result_data["process"]["title"] == "Test Process"



