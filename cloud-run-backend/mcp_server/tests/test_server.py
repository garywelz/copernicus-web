"""
Integration tests for MCP Server
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from mcp_server.server import server, call_tool


@pytest.mark.asyncio
async def test_server_list_tools():
    """Test that server lists all tools"""
    tools = await server.list_tools()
    
    # Should have at least 15 tools (1 server info + 14 component tools)
    assert len(tools) >= 15
    
    # Check for key tools
    tool_names = [tool.name for tool in tools]
    assert "get_server_info" in tool_names
    assert "query_research_papers" in tool_names
    assert "list_glmp_processes" in tool_names
    assert "list_podcasts" in tool_names
    assert "find_related_content" in tool_names


@pytest.mark.asyncio
async def test_get_server_info():
    """Test server info tool"""
    from mcp.types import TextContent
    
    result = await call_tool("get_server_info", {})
    
    assert len(result) > 0
    assert isinstance(result[0], TextContent)
    assert "CopernicusAI" in result[0].text
    assert "15 tools" in result[0].text or "tools operational" in result[0].text



