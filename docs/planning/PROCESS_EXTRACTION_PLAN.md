# Process Extraction Plan: Chemistry, Physics, Computer Science

## Overview

Extract processes from Programming Framework HTML files and create separate databases for each subject category, similar to what was done for mathematics processes.

## Content Inventory

### Chemistry Processes
- **Source:** https://garywelz-programming-framework.static.hf.space/chemistry_index.html
- **Batches:** 14 total
  - Batches 1-7: 3 processes each = 21 processes (uses `<h2>` tags)
  - Batches 8-14: 5 processes each = 35 processes (uses `<div class="process-title">`)
- **Total:** 56 processes
- **Subcategories:** Organic Chemistry, Physical Chemistry, Analytical Chemistry, Inorganic Chemistry, Biochemistry, Materials Chemistry, Environmental Chemistry, Electrochemical Processes, Surface Chemistry & Catalysis, Thermodynamic Processes, Kinetic Processes, Spectroscopy & Analysis, Quantum Chemistry, Materials Chemistry

### Physics Processes
- **Source:** https://garywelz-programming-framework.static.hf.space/physics_processes.html
- **Batches:** 2 total
  - Batch 1: 3 processes
  - Batch 2: 3 processes
- **Total:** 6 processes
- **Subcategories:** Classical Mechanics, (others to be determined from batch 2)

### Computer Science Processes
- **Source:** https://garywelz-programming-framework.static.hf.space/computer_science_index.html
- **Batches:** 7 total
  - Each batch: 3 processes
- **Total:** 21 processes
- **Subcategories:** Algorithms & Data Structures, Software Engineering, Artificial Intelligence, Computer Security, Computer Networks, Database Systems, Computer Graphics

## HTML Structure Analysis

Based on examination of sample files:

1. **Structure Pattern (Batches 1-7):**
   - Each batch HTML file contains multiple processes
   - Each process has:
     - `<h2>` tag with numbered title (e.g., "1. Process Name")
     - `<div class="mermaid">` containing Mermaid flowchart code
   - Same structure as mathematics processes

2. **Structure Pattern (Batches 8-14 for Chemistry):**
   - Uses `<div class="process-title">` instead of `<h2>`
   - Format: "Process 1: Process Name" or "Process 2: Process Name"
   - Still uses `<div class="mermaid">` for diagrams
   - Need to handle both formats in extraction script

2. **URL Pattern:**
   - Chemistry: `chemistry_batch_01.html` through `chemistry_batch_14.html`
   - Physics: `physics_batch_01.html` through `physics_batch_02.html`
   - Computer Science: `computer_science_batch_01.html` through `computer_science_batch_07.html`

3. **Base URL:**
   - `https://garywelz-programming-framework.static.hf.space/`

## Implementation Plan

### Phase 1: Create Generic Extraction Script

**File:** `scripts/extract_programming_framework_processes.py`

**Features:**
- Generic script that works for any subject category
- Takes subject name and batch URLs as input
- Extracts processes from batch HTML files
- Handles different batch numbering formats
- Creates JSON files organized by subcategory

**Parameters:**
- `--subject`: chemistry, physics, computer_science
- `--batch-urls`: List of batch HTML URLs (or auto-discover from index)
- `--output-dir`: Output directory for JSON files

### Phase 2: Subject-Specific Extraction Scripts

Create wrapper scripts for each subject:

1. **`scripts/extract_chemistry_processes.py`**
   - Calls generic script with chemistry-specific parameters
   - Handles 14 batches
   - Organizes by subcategory

2. **`scripts/extract_physics_processes.py`**
   - Calls generic script with physics-specific parameters
   - Handles 2 batches

3. **`scripts/extract_computer_science_processes.py`**
   - Calls generic script with CS-specific parameters
   - Handles 7 batches

### Phase 3: GCS Storage Structure

**Bucket:** `gs://regal-scholar-453620-r7-podcast-storage/`

**Structure:**
```
chemistry-processes-database/
  organic_chemistry/
    process-1.json
    process-2.json
  physical_chemistry/
    ...
  ...

physics-processes-database/
  classical_mechanics/
    process-1.json
    ...

computer_science-processes-database/
  algorithms_data_structures/
    process-1.json
    ...
```

### Phase 4: Sync Scripts

Create sync scripts for each subject (similar to `sync_math_processes.py`):

1. **`scripts/sync_chemistry_processes.py`**
   - Syncs from `chemistry-processes-database/` GCS path
   - Stores in Firestore collection `chemistry_processes`

2. **`scripts/sync_physics_processes.py`**
   - Syncs from `physics-processes-database/` GCS path
   - Stores in Firestore collection `physics_processes`

3. **`scripts/sync_computer_science_processes.py`**
   - Syncs from `computer_science-processes-database/` GCS path
   - Stores in Firestore collection `computer_science_processes`

### Phase 5: Firestore Integration

1. **Create Vector Indexes:**
   - `chemistry_processes` collection
   - `physics_processes` collection
   - `computer_science_processes` collection

2. **Update Config:**
   - Add collection constants to `mcp_server/config.py`

3. **Update Vector Search:**
   - Add chemistry, physics, computer_science to `search_semantic()`
   - Add to `find_similar_content()`
   - Add helper functions: `create_text_for_chemistry()`, etc.

4. **Update RAG Service:**
   - Include new process types in RAG context

### Phase 6: Testing

1. Test extraction for each subject
2. Test GCS upload
3. Test Firestore sync
4. Test vector search
5. Test RAG integration

## Detailed Steps

### Step 1: Create Generic Extraction Script

**File:** `scripts/extract_programming_framework_processes.py`

**Key Functions:**
- `extract_processes_from_batch(url, subject, batch_number)` - Extract from single batch
- `extract_all_batches(subject, batch_urls)` - Extract from all batches
- `determine_subcategory(title, subject, batch_number)` - Determine subcategory from title and batch
- `create_process_json(process_data, subject)` - Create JSON structure
- `MermaidExtractor` class - Handle both `<h2>` and `<div class="process-title">` formats

**JSON Structure:**
```json
{
  "id": "process-id",
  "title": "Process Title",
  "description": "Subject process: Process Title",
  "category": "chemistry|physics|computer_science",
  "subcategory": "organic_chemistry|classical_mechanics|algorithms",
  "mermaid": "...",
  "entities": [...],
  "metadata": {
    "source": "programming_framework",
    "batch": "batch_01",
    "batch_number": 1,
    "color_scheme": "discipline_based",
    "node_count": 50,
    "complexity": "high"
  }
}
```

### Step 2: Subject-Specific Wrappers

Each wrapper script will:
1. Define batch URLs for that subject
2. Call generic extraction script
3. Handle subject-specific subcategory mapping
4. Save to subject-specific output directory

### Step 3: GCS Upload

For each subject:
```bash
gsutil -m cp -r {subject}-processes/* \
  gs://regal-scholar-453620-r7-podcast-storage/{subject}-processes-database/
```

### Step 4: Sync Scripts

Each sync script will:
- Read from GCS `{subject}-processes-database/`
- Generate embeddings
- Store in Firestore `{subject}_processes` collection
- Use Vector type for embeddings

### Step 5: Vector Search Integration

Update `mcp_server/tools/vector_search.py`:
- Add `COLLECTION_CHEMISTRY_PROCESSES`, `COLLECTION_PHYSICS_PROCESSES`, `COLLECTION_COMPUTER_SCIENCE_PROCESSES` to imports
- Add search blocks for each in `search_semantic()`
- Add similarity search blocks in `find_similar_content()`
- Add helper functions for text extraction

### Step 6: Vector Indexes

Create indexes:
```bash
# Chemistry
gcloud firestore indexes composite create \
  --project=regal-scholar-453620-r7 \
  --database="copernicusai" \
  --collection-group=chemistry_processes \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding

# Physics
gcloud firestore indexes composite create \
  --project=regal-scholar-453620-r7 \
  --database="copernicusai" \
  --collection-group=physics_processes \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding

# Computer Science
gcloud firestore indexes composite create \
  --project=regal-scholar-453620-r7 \
  --database="copernicusai" \
  --collection-group=computer_science_processes \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
```

## Estimated Totals

| Subject | Batches | Processes/Batch | Total Processes |
|---------|---------|----------------|-----------------|
| Chemistry | 14 | 3-5 | 56 (21 + 35) |
| Physics | 2 | 3 | 6 |
| Computer Science | 7 | 3 | 21 |
| **Total** | **23** | **~3-5** | **83 processes** |

## Timeline

1. **Generic extraction script:** 2-3 hours
2. **Subject-specific wrappers:** 1 hour
3. **Extraction and testing:** 1-2 hours
4. **GCS upload:** 30 minutes
5. **Sync scripts:** 2-3 hours
6. **Vector search integration:** 2-3 hours
7. **Vector indexes:** 30 minutes
8. **Testing:** 1-2 hours

**Total Estimated Time:** 10-15 hours

## Files to Create

1. `scripts/extract_programming_framework_processes.py` (generic)
2. `scripts/extract_chemistry_processes.py`
3. `scripts/extract_physics_processes.py`
4. `scripts/extract_computer_science_processes.py`
5. `scripts/sync_chemistry_processes.py`
6. `scripts/sync_physics_processes.py`
7. `scripts/sync_computer_science_processes.py`

## Files to Update

1. `mcp_server/config.py` - Add collection constants
2. `mcp_server/tools/vector_search.py` - Add search capabilities
3. `services/rag_service.py` - Add to RAG context
4. `scripts/quick_search.py` - Add content type options

## Next Steps After Completion

1. Test all extraction scripts
2. Verify JSON structure
3. Upload to GCS
4. Run sync scripts
5. Create vector indexes
6. Test vector search
7. Update documentation

## Notes

- **Chemistry batches 1-7:** Use `<h2>` tags with format "1. Process Name"
- **Chemistry batches 8-14:** Use `<div class="process-title">` with format "Process 1: Process Name"
- **Physics and Computer Science:** Use `<h2>` tags (same as chemistry batches 1-7)
- Subcategory determination will be based on batch title and process title
- All processes use the same color coding system (Red, Yellow, Green, Blue, Violet)
- Mermaid diagrams are embedded in `<div class="mermaid">` tags
- Extraction script must handle both title formats

