# MCP Server Deployment Status

**Date:** December 24, 2025  
**Status:** ✅ Prerequisites Verified, Ready for Cursor Configuration

---

## Prerequisites Check ✅

### 1. Python Environment
- ✅ Python 3.x installed
- ✅ Virtual environment available

### 2. Dependencies
- ✅ MCP SDK installed
- ✅ Google Cloud libraries installed
- ✅ All required packages available

### 3. Configuration
- ✅ Config file loads successfully
- ✅ GCP Project ID: `regal-scholar-453620-r7`
- ✅ Firestore Database: `copernicusai`
- ✅ GCS Bucket: `regal-scholar-453620-r7-podcast-storage`

### 4. GCP Credentials
- ✅ Firestore client initializes
- ✅ GCS client initializes
- ✅ Credentials configured correctly

### 5. Server Startup
- ✅ Server module imports successfully
- ✅ No import errors
- ✅ Ready to run

---

## Cursor Configuration

### Config File Created
**Location:** `cloud-run-backend/mcp_server/cursor_mcp_config.json`

### Installation Steps

#### For Linux/WSL:
```bash
# Create Cursor config directory if it doesn't exist
mkdir -p ~/.config/cursor

# Copy config file
cp /home/gdubs/copernicus-web-public/cloud-run-backend/mcp_server/cursor_mcp_config.json ~/.config/cursor/mcp.json

# Verify
cat ~/.config/cursor/mcp.json
```

#### For macOS:
```bash
# Create directory if needed
mkdir -p ~/Library/Application\ Support/Cursor

# Copy config file
cp /home/gdubs/copernicus-web-public/cloud-run-backend/mcp_server/cursor_mcp_config.json ~/Library/Application\ Support/Cursor/mcp.json
```

#### For Windows:
```powershell
# Create directory if needed
New-Item -ItemType Directory -Force -Path "$env:APPDATA\Cursor"

# Copy config file
Copy-Item "C:\path\to\cursor_mcp_config.json" "$env:APPDATA\Cursor\mcp.json"
```

---

## Verification Steps

### 1. Restart Cursor
- Close Cursor completely
- Reopen Cursor
- The MCP server should connect automatically

### 2. Test Connection
Open a chat in Cursor and ask:
```
What MCP tools are available from CopernicusAI?
```

You should see a list of all 15 tools.

### 3. Test a Tool
Try:
```
Use the get_glmp_categories tool to show me all GLMP categories
```

Or:
```
Use the list_glmp_processes tool to show me 5 processes from the Central Dogma category
```

---

## Troubleshooting

### If Server Doesn't Connect

1. **Check Python Path:**
   ```bash
   which python3
   ```
   Update `command` in config if needed.

2. **Check Working Directory:**
   Verify `cwd` path is correct in config.

3. **Check Logs:**
   Look for MCP errors in Cursor's developer console or logs.

4. **Test Server Manually:**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   python3 -m mcp_server.server
   ```
   Should start without errors (will wait for stdin).

### If Tools Don't Appear

1. **Verify Config File:**
   - Check JSON syntax is valid
   - Ensure file is named `mcp.json` (not `cursor_mcp_config.json`)

2. **Check Environment Variables:**
   - Verify all env vars are set correctly
   - Test with: `echo $GCP_PROJECT_ID`

3. **Restart Cursor:**
   - Fully quit and restart
   - MCP servers load on startup

---

## Next Steps

Once Cursor is configured:

1. ✅ Test all 15 tools
2. ✅ Begin Paper 2 (GLMP) writing using MCP tools
3. ✅ Document any issues
4. ✅ Measure performance

---

## Status

**Current:** Prerequisites verified, config file ready  
**Next:** Install config in Cursor and test connection



