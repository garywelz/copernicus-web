# MCP Server Tests

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest mcp_server/tests/

# Run specific test file
pytest mcp_server/tests/test_papers_tools.py

# Run with coverage
pytest --cov=mcp_server mcp_server/tests/
```

## Test Structure

- `test_papers_tools.py` - Research paper tool tests
- `test_glmp_tools.py` - GLMP tool tests
- `test_server.py` - Server integration tests
- `conftest.py` - Pytest configuration and fixtures

## Test Coverage Goals

- Unit tests for all 15 tools
- Integration tests for server functionality
- Performance tests for query response times
- Error handling tests



