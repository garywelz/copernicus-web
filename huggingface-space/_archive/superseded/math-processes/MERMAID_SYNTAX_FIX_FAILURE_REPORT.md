# Mermaid Syntax Error Fix - Failure Report
**Date:** January 5, 2026  
**Issue:** Mathematics Process Flowcharts Displaying "Syntax error in text"  
**Status:** ❌ **UNRESOLVED** - All 41 processes still showing syntax errors

---

## Problem Summary

All 41 mathematics process HTML pages in the Mathematics Processes Database are displaying "Syntax error in text" when rendering Mermaid flowcharts. The pages are hosted on Google Cloud Storage at:
- `gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/processes/*.html`

**Example affected page:**
- `binomial-coefficient-calculation.html`
- `convex-hull-algorithm.html`
- All 41 processes in the database

**Error displayed:** "Syntax error in text" with Mermaid version 11.12.2

---

## Root Cause Analysis

### Primary Issue: JSON Source Files Contain Inline Styles

The mathematics process JSON files (stored in `math-processes/[subcategory]/*.json`) contain Mermaid code with **inline style statements** mixed directly into the graph definition:

**Example from `binomial-coefficient-calculation.json`:**
```json
"mermaid": "graph TD A1[[Input: n (Total items), k (Items to choose)]] --> B1([Check: n >= 0 and k >= 0]) style A1 fill:#ff6b6b,color:#fff style B1 fill:#ffd43b,color:#000 B1 -- Yes --> C1..."
```

**Problems:**
1. All Mermaid code is on a single line (no line breaks)
2. Style statements (`style NodeID fill:...,color:...`) are inline between edges
3. Mermaid.js requires styles to be on separate lines at the end
4. Edges need to be one-per-line for reliable parsing

### Secondary Issue: HTML Generation Pipeline

The HTML pages are generated from JSON files using `math-processes/create_individual_pages.py`, which:
1. Reads Mermaid code from JSON files
2. Attempts to clean it using `clean_mermaid_syntax()` function
3. Embeds the cleaned code into HTML templates
4. The cleaned code is then processed by `scripts/sanitize_math_mermaid.py`

**Problem:** The cleaning functions are not successfully handling all edge cases, particularly:
- Preserving source node IDs when splitting edges
- Handling double brackets `[[...]]` in node definitions
- Correctly extracting and repositioning inline styles

---

## Attempted Solutions

### Solution 1: Sanitizer Script (`scripts/sanitize_math_mermaid.py`)
**Status:** ❌ Partial success

**What it does:**
- Downloads HTML files from GCS
- Extracts Mermaid blocks from HTML
- Attempts to:
  - Move style statements to separate lines
  - Split edges to one-per-line
  - Fix HTML entity escaping
  - Pretty-print Mermaid code

**Results:**
- Successfully processes files (reports 159-169 change operations)
- Files on GCS show correct formatting when inspected
- **BUT:** Browser still shows syntax errors

**Why it failed:**
- The sanitizer works on already-generated HTML, but the HTML is regenerated from JSON
- The JSON source files still contain the problematic inline styles
- Regenerating HTML reintroduces the problems

### Solution 2: Enhanced `clean_mermaid_syntax()` Function
**Status:** ❌ Partial success

**What was attempted:**
1. Extract inline style statements using regex
2. Remove styles from middle of code
3. Add styles at the end on separate lines
4. Split edges to one-per-line while preserving source node IDs
5. Handle double brackets `[[...]]` correctly

**Code changes made:**
- Added style extraction: `r'\bstyle\s+([A-Za-z0-9]+)\s+fill:(#[0-9A-Fa-f]{3,6})\s*,\s*color:(#[0-9A-Fa-f]{3,6})\b'`
- Added edge splitting with source ID preservation
- Added line break normalization

**Results:**
- Local files show correct formatting when inspected
- GCS files show correct formatting when inspected via `gsutil cat`
- **BUT:** Browser still shows syntax errors

**Why it failed:**
- The fixes work in isolation but may not handle all edge cases
- Complex nested patterns (double brackets with parentheses in text) may not be fully handled
- Browser may be caching or there may be CDN caching issues
- OR: There may be additional syntax issues not visible in the formatted output

### Solution 3: Entity Cleaning for "Key Concepts" Section
**Status:** ✅ Success (but unrelated to Mermaid errors)

**What was done:**
- Added `clean_entity_for_display()` function to clean malformed entity patterns
- Prevents HTML corruption in the "Key Concepts" section

**Results:**
- Key Concepts section no longer contains Mermaid code fragments
- **BUT:** This doesn't fix the Mermaid syntax errors in the flowchart itself

---

## Current State

### Files on GCS (Verified via `gsutil cat`)

**Example from `binomial-coefficient-calculation.html`:**
```mermaid
graph TD
A1[[Input: n (Total items), k (Items to choose)]]
A1 --> B1([Check: n >= 0 and k >= 0])
B1 -- Yes --> C1([Check: k <= n])
...
style A1 fill:#ff6b6b,color:#fff
style B1 fill:#ffd43b,color:#000
...
```

**Formatting appears correct:**
- ✅ `graph TD` on its own line
- ✅ Edges are one-per-line
- ✅ Source node IDs preserved
- ✅ Style statements on separate lines at end
- ✅ HTML entities properly escaped (`--&gt;`, `&gt;`, `&lt;`)

### Browser Display (User Report)

**Still showing:**
- ❌ "Syntax error in text" message
- ❌ Bomb icon indicating Mermaid parse failure
- ❌ No flowchart rendered

**Tested in:**
- Regular browser window
- Incognito/private window (fresh cache)
- Multiple processes (all 41 affected)

---

## Possible Remaining Issues

### 1. Mermaid.js Version Compatibility
- Current: Mermaid version 11.12.2 (from CDN)
- The syntax may require a different format than what we're generating
- Double brackets `[[...]]` may not be supported or may require different syntax

### 2. Hidden Characters or Encoding Issues
- There may be invisible characters (zero-width spaces, BOM markers) in the JSON files
- Encoding issues when reading/writing files
- Line ending differences (CRLF vs LF)

### 3. Mermaid Syntax Requirements Not Met
- Mermaid may require specific formatting we're not aware of
- The `[[...]]` double bracket syntax may be invalid
- Node text with special characters may need different escaping

### 4. Browser/CDN Caching
- Despite cache-busting headers, CDN may still be serving old versions
- Browser may have cached the error state
- GCS may have its own caching layer

### 5. JavaScript Execution Order
- Mermaid initialization may be happening before DOM is ready
- Script loading order issues
- Race conditions in Mermaid.js initialization

---

## Comparison with Working System (GLMP)

**Working example:** GLMP biological processes
- URL: `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/glmp-v2/viewer/index.html?process=ecoli_amino_acid_biosynthesis`
- **Status:** ✅ Renders correctly without syntax errors

**Key differences:**
- GLMP uses different JSON structure
- GLMP Mermaid code may have been generated differently
- GLMP may use different node syntax (single brackets vs double brackets)

**Investigation needed:**
- Compare GLMP JSON structure with mathematics JSON structure
- Compare GLMP Mermaid syntax with mathematics Mermaid syntax
- Identify what makes GLMP work that mathematics doesn't have

---

## Files Modified

1. **`math-processes/create_individual_pages.py`**
   - Enhanced `clean_mermaid_syntax()` function
   - Added style extraction and repositioning
   - Added edge splitting with source ID preservation
   - Added entity cleaning function

2. **`scripts/sanitize_math_mermaid.py`**
   - Added logic to handle missing source node IDs
   - Enhanced edge splitting
   - Improved HTML entity escaping

3. **All 41 HTML files regenerated and uploaded to GCS**

---

## Recommended Next Steps

### Option 1: Compare with GLMP (Highest Priority)
1. Download a working GLMP process JSON file
2. Compare its Mermaid syntax structure with mathematics JSON files
3. Identify the exact differences in syntax
4. Adapt mathematics JSON generation to match GLMP format

### Option 2: Manual Fix of JSON Source Files
1. Fix the JSON source files directly (not just the generated HTML)
2. Ensure Mermaid code in JSON has:
   - Proper line breaks
   - Styles on separate lines
   - Correct node syntax
3. Regenerate HTML from fixed JSON

### Option 3: Test with Minimal Mermaid Example
1. Create a minimal test HTML page with a simple Mermaid diagram
2. Verify it renders correctly
3. Gradually add complexity until we find what breaks
4. Use this to identify the exact syntax requirement

### Option 4: Use Different Mermaid Syntax
1. Convert `[[...]]` double brackets to single brackets `[...]`
2. Test if this resolves the syntax errors
3. Update JSON generation to use single brackets

### Option 5: Validate Mermaid Syntax Before Embedding
1. Add a Mermaid syntax validator to the generation pipeline
2. Use Mermaid's parser to validate before embedding
3. Reject invalid syntax and regenerate

---

## Technical Details

### JSON File Location
- Path: `math-processes/[subcategory]/*.json`
- Example: `math-processes/combinatorics/binomial-coefficient-calculation.json`

### HTML Generation
- Script: `math-processes/create_individual_pages.py`
- Output: `math-processes/processes/*.html`
- Upload: `gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/processes/*.html`

### Sanitizer Script
- Script: `scripts/sanitize_math_mermaid.py`
- Processes: HTML files (not JSON)
- Output: Sanitized HTML with proper Mermaid formatting

### Mermaid Version
- CDN: `https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js`
- Version displayed in error: 11.12.2

---

## Conclusion

Despite multiple attempts to fix the Mermaid syntax errors through:
1. HTML sanitization
2. Enhanced cleaning functions
3. Style extraction and repositioning
4. Edge splitting with source ID preservation
5. Cache-busting and re-uploading

**The issue persists.** All 41 mathematics process pages continue to display "Syntax error in text" when rendered in browsers, even though the files on GCS appear to be correctly formatted when inspected directly.

**Recommendation:** Compare the working GLMP implementation with the mathematics processes to identify the fundamental difference in Mermaid syntax or generation approach that makes GLMP work while mathematics fails.

---

**Prepared by:** AI Assistant (Auto)  
**For:** Cursor.com / User handoff  
**Date:** January 5, 2026

