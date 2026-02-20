# MCP Server Deployment & Real-World Testing Plan

## Current Status

**MCP Server:** ✅ Code Complete, ⚪ Not Yet Deployed  
**Next Step:** Deploy and test with real-world task (paper writing)

---

## Phase 1: Deploy MCP Server (30 minutes)

### Step 1.1: Verify Prerequisites
- [ ] Check Python environment and dependencies
- [ ] Verify GCP credentials are configured
- [ ] Test server startup locally
- [ ] Verify Firestore and GCS access

### Step 1.2: Configure Cursor IDE
- [ ] Create MCP configuration file (`~/.config/cursor/mcp.json` or equivalent)
- [ ] Add CopernicusAI MCP server configuration
- [ ] Set environment variables
- [ ] Restart Cursor

### Step 1.3: Verify Connection
- [ ] Test server connection in Cursor
- [ ] Verify all 15 tools are available
- [ ] Test a simple tool call (e.g., `get_server_info`)

**Checkpoint:** Server operational and accessible in Cursor

---

## Phase 2: Real-World Testing - Paper Writing Task (2-3 hours)

### Task: Write Paper 2 or Paper 3 from Publication Plan

**Option A: Paper 2 - "GLMP: Genome Logic Modeling for Biochemical Process Visualization"**
- **Why:** Directly uses GLMP tools
- **MCP Tools Needed:**
  - `list_glmp_processes` - Get process examples
  - `get_glmp_process` - Get detailed process data
  - `get_glmp_categories` - Organize by category
  - `search_glmp_by_entity` - Find processes by gene/protein
  - `get_paper_visualizations` - Link to related papers

**Option B: Paper 3 - "AI-Generated Podcasts for Scientific Research"**
- **Why:** Uses podcast tools extensively
- **MCP Tools Needed:**
  - `list_podcasts` - Get podcast examples
  - `get_podcast_details` - Get full metadata
  - `get_podcast_source_papers` - Link podcasts to papers
  - `search_podcasts_by_topic` - Find relevant podcasts
  - `find_related_content` - Cross-component linking

**Option C: Paper 4 - "Research Metadata Database"**
- **Why:** Uses research paper tools
- **MCP Tools Needed:**
  - `query_research_papers` - Search papers
  - `get_paper_by_id` - Get paper details
  - `get_paper_citations` - Citation networks
  - `search_papers_by_entity` - Entity-based search
  - `search_across_components` - Unified search

### Recommended: **Paper 2 (GLMP)** - Best for testing multiple tool types

---

## Phase 3: Paper Writing Workflow with MCP Tools

### Step 3.1: Research Phase (Using MCP Tools)

**Task:** Gather material for GLMP paper using MCP tools

1. **Get GLMP Overview:**
   ```
   Use: get_glmp_categories()
   Purpose: Understand scope and organization
   ```

2. **Collect Process Examples:**
   ```
   Use: list_glmp_processes(category="Central Dogma", limit=10)
   Use: list_glmp_processes(category="Metabolism", limit=10)
   Purpose: Get representative examples for paper
   ```

3. **Get Detailed Process Data:**
   ```
   Use: get_glmp_process(process_name="DNA replication")
   Use: get_glmp_process(process_name="glycolysis")
   Purpose: Extract Mermaid diagrams and metadata
   ```

4. **Find Related Research:**
   ```
   Use: search_papers_by_entity(entity="p53")
   Use: get_paper_visualizations(paper_id="...")
   Purpose: Find papers that could be cited
   ```

5. **Cross-Component Linking:**
   ```
   Use: find_related_content(process_id="...")
   Use: search_across_components(query="DNA replication")
   Purpose: Discover connections between components
   ```

### Step 3.2: Writing Phase (AI-Assisted)

**Task:** Write paper sections using gathered data

1. **Introduction:**
   - Use GLMP category data
   - Reference process counts
   - Cite related papers found via MCP

2. **Methodology:**
   - Use process examples from MCP queries
   - Include Mermaid diagram examples
   - Reference Programming Framework

3. **Results:**
   - Use actual GLMP process data
   - Include statistics from `get_glmp_categories`
   - Show entity search examples

4. **Discussion:**
   - Use cross-component relationships
   - Reference related podcasts/papers
   - Discuss integration opportunities

### Step 3.3: Validation Phase

**Task:** Verify paper content using MCP tools

1. **Fact Check:**
   - Verify process names via `list_glmp_processes`
   - Confirm entity names via `search_glmp_by_entity`
   - Validate paper citations via `get_paper_by_id`

2. **Completeness Check:**
   - Ensure all mentioned processes exist
   - Verify category counts are accurate
   - Confirm all citations are valid

---

## Phase 4: Testing & Refinement (1 hour)

### Step 4.1: Tool Performance Testing

- [ ] Measure response times for each tool used
- [ ] Identify slow queries (> 2 seconds)
- [ ] Test error handling (invalid inputs)
- [ ] Verify result accuracy

### Step 4.2: Workflow Optimization

- [ ] Document successful tool combinations
- [ ] Identify missing functionality
- [ ] Note any usability issues
- [ ] Suggest improvements

### Step 4.3: Documentation Updates

- [ ] Update USER_GUIDE.md with real examples
- [ ] Add paper writing workflow to documentation
- [ ] Document any discovered edge cases
- [ ] Create best practices guide

---

## Success Criteria

### Deployment Success:
- ✅ Server connects in Cursor
- ✅ All 15 tools accessible
- ✅ No connection errors

### Testing Success:
- ✅ Paper written using MCP tools
- ✅ All cited data verified via tools
- ✅ Cross-component linking demonstrated
- ✅ Performance acceptable (< 5s per query)

### Refinement Success:
- ✅ Performance issues identified and documented
- ✅ Missing features documented
- ✅ Workflow improvements suggested

---

## Timeline

- **Phase 1 (Deployment):** 30 minutes
- **Phase 2 (Paper Writing):** 2-3 hours
- **Phase 3 (Workflow):** Integrated into Phase 2
- **Phase 4 (Testing):** 1 hour

**Total:** ~4 hours for complete deployment and real-world testing

---

## Next Steps (After Testing)

1. **Performance Optimization:**
   - Add caching if queries are slow
   - Optimize Firestore queries
   - Batch operations where possible

2. **Feature Enhancements:**
   - Add missing functionality identified during testing
   - Improve error messages
   - Add result formatting options

3. **Documentation:**
   - Create paper writing workflow guide
   - Add more real-world examples
   - Document best practices

4. **Integration:**
   - Test with Claude Desktop
   - Consider HTTP MCP server for remote access
   - Explore other MCP clients

---

## Quick Start Commands

### Test Server Locally:
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
python -m mcp_server.server
```

### Run Performance Tests:
```bash
python -m mcp_server.performance_test
```

### Check Tool Availability in Cursor:
Ask: "What MCP tools are available from CopernicusAI?"

---

## Notes

- Start with Paper 2 (GLMP) for best tool coverage
- Document any issues encountered
- Note tool combinations that work well
- Track response times for optimization
- Save successful queries for documentation

---

**Ready to begin?** Start with Phase 1, Step 1.1: Verify Prerequisites


