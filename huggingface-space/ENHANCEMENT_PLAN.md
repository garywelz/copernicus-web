# Knowledge Engine Enhancement Plan

**Date:** January 11, 2025  
**Status:** Status page created, enhancements planned

## ✅ Completed

### 1. Status Dashboard Created
- **URL:** https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/knowledge-engine-status.html
- ✅ All project links organized
- ✅ Auto-updating statistics
- ✅ Progress bars
- ✅ Responsive design

## 📋 Enhancements Needed

### 1. Research Paper Database Front End ⚠️

**Status:** HTML viewer created, needs metadata file

**Created:**
- ✅ `papers-database-table.html` - Searchable, filterable table viewer
- ✅ Script to generate `papers-metadata.json`

**Features:**
- Search by title, author, abstract, keywords
- Filter by source (PubMed, arXiv, NASA ADS, Crossref)
- Filter by category (biology, chemistry, physics, etc.)
- Filter by year
- Sortable columns
- Pagination (50 papers per page)
- Links to DOI, PubMed, original URLs

**Next Steps:**
1. Generate `papers-metadata.json` (may be large - 23,246 papers)
2. Upload to GCS
3. Test the viewer
4. Consider splitting into smaller files if too large

**Note:** With 23,246 papers, the metadata file may be 50-100MB. Consider:
- Option A: Generate full metadata file (may be slow to load)
- Option B: Create paginated API endpoint
- Option C: Generate metadata in chunks by discipline

### 2. Science Video Database Enhancement ⚠️

**Current:** https://scienceviddb-web-204731194849.us-central1.run.app/
- Shows 0 videos (display issue)
- Not suitable for 700+ videos

**Needs:**
- ✅ Pagination or infinite scroll
- ✅ Search and filter (by discipline, channel, date, transcript)
- ✅ Grid view with thumbnails
- ✅ Table view option
- ✅ Video metadata display
- ✅ Transcript search

**Options:**
1. Enhance existing React/Next.js app (if that's what it is)
2. Create new table-based viewer (similar to process databases)
3. Create hybrid viewer (table + grid toggle)

**Recommendation:** Check the existing app structure first, then decide whether to enhance or rebuild.

### 3. Knowledge Map Enhancement ⚠️

**Current:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine
- User can't select which papers/objects to visualize
- Unclear filtering/customization

**Needs:**
- ✅ **Selection Interface:**
  - Checkboxes for content types (Papers, Processes, Videos, Podcasts)
  - Discipline filters
  - Date range selector
  - Keyword search
  - Source selection (PubMed, arXiv, etc.)
- ✅ **Map Controls:**
  - Show/hide different content types
  - Adjust node size (by citations, relevance)
  - Color coding by discipline
  - Zoom and pan controls
- ✅ **Clear Instructions:**
  - How to use the map
  - What the visualization shows
  - How to interpret connections

**Recommendation:** Add a sidebar or top panel with filter controls before rendering the map.

## Additional Pages Found

1. **Metadata Database Index** - `metadata-database/index.html` (exists locally, may need to check if it's a viewer)
2. **Individual Process Viewers** - May exist in GCS for each process
3. **Individual Paper Viewers** - Could be created for detailed paper pages
4. **Cross-Modal Linking Viewer** - Show connections between content types

## Implementation Priority

1. **High Priority:**
   - ✅ Status dashboard (DONE)
   - 📋 Research Paper Database (HTML created, needs metadata)
   - 📋 Science Video Database enhancement
   - 📋 Knowledge Map enhancement

2. **Medium Priority:**
   - Individual content viewers
   - Cross-modal linking visualization

3. **Low Priority:**
   - Statistics dashboard
   - Analytics pages

---

**Status:** Status page live! Paper database HTML ready, needs metadata generation. Video and Knowledge Map enhancements planned.
