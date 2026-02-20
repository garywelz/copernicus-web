# Source References Integration Plan

**Issue:** All 206 processes currently only reference the Programming Framework methodology. They need actual research paper citations.

**Current State:**
- 200+ processes across 5 disciplines
- 12,000+ papers indexed in Knowledge Engine
- Need to link processes to relevant papers

---

## Source Reference Requirements

### Minimum Standards
- **Each process must have 1-3 relevant research papers**
- **Source format:** Title, Authors, Journal, Year, DOI/URL
- **Sources must be:** Directly relevant, accessible, verified

### Current Source Structure
```json
{
  "sources": [
    {
      "title": "Programming Framework: A Universal Process Visualization Methodology",
      "authors": "Welz, G.",
      "journal": "CopernicusAI Knowledge Engine",
      "year": "2025",
      "url": "https://huggingface.co/spaces/garywelz/programming_framework",
      "notes": "Methodology reference"
    }
  ]
}
```

### Required Source Structure
```json
{
  "sources": [
    {
      "title": "Programming Framework: A Universal Process Visualization Methodology",
      "authors": "Welz, G.",
      "journal": "CopernicusAI Knowledge Engine",
      "year": "2025",
      "url": "https://huggingface.co/spaces/garywelz/programming_framework",
      "notes": "Methodology reference"
    },
    {
      "title": "Actual Research Paper Title",
      "authors": "Author1, A., Author2, B., et al.",
      "journal": "Nature / Science / Journal Name",
      "year": "2023",
      "doi": "10.xxxx/xxxxx",
      "url": "https://doi.org/10.xxxx/xxxxx",
      "relevance": "Describes [specific aspect] of [process name]",
      "verified": true
    }
  ]
}
```

---

## Integration Approach

### Option 1: Manual Curation (Recommended for Quality)
- **Process:** For each process, identify 1-3 key papers from the 12,000+ indexed papers
- **Method:** Use Knowledge Engine Dashboard to search for relevant papers
- **Quality:** Highest quality, ensures relevance
- **Time:** More time-intensive but ensures accuracy

### Option 2: Automated Matching
- **Process:** Use LLM to match processes to papers based on keywords/topics
- **Method:** Query Knowledge Engine API with process keywords
- **Quality:** Good, but requires verification
- **Time:** Faster, but needs review

### Option 3: Hybrid Approach
- **Process:** Automated suggestions + manual review
- **Method:** Generate candidate papers, then curate
- **Quality:** Good balance
- **Time:** Efficient workflow

---

## Implementation Steps

### Phase 1: Access Paper Database
1. **Identify Access Method:**
   - Knowledge Engine Dashboard API?
   - Direct database access?
   - Paper metadata files?

2. **Paper Metadata Structure:**
   - Need to understand format of indexed papers
   - DOI, title, authors, journal, year, abstract?
   - How are papers currently stored/accessed?

### Phase 2: Matching Process
1. **For Each Process:**
   - Extract keywords and topics
   - Search paper database
   - Identify 1-3 most relevant papers
   - Verify relevance and accessibility

2. **Source Addition:**
   - Add paper references to JSON files
   - Update metadata
   - Verify links work

### Phase 3: Quality Assurance
1. **Verification:**
   - Check all DOIs resolve
   - Verify paper relevance
   - Ensure sources are accessible
   - Review for accuracy

---

## Questions to Resolve

1. **How to access the 12,000+ indexed papers?**
   - API endpoint?
   - Database location?
   - File structure?

2. **Paper metadata format?**
   - What fields are available?
   - How are papers organized?
   - Can we search by topic/keyword?

3. **Integration method?**
   - Direct database query?
   - Knowledge Engine API?
   - Manual file lookup?

4. **Priority order?**
   - Which disciplines first?
   - Which processes are highest priority?
   - Timeline expectations?

---

## Recommended Next Steps

1. **Immediate:** Fix biology links (IN PROGRESS)
2. **Short-term:** Identify paper database access method
3. **Medium-term:** Implement source matching system
4. **Long-term:** Add sources to all 206 processes

---

**Status:** Plan created. Awaiting information on paper database access method.
