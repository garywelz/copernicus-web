# Vector Indexing Status

**Date**: January 13, 2026  
**Issue**: Vector Search and RAG return no results

## Root Cause

Vector Search and RAG require documents in Firestore to have an `embedding` field containing vector embeddings. Currently:

- ✅ **Content exists** in Firestore (papers, processes)
- ❌ **Content lacks embeddings** - documents don't have the `embedding` field
- ❌ **Vector search fails silently** - returns empty results when no embeddings found

## Technical Details

The vector search code in `mcp_server/tools/vector_search.py` uses:

```python
vector_query = papers_ref.find_nearest(
    vector_field="embedding",  # Requires this field to exist
    query_vector=Vector(query_embedding),
    ...
)
```

If documents don't have an `embedding` field, the query returns no results (silently).

## Current Status

- **Browse Content**: ✅ Works (queries Firestore directly, doesn't need embeddings)
- **Vector Search**: ❌ Returns empty (no embeddings in documents)
- **RAG**: ❌ Returns empty (depends on vector search)

## Solution Required

1. **Generate embeddings** for existing content in Firestore
2. **Add embeddings** to new content as it's ingested
3. **Verify embeddings** are being created and stored

## Next Steps

1. Check if embedding generation service is working
2. Create a script to backfill embeddings for existing papers
3. Ensure new content gets embeddings when added
4. Test vector search with embedded content

## Temporary Workaround

- Users can use **Browse Content** to see available papers/processes
- Vector Search/RAG will work once embeddings are added
- Examples in UI match available content and will work once indexed
