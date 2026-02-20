# MCP Server Monitoring Guide

## Logging

The server uses Python's standard logging module with the following configuration:

### Log Levels

- **INFO:** Normal operations, tool calls, successful queries
- **WARNING:** Non-critical issues, missing data
- **ERROR:** Errors, exceptions, failed operations
- **DEBUG:** Detailed debugging information (if enabled)

### Log Format

```
2025-12-24 10:30:45 - mcp_server.server - INFO - Tool called: query_research_papers with arguments: {'query': 'CRISPR', 'limit': 10}
2025-12-24 10:30:46 - mcp_server.tools.papers - INFO - Query returned 5 papers
```

### Enabling Debug Logging

Set environment variable:
```bash
export MCP_LOG_LEVEL=DEBUG
```

Or modify `server.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Performance Monitoring

### Key Metrics

1. **Query Response Time:**
   - Target: < 2 seconds for simple queries
   - Target: < 5 seconds for complex cross-component queries
   - Monitor: Average, min, max response times

2. **Tool Usage:**
   - Track which tools are used most frequently
   - Identify unused tools
   - Monitor error rates per tool

3. **Data Access Patterns:**
   - Most queried papers/processes/podcasts
   - Common search terms
   - Entity search patterns

### Performance Testing

Run performance tests:
```bash
python -m mcp_server.performance_test
```

## Error Monitoring

### Common Errors

1. **Firestore Connection Errors:**
   - Check: GCP credentials, network connectivity
   - Action: Verify service account permissions

2. **GCS Access Errors:**
   - Check: Bucket name, path, permissions
   - Action: Verify Storage Object Viewer role

3. **Tool Execution Errors:**
   - Check: Input validation, data availability
   - Action: Review error logs for specific issues

### Error Tracking

Monitor error rates:
- Errors per tool
- Error types and frequencies
- Recovery success rates

## Health Checks

### Server Health

Check if server is running:
```bash
# Test server startup
python -m mcp_server.server --test
```

### Component Health

Test individual components:
```python
# Test Firestore connection
from mcp_server.utils.firestore_client import get_firestore_client
client = get_firestore_client()
# Should not raise exception

# Test GCS connection
from mcp_server.utils.gcs_client import get_storage_client
client = get_storage_client()
# Should not raise exception
```

## Monitoring Tools

### Built-in Monitoring

The server logs all tool calls and errors. Review logs for:
- Performance issues
- Error patterns
- Usage statistics

### External Monitoring (Future)

Consider integrating:
- **Cloud Monitoring:** GCP Cloud Monitoring for metrics
- **Error Tracking:** Sentry or similar for error tracking
- **Analytics:** Custom analytics for tool usage

## Alerts

Set up alerts for:
- High error rates (> 10% of requests)
- Slow queries (> 5 seconds average)
- Connection failures
- Unusual usage patterns

## Optimization Opportunities

Monitor for:
- Frequently accessed data (candidate for caching)
- Slow queries (candidate for optimization)
- Large result sets (consider pagination)
- Repeated queries (candidate for caching)

## Reporting

Generate reports on:
- Tool usage statistics
- Performance metrics
- Error rates
- User patterns



