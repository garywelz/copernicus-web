# Mathematics Processes Database Table Setup

**Date:** December 31, 2025  
**Status:** Ready for deployment

---

## Overview

Created a database table for mathematics processes similar to the GLMP database table, but simplified for mathematics processes which don't have AND/OR gates or conditional nodes.

---

## Files Created

### 1. `generate_metadata.py`
Python script that:
- Scans all mathematics process JSON files in subdirectories
- Counts nodes from Mermaid diagrams
- Counts entities
- Generates `metadata.json` with statistics and process listings

**Usage:**
```bash
cd /home/gdubs/copernicus-web-public/math-processes
python3 generate_metadata.py
```

**Output:** `metadata.json` with:
- Total processes count
- Total nodes and entities
- Average nodes and entities
- Subcategory distribution
- Complexity distribution
- Full process listings with metadata

### 2. `mathematics-database-table.html`
Interactive HTML database table that:
- Fetches metadata from `metadata.json`
- Displays statistics cards
- Shows sortable table with columns:
  - **Process Name** (clickable links to flowcharts)
  - **Subcategory** (proof_methods, algorithms, linear_algebra, calculus, probability)
  - **Complexity** (low, medium, high)
  - **Nodes** (count of flowchart nodes)
  - **Entities** (count of extracted entities)
- Provides breakdown analysis by subcategory and complexity

**Note:** No AND/OR gates or conditional node columns (unlike GLMP) since mathematics processes don't use these.

---

## Table Columns

The database table shows:

1. **Process Name** - Clickable link to view the flowchart
2. **Subcategory** - Mathematics subdiscipline (proof_methods, algorithms, etc.)
3. **Complexity** - Process complexity level (low, medium, high)
4. **Nodes** - Total number of nodes in the Mermaid flowchart
5. **Entities** - Number of extracted entities/concepts

**Removed columns** (not applicable to mathematics):
- ❌ Organism (biology-specific)
- ❌ OR Gates (not used in math processes)
- ❌ AND Gates (not used in math processes)
- ❌ Total Gates (not used in math processes)

---

## Deployment Steps

### Step 1: Generate Metadata
```bash
cd /home/gdubs/copernicus-web-public/math-processes
python3 generate_metadata.py
```

This creates `metadata.json` in the same directory.

### Step 2: Deploy Files

**Option A: Deploy to Google Cloud Storage**
```bash
# Upload metadata.json
gsutil cp metadata.json gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/

# Upload HTML table
gsutil cp mathematics-database-table.html gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/

# Make publicly accessible
gsutil acl ch -u AllUsers:R gs://regal-scholar-453620-r7-podcast-storage/math-processes-database/*
```

**Option B: Deploy to Hugging Face Space**
- Upload both files to the programming-framework Hugging Face Space
- Update the HTML to use relative paths for metadata.json

### Step 3: Link from Programming Framework

Update the Programming Framework page to link to the database table:

**In `huggingface-space/programming-framework/index.html` or README.md:**

Replace the mathematics processes link:
```html
### 🔢 Mathematics
- [Mathematics Processes Collection](...) - Overview of mathematics process diagrams
```

With:
```html
### 🔢 Mathematics
- [Mathematics Processes Database Table](https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/math-processes-database/mathematics-database-table.html) - Interactive database table with all mathematics processes
- [Mathematics Processes Collection](...) - Overview of mathematics process diagrams
```

---

## URL Structure

Once deployed, the database table will be accessible at:
- **GCS:** `https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/math-processes-database/mathematics-database-table.html`
- **Hugging Face:** `https://huggingface.co/spaces/garywelz/programming_framework/blob/main/mathematics-database-table.html`

---

## Replicating for Other Disciplines

This same structure can be replicated for:
- **Chemistry** - Use `chemistry-processes/` directory
- **Physics** - Use `physics-processes/` directory  
- **Computer Science** - Use `computer_science-processes/` directory

**Steps:**
1. Copy `generate_metadata.py` to each discipline directory
2. Update the script to scan the correct subdirectories
3. Copy `mathematics-database-table.html` and rename (e.g., `chemistry-database-table.html`)
4. Update the HTML title, header, and metadata URL
5. Run the metadata generation script
6. Deploy both files
7. Link from Programming Framework page

---

## Current Mathematics Processes

Based on `index.json`, we have:
- **5 processes** total
- **5 subcategories:**
  - proof_methods (1)
  - algorithms (1)
  - linear_algebra (1)
  - calculus (1)
  - probability (1)

---

## Next Steps

1. ✅ Generate metadata.json (run the script)
2. ⏳ Deploy files to GCS or Hugging Face
3. ⏳ Update Programming Framework links
4. ⏳ Test the database table
5. ⏳ Replicate for Chemistry, Physics, and Computer Science

---

**Status:** Ready to generate metadata and deploy!

