# Fix ArXiv Search - Remove OpenRouter Dependency

## Problem

**ArXiv search is failing because it requires OpenRouter API key**, but ArXiv is a **public API** that doesn't need any authentication!

The current code:
1. Tries to use OpenRouter to "refine" the search query
2. If OpenRouter fails, it might silently fail
3. Returns 0 sources even though ArXiv has thousands of papers

## Root Cause

In `research_pipeline.py`, the `_search_arxiv()` method:
- Requires `self.openrouter_api_key` (line 193)
- Uses OpenRouter to refine query before searching ArXiv
- If OpenRouter fails or key is missing, search fails

**ArXiv is PUBLIC and doesn't need any API key!**

## The Fix

Make ArXiv search work directly without OpenRouter dependency:

1. **Search ArXiv directly** - no OpenRouter needed
2. **Use proper ArXiv query syntax** for mathematics
3. **Fallback gracefully** if OpenRouter refinement fails (optional)

## Implementation

```python
async def _search_arxiv(self, query: str, depth: str) -> List[ResearchSource]:
    """Search arXiv for preprint papers - PUBLIC API, no auth needed"""
    sources = []
    max_results = {"basic": 5, "comprehensive": 15, "exhaustive": 25}
    
    try:
        # ArXiv is PUBLIC - search directly!
        # Map query to ArXiv categories (math.NT = Number Theory)
        arxiv_categories = self._map_to_arxiv_categories(query)
        
        # Build search query
        search_terms = []
        for term in query.split():
            search_terms.append(f"all:{term}")
        
        # Add category filter for mathematics
        category_filter = ""
        if "math" in query.lower() or "number theory" in query.lower():
            category_filter = "+AND+cat:math.NT"  # Number Theory category
        
        search_query = "+OR+".join(search_terms) + category_filter
        
        arxiv_params = {
            "search_query": search_query or f"all:{query}",
            "start": 0,
            "max_results": max_results.get(depth, 15),
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.endpoints["arxiv"], params=arxiv_params) as response:
                if response.status == 200:
                    xml_data = await response.text()
                    sources = self._parse_arxiv_xml(xml_data)
                    
    except Exception as e:
        structured_logger.warning("ArXiv search error", error=str(e), query=query)
    
    return sources

def _map_to_arxiv_categories(self, query: str) -> str:
    """Map search query to ArXiv categories"""
    query_lower = query.lower()
    
    # Mathematics categories
    if "number theory" in query_lower or "arithmetic" in query_lower:
        return "math.NT"  # Number Theory
    elif "algebra" in query_lower:
        return "math.AC"  # Commutative Algebra
    elif "geometry" in query_lower:
        return "math.DG"  # Differential Geometry
    # ... more mappings
    
    return ""
```

## Why This Matters

- **ArXiv has MILLIONS of papers** including thousands on number theory
- **No API key needed** - it's a public service
- **Direct search is faster** - no need to refine query first
- **More reliable** - one less dependency

## Next Steps

1. Fix ArXiv search to work directly
2. Test with "number theory" query
3. Ensure other APIs (CORE, Zenodo) are also working
4. Add better error logging

---

**This should fix the 0 sources problem!**



