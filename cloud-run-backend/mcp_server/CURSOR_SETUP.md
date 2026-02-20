# Cursor IDE MCP Server Setup

## Quick Setup Guide

### Step 1: Verify Server Works

Test the server locally:
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
python -m mcp_server.server
```

If it starts without errors, you're ready to configure Cursor.

### Step 2: Configure Cursor

1. **Open Cursor Settings:**
   - Press `Cmd/Ctrl + ,` to open settings
   - Search for "MCP" or "Model Context Protocol"

2. **Add MCP Server Configuration:**
   
   Create or edit the MCP configuration file. The location depends on your OS:
   
   **Linux/WSL:**
   ```bash
   ~/.config/cursor/mcp.json
   ```
   
   **macOS:**
   ```bash
   ~/Library/Application Support/Cursor/mcp.json
   ```
   
   **Windows:**
   ```bash
   %APPDATA%\Cursor\mcp.json
   ```

3. **Add Configuration:**
   
   ```json
   {
     "mcpServers": {
       "copernicusai": {
         "command": "python3",
         "args": [
           "-m",
           "mcp_server.server"
         ],
         "cwd": "/home/gdubs/copernicus-web-public/cloud-run-backend",
         "env": {
           "GCP_PROJECT_ID": "regal-scholar-453620-r7",
           "FIRESTORE_DATABASE": "copernicusai",
           "GCP_AUDIO_BUCKET": "regal-scholar-453620-r7-podcast-storage",
           "GLMP_BUCKET_PATH": "glmp-v2/processes"
         }
       }
     }
   }
   ```

4. **Restart Cursor:**
   - Close and reopen Cursor
   - The MCP server should connect automatically

### Step 3: Verify Connection

1. Open a chat in Cursor
2. Ask: "What tools are available from the CopernicusAI MCP server?"
3. The AI should list all 15 tools

### Step 4: Test a Tool

Try a query:
```
Use the query_research_papers tool to find papers about CRISPR
```

Or:
```
List all GLMP processes in the Central Dogma category
```

## Troubleshooting

### Server Won't Start
- Check Python path: `which python3`
- Verify MCP SDK: `pip list | grep mcp`
- Check GCP credentials: `gcloud auth application-default print-access-token`

### Tools Not Available
- Verify server is running (check Cursor logs)
- Check configuration file syntax (valid JSON)
- Ensure `cwd` path is correct

### Connection Errors
- Verify Firestore database name
- Check GCS bucket permissions
- Review Cursor MCP logs for errors

## Advanced Configuration

### Using Virtual Environment

If using a virtual environment:

```json
{
  "mcpServers": {
    "copernicusai": {
      "command": "/home/gdubs/copernicus-web-public/cloud-run-backend/venv/bin/python",
      "args": [
        "-m",
        "mcp_server.server"
      ],
      "cwd": "/home/gdubs/copernicus-web-public/cloud-run-backend"
    }
  }
}
```

### Custom Environment Variables

Add any additional environment variables to the `env` section:

```json
"env": {
  "GCP_PROJECT_ID": "regal-scholar-453620-r7",
  "FIRESTORE_DATABASE": "copernicusai",
  "GCP_AUDIO_BUCKET": "regal-scholar-453620-r7-podcast-storage",
  "MCP_CACHE_TTL": "600",
  "MCP_DEFAULT_LIMIT": "20"
}
```

## Usage Tips

1. **Tool Discovery:** Ask "What MCP tools are available?" to see all tools
2. **Combined Queries:** Use cross-component tools to find relationships
3. **Entity Search:** Use entity-based tools for precise biological/chemical queries
4. **Error Handling:** If a tool fails, check the error message for guidance

## Next Steps

- Test all 15 tools
- Explore cross-component relationships
- Use in your research workflow
- Provide feedback for improvements



