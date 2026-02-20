# Knowledge Map Enhancement Plan

**Date:** January 11, 2025  
**Status:** ⚠️ In Progress

## Current Situation

**URL:** https://copernicus-frontend-phzp4ie2sq-uc.a.run.app/knowledge-engine

**Issues:**
- User can't select which papers/objects to visualize
- Unclear filtering/customization
- No clear instructions on how to use the map
- Can't filter by content type, discipline, date, keywords

## Enhancement Goals

### 1. Selection Interface ✅

**Add sidebar or top panel with:**
- Checkboxes for content types:
  - ☑ Papers
  - ☑ Processes
  - ☑ Videos
  - ☑ Podcasts
- Multi-select capability
- "Select All" / "Deselect All" options

### 2. Filter Controls ✅

**Add filter panel with:**
- **Discipline filters:**
  - ☑ Biology
  - ☑ Chemistry
  - ☑ Physics
  - ☑ Mathematics
  - ☑ Computer Science
  - ☑ Interdisciplinary

- **Date range selector:**
  - Start date picker
  - End date picker
  - Quick filters: "Last year", "Last 5 years", "All time"

- **Keyword search:**
  - Text input for keyword search
  - Search in titles, abstracts, descriptions

- **Source filters:**
  - ☑ PubMed
  - ☑ arXiv
  - ☑ NASA ADS
  - ☑ Crossref
  - ☑ YouTube
  - ☑ RSS Feed

### 3. Map Customization Options ✅

**Add controls for:**
- **Node size:**
  - By citations
  - By relevance
  - By date
  - Uniform

- **Color coding:**
  - By discipline
  - By content type
  - By date
  - By source

- **Show/Hide options:**
  - Show/hide different content types
  - Show/hide connections
  - Show/hide labels

- **Layout options:**
  - Force-directed
  - Hierarchical
  - Circular

### 4. Clear Instructions ✅

**Add help section with:**
- How to use the map
- What the visualization shows
- How to interpret connections
- How to filter and customize
- Keyboard shortcuts

## Implementation Approach

### Option A: Enhance Existing App
- If source code is available locally
- Add React/Next.js components for filters
- Integrate with existing visualization

### Option B: Create Standalone Enhancement Page
- Create new HTML page with enhanced interface
- Load data from APIs
- Use D3.js or similar for visualization
- Can be deployed separately

### Option C: Create Filter Panel Overlay
- Create standalone filter panel component
- Can be embedded in existing page
- Communicates via postMessage or shared state

## Recommended Approach

**Option B: Create Standalone Enhancement Page**

**Reasons:**
1. Can work independently of existing app
2. Easier to test and iterate
3. Can be deployed to GCS like other database viewers
4. Can be linked from status page

**Structure:**
- HTML page with embedded JavaScript
- Loads data from metadata files (papers, videos, processes, podcasts)
- Uses D3.js or vis.js for graph visualization
- Full filter/selection interface
- Clear instructions panel

## Next Steps

1. Explore existing knowledge map implementation
2. Create enhanced knowledge map page
3. Add selection and filter interface
4. Add customization options
5. Add instructions
6. Test with real data
7. Upload to GCS
8. Update status page link

---

**Status:** Planning complete, ready to implement.
