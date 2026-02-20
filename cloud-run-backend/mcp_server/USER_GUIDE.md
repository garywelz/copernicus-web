# MCP Server User Guide
## CopernicusAI Knowledge Engine

## Introduction

The CopernicusAI Knowledge Engine MCP server provides AI assistants (like Cursor and Claude Desktop) with direct access to all knowledge engine components. This guide explains how to use the 15 available tools.

## Setup

### Prerequisites
- Python 3.8+
- MCP SDK installed (`pip install mcp`)
- Google Cloud credentials configured
- Access to Firestore and Cloud Storage

### Installation
```bash
cd cloud-run-backend
pip install -r mcp_server/requirements.txt
```

## Available Tools

### Research Paper Tools

#### 1. `query_research_papers`
Search for research papers by query, discipline, or keywords.

**Example:**
```
Tool: query_research_papers
Arguments: {
  "query": "CRISPR",
  "discipline": "biology",
  "limit": 10
}
```

**Returns:** List of papers matching the query

#### 2. `get_paper_by_id`
Get full paper metadata by paper ID or DOI.

**Example:**
```
Tool: get_paper_by_id
Arguments: {
  "doi": "10.1038/nature12345"
}
```

**Returns:** Complete paper data including preprocessing

#### 3. `get_paper_citations`
Find papers that cite a specified paper.

**Example:**
```
Tool: get_paper_citations
Arguments: {
  "paper_id": "abc123"
}
```

**Returns:** List of citing papers

#### 4. `search_papers_by_entity`
Search for papers mentioning a specific entity (gene, protein, chemical).

**Example:**
```
Tool: search_papers_by_entity
Arguments: {
  "entity": "p53",
  "entity_type": "gene",
  "limit": 10
}
```

**Returns:** Papers containing the entity

---

### GLMP Tools

#### 5. `list_glmp_processes`
List biological processes, optionally filtered by category.

**Example:**
```
Tool: list_glmp_processes
Arguments: {
  "category": "Central Dogma",
  "limit": 20
}
```

**Returns:** List of processes with metadata

#### 6. `get_glmp_process`
Get full process details including Mermaid diagram.

**Example:**
```
Tool: get_glmp_process
Arguments: {
  "process_name": "beta-galactosidase regulation"
}
```

**Returns:** Complete process data with Mermaid code

#### 7. `search_glmp_by_entity`
Search for processes involving a specific entity.

**Example:**
```
Tool: search_glmp_by_entity
Arguments: {
  "entity": "ATP",
  "limit": 10
}
```

**Returns:** Processes containing the entity

#### 8. `get_glmp_categories`
Get all GLMP categories with process counts.

**Example:**
```
Tool: get_glmp_categories
Arguments: {}
```

**Returns:** Categories and counts

---

### Podcast Tools

#### 9. `list_podcasts`
List podcasts, optionally filtered by discipline or subscriber.

**Example:**
```
Tool: list_podcasts
Arguments: {
  "discipline": "biology",
  "limit": 10
}
```

**Returns:** List of podcasts

#### 10. `get_podcast_details`
Get full podcast metadata including source papers and URLs.

**Example:**
```
Tool: get_podcast_details
Arguments: {
  "podcast_id": "canonical-filename-123"
}
```

**Returns:** Complete podcast data

#### 11. `get_podcast_source_papers`
Get source papers used in a podcast.

**Example:**
```
Tool: get_podcast_source_papers
Arguments: {
  "podcast_id": "canonical-filename-123"
}
```

**Returns:** List of source papers

#### 12. `search_podcasts_by_topic`
Search for podcasts matching a topic.

**Example:**
```
Tool: search_podcasts_by_topic
Arguments: {
  "topic": "quantum computing",
  "limit": 10
}
```

**Returns:** Matching podcasts

---

### Cross-Component Tools

#### 13. `find_related_content`
Find related content across all components for a paper, podcast, or process.

**Example:**
```
Tool: find_related_content
Arguments: {
  "paper_id": "abc123",
  "limit": 10
}
```

**Returns:** Related papers, podcasts, and GLMP processes

#### 14. `get_paper_visualizations`
Get GLMP processes related to a paper.

**Example:**
```
Tool: get_paper_visualizations
Arguments: {
  "doi": "10.1038/nature12345"
}
```

**Returns:** Related GLMP processes

#### 15. `search_across_components`
Unified search across papers, podcasts, and GLMP.

**Example:**
```
Tool: search_across_components
Arguments: {
  "query": "CRISPR",
  "components": ["papers", "podcasts", "glmp"],
  "limit": 10
}
```

**Returns:** Results from all specified components

---

## Usage Examples

### Example 1: Find All Content About a Topic
```
1. search_across_components("CRISPR", ["papers", "podcasts", "glmp"])
2. Review results from all components
3. Use find_related_content to discover connections
```

### Example 2: Explore a Research Paper
```
1. get_paper_by_id(doi="10.1038/nature12345")
2. get_paper_citations(doi="10.1038/nature12345")
3. get_paper_visualizations(doi="10.1038/nature12345")
4. find_related_content(paper_id="...")
```

### Example 3: Discover Biological Processes
```
1. get_glmp_categories()
2. list_glmp_processes(category="Central Dogma")
3. get_glmp_process(process_name="DNA replication")
4. search_glmp_by_entity(entity="p53")
```

## Best Practices

1. **Use Limits:** Always specify reasonable limits to avoid large responses
2. **Combine Tools:** Use cross-component tools to discover relationships
3. **Entity Search:** Use entity search for precise biological/chemical queries
4. **Error Handling:** Check for errors in JSON responses
5. **Caching:** Results can be cached for frequently accessed data

## Troubleshooting

- **No Results:** Try broader search terms or remove filters
- **Slow Queries:** Reduce limit or use more specific filters
- **Missing Data:** Some tools require preprocessing (e.g., entity extraction)
- **Connection Errors:** Verify GCP credentials and network access

## Support

For issues or questions:
- Check `DEPLOYMENT.md` for setup issues
- Review `CHECKPOINTS.md` for implementation status
- See `README.md` for architecture overview



