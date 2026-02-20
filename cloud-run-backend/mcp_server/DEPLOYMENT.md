# MCP Server Deployment Guide

## Overview

This guide covers deploying the CopernicusAI Knowledge Engine MCP server for use with Cursor, Claude Desktop, and other MCP-compatible clients.

## Deployment Options

### Option 1: Local Development (Recommended for Testing)

**Best for:** Development, testing, local use

1. **Install Dependencies:**
   ```bash
   cd cloud-run-backend
   pip install -r mcp_server/requirements.txt
   ```

2. **Set Environment Variables:**
   ```bash
   export GCP_PROJECT_ID="regal-scholar-453620-r7"
   export FIRESTORE_DATABASE="copernicusai"
   export GCP_AUDIO_BUCKET="regal-scholar-453620-r7-podcast-storage"
   ```

3. **Test Server:**
   ```bash
   python -m mcp_server.server
   ```

### Option 2: Cursor IDE Integration

**Configuration File:** `~/.cursor/mcp.json` (or Cursor settings)

```json
{
  "mcpServers": {
    "copernicusai": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server.server"
      ],
      "cwd": "/home/gdubs/copernicus-web-public/cloud-run-backend",
      "env": {
        "GCP_PROJECT_ID": "regal-scholar-453620-r7",
        "FIRESTORE_DATABASE": "copernicusai",
        "GCP_AUDIO_BUCKET": "regal-scholar-453620-r7-podcast-storage"
      }
    }
  }
}
```

### Option 3: Claude Desktop Integration

**Configuration File:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "copernicusai": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server.server"
      ],
      "cwd": "/home/gdubs/copernicus-web-public/cloud-run-backend",
      "env": {
        "GCP_PROJECT_ID": "regal-scholar-453620-r7",
        "FIRESTORE_DATABASE": "copernicusai",
        "GCP_AUDIO_BUCKET": "regal-scholar-453620-r7-podcast-storage"
      }
    }
  }
}
```

### Option 4: Standalone Service (Future)

For production deployment as a standalone service, the server can be wrapped in a systemd service or Docker container.

## Authentication

The server uses Google Cloud service account credentials. Ensure:

1. **Service Account Key:** Available via:
   - Environment variable: `GOOGLE_APPLICATION_CREDENTIALS` pointing to key file
   - Default credentials: `gcloud auth application-default login`
   - Secret Manager: (if using Cloud Run deployment)

2. **Required Permissions:**
   - Firestore: Read access to `copernicusai` database
   - Cloud Storage: Read access to `regal-scholar-453620-r7-podcast-storage` bucket

## Monitoring

### Logging

The server uses Python's logging module. Logs include:
- Tool calls and arguments
- Query execution times
- Errors and exceptions

**Log Levels:**
- `INFO`: Normal operations, tool calls
- `ERROR`: Errors and exceptions
- `DEBUG`: Detailed debugging (if enabled)

### Performance Metrics

Monitor:
- Query response times
- Concurrent request handling
- Error rates
- Tool usage patterns

## Troubleshooting

### Common Issues

1. **Import Errors:**
   - Ensure MCP SDK is installed: `pip install mcp`
   - Check Python path includes `cloud-run-backend` directory

2. **Firestore Connection Errors:**
   - Verify GCP credentials are set
   - Check Firestore database name matches configuration

3. **GCS Access Errors:**
   - Verify bucket name and path are correct
   - Check service account has Storage Object Viewer permission

4. **Tool Not Found:**
   - Verify tool is registered in `server.py`
   - Check tool name matches exactly (case-sensitive)

## Security Considerations

- **Credentials:** Never commit service account keys to version control
- **Access Control:** Server provides read-only access to data
- **Input Validation:** All tool inputs are validated
- **Error Messages:** Errors don't expose sensitive information

## Performance Optimization

- **Caching:** Consider implementing caching for frequently accessed data
- **Connection Pooling:** Firestore and GCS clients use connection pooling
- **Query Limits:** Default limit is 10, max is 100 to prevent large responses

## Next Steps

1. Test server with Cursor/Claude Desktop
2. Monitor performance and optimize as needed
3. Add caching if query times are slow
4. Consider HTTP MCP server option for remote access



