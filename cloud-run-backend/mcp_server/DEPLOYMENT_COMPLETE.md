# MCP Server Deployment - COMPLETE ✅

**Date:** December 24, 2025  
**Status:** ✅ Deployed and Ready for Testing

---

## Deployment Summary

### ✅ Prerequisites Verified

1. **Python Environment**
   - Python 3.12.3 ✅
   - Virtual environment available ✅

2. **Dependencies**
   - MCP SDK 1.25.0 ✅
   - Google Cloud libraries ✅
   - google-cloud-firestore ✅

3. **Configuration**
   - GCP Project: `regal-scholar-453620-r7` ✅
   - Firestore Database: `copernicusai` ✅
   - GCS Bucket: `regal-scholar-453620-r7-podcast-storage` ✅

4. **GCP Credentials**
   - Firestore access ✅
   - GCS access ✅

5. **Cursor Configuration**
   - Config file created ✅
   - Installed to `~/.config/cursor/mcp.json` ✅

---

## Next Steps

### 1. Restart Cursor
**IMPORTANT:** You must fully restart Cursor for the MCP server to connect.

1. Close Cursor completely (not just the window)
2. Reopen Cursor
3. The MCP server should connect automatically on startup

### 2. Verify Connection

Open a chat in Cursor and ask:
```
What MCP tools are available from CopernicusAI?
```

You should see a list of all 15 tools.

### 3. Test a Tool

Try one of these:

**Get GLMP Categories:**
```
Use the get_glmp_categories tool to show me all GLMP categories with their process counts
```

**List GLMP Processes:**
```
Use the list_glmp_processes tool to show me 5 processes from the Central Dogma category
```

**Search Papers:**
```
Use the query_research_papers tool to find papers about CRISPR, limit to 5 results
```

---

## Troubleshooting

### If Tools Don't Appear

1. **Check Config File:**
   ```bash
   cat ~/.config/cursor/mcp.json
   ```
   Should show the CopernicusAI server configuration.

2. **Check Python Path:**
   The config uses `python3`. If you need a different path:
   ```bash
   which python3
   ```
   Update the `command` field in `~/.config/cursor/mcp.json` if needed.

3. **Check Working Directory:**
   Verify the `cwd` path is correct:
   ```bash
   ls /home/gdubs/copernicus-web-public/cloud-run-backend/mcp_server/server.py
   ```

4. **Check Logs:**
   Look for MCP errors in Cursor's developer console (Help → Toggle Developer Tools).

### If Server Doesn't Connect

1. **Test Server Manually:**
   ```bash
   cd /home/gdubs/copernicus-web-public/cloud-run-backend
   source venv/bin/activate  # or backend_venv/bin/activate
   python3 -m mcp_server.server
   ```
   Should start without errors (will wait for stdin - press Ctrl+C to exit).

2. **Check Dependencies:**
   ```bash
   pip list | grep -E "(mcp|google-cloud-firestore)"
   ```

3. **Verify Environment Variables:**
   The config sets them automatically, but you can test:
   ```bash
   python3 -c "import os; print(os.getenv('GCP_PROJECT_ID'))"
   ```

---

## Ready for Real-World Testing!

Once Cursor is restarted and tools are available, you can:

1. **Start Paper 2 (GLMP):**
   - Use `get_glmp_categories` to get overview
   - Use `list_glmp_processes` to get examples
   - Use `get_glmp_process` to get detailed data
   - Use `search_papers_by_entity` to find related papers

2. **Test Cross-Component Tools:**
   - Use `find_related_content` to discover connections
   - Use `search_across_components` for unified search

3. **Measure Performance:**
   - Note response times
   - Document any issues
   - Suggest improvements

---

## Status

**✅ DEPLOYMENT COMPLETE**

- Server code: ✅ Ready
- Dependencies: ✅ Installed
- Configuration: ✅ Complete
- Cursor config: ✅ Installed

**Next:** Restart Cursor and begin testing!

---

## Quick Reference

**Config File Location:** `~/.config/cursor/mcp.json`  
**Server Location:** `/home/gdubs/copernicus-web-public/cloud-run-backend/mcp_server/`  
**Documentation:** See `USER_GUIDE.md` for tool usage

**Test Command:**
```
What MCP tools are available from CopernicusAI?
```



