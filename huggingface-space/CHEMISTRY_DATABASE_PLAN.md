# Chemistry Database Creation Plan

## Goal
Convert existing chemistry HTML flowcharts (from `progframe/programming_framework/chemistry_batch_*.html`) to JSON format, creating a comprehensive chemistry processes database modeled on GLMP structure but using the 5-color scheme.

## Key Requirements

1. **Color Scheme**: Use 5-color scheme (NOT 8-color GLMP scheme)
   - Red (#ff6b6b) - Triggers & Inputs
   - Yellow (#ffd43b) - Structures & Objects (black text)
   - Green (#51cf66) - Processing & Operations
   - Blue (#74c0fc) - Intermediates & States
   - Violet (#b197fc) - Products & Outputs
   - **No separate colors for AND/OR/NOT gates** (unlike GLMP's 8-color scheme)

2. **JSON Structure**: Model on GLMP but adapted for 5-color scheme
   - Similar metadata fields
   - Similar complexity tracking
   - But simplified colorScheme section (5 colors only)

3. **Source**: 14 chemistry batch HTML files in `/home/gdubs/progframe/programming_framework/`
   - Each batch contains 3 processes (approximately)
   - Total: ~42 processes to convert

## Chemistry Subcategories (from chemistry_index.html)

1. **Organic Chemistry** - Batch 01 (3 processes)
2. **Physical Chemistry** - Batch 02 (3 processes)
3. **Analytical Chemistry** - Batch 03 (3 processes)
4. **Inorganic Chemistry** - Batch 04 (3 processes)
5. **Biochemistry** - Batch 05 (3 processes)
6. **Materials Chemistry** - Batch 06 (3 processes)
7. **Environmental Chemistry** - Batch 07 (3 processes)
8. **Nuclear Chemistry** - Batch 08 (3 processes)
9. **Theoretical Chemistry** - Batch 09 (3 processes)
10. **Polymer Chemistry** - Batch 10 (3 processes)
11. **Medicinal Chemistry** - Batch 11 (3 processes)
12. **Computational Chemistry** - Batch 12 (3 processes)
13. **Electrochemistry** - Batch 13 (3 processes)
14. **Surface Chemistry** - Batch 14 (3 processes)

## Process Steps

1. **Extract from HTML**:
   - Parse each chemistry_batch_*.html file
   - Extract process titles (from `<h2>` tags)
   - Extract Mermaid flowcharts (from `<div class="mermaid">`)
   - Extract descriptions/figures (from figure captions if available)

2. **Analyze Flowcharts**:
   - Count nodes (unique identifiers)
   - Count edges (arrows)
   - Count conditionals/decision points
   - Count AND/OR gates (if any - but don't color them separately)

3. **Generate JSON Files**:
   - Create individual JSON files per process
   - Use naming convention: `{subcategory}-{process-name-slug}.json`
   - Store in: `chemistry-processes-database/processes/{subcategory}/`

4. **Create Metadata**:
   - Generate `metadata.json` with process list
   - Include statistics (total processes, nodes, complexity, etc.)

5. **Create Database Table HTML**:
   - Model on GLMP database table
   - Load from metadata.json
   - Display interactive table with all processes
   - Link to individual process viewers

## JSON Structure (per process)

```json
{
  "id": "organic-chemistry-organic-reaction-mechanisms",
  "name": "Organic Reaction Mechanisms Process",
  "category": "chemistry",
  "subcategory": "organic_chemistry",
  "description": "Description of the process...",
  "complexity": {
    "nodes": 35,
    "edges": 40,
    "conditionals": 3,
    "logicGates": {
      "orGates": 2,
      "andGates": 1,
      "total": 3
    },
    "level": "detailed"
  },
  "colorScheme": {
    "red": {
      "hex": "#ff6b6b",
      "category": "Triggers & Inputs"
    },
    "yellow": {
      "hex": "#ffd43b",
      "category": "Structures & Objects"
    },
    "green": {
      "hex": "#51cf66",
      "category": "Processing & Operations"
    },
    "blue": {
      "hex": "#74c0fc",
      "category": "Intermediates & States"
    },
    "violet": {
      "hex": "#b197fc",
      "category": "Products & Outputs"
    }
  },
  "mermaid": "graph TD\n    A1[Reactant Molecules] --> B1[Reaction Type Classification]\n    ...",
  "sources": [],
  "keywords": [],
  "relatedProcesses": [],
  "created": "2025-01-XX",
  "lastUpdated": "2025-01-XX",
  "verified": false,
  "notes": "Converted from chemistry_batch_01.html"
}
```

## Storage Location

- **GCS Path**: `gs://regal-scholar-453620-r7-podcast-storage/chemistry-processes-database/`
- **Local Path**: Create in workspace for development, then upload

## Next Steps

1. Create Python script to extract and convert HTML → JSON
2. Run script on all 14 chemistry batch files
3. Validate JSON files
4. Create metadata.json
5. Create database-table.html (modeled on GLMP)
6. Test locally
7. Upload to GCS

---

**Status**: Ready to begin implementation
