# Paper Acquisition Scripts

Scripts for acquiring research papers from multiple academic databases as part of the CopernicusAI Knowledge Engine **Ingestion** capability.

## Overview

These scripts implement the **Ingestion** capability from the Knowledge Engine framework, systematically acquiring papers from multiple sources to build the paper database for analysis, connection, and knowledge graph construction.

## Scripts

### 1. `acquire_pubmed_batch.py`
Acquires papers from PubMed/NCBI using Entrez API.

**Target:** 30,000 papers (15,000 recent 2020-2025, 15,000 classic 1950-2019)  
**Focus:** Biology, medicine, biochemistry

**Requirements:**
- `biopython` package: `pip install biopython`
- Optional: PubMed API key (increases rate limits from 3 to 10 requests/second)

**Usage:**
```bash
# Test mode (10 papers)
python3 acquire_pubmed_batch.py --test

# Acquire recent papers only
python3 acquire_pubmed_batch.py --recent 15000

# Acquire classic papers only
python3 acquire_pubmed_batch.py --classic 15000

# Full acquisition
python3 acquire_pubmed_batch.py --recent 15000 --classic 15000
```

**Output:** Saves papers to `metadata-database/papers/biology/recent/` and `classic/`

### 2. `acquire_arxiv_batch.py`
Acquires papers from arXiv using their API.

**Target:** 10,000 papers (5,000 recent 2023-2025, 5,000 classic pre-2023)  
**Focus:** Physics, CS, math, quantitative biology

**Requirements:**
- Standard library only (uses `requests` if available, otherwise `urllib`)

**Usage:**
```bash
# Test mode (10 papers)
python3 acquire_arxiv_batch.py --test

# Acquire recent papers only
python3 acquire_arxiv_batch.py --recent 5000

# Acquire classic papers only
python3 acquire_arxiv_batch.py --classic 5000

# Full acquisition
python3 acquire_arxiv_batch.py --recent 5000 --classic 5000
```

**Output:** Saves papers to `metadata-database/papers/{discipline}/arxiv_recent/` and `arxiv_classic/`

### 3. `acquire_nasa_ads_batch.py`
Acquires papers from NASA Astrophysics Data System (ADS).

**Target:** 5,000 papers  
**Focus:** Astronomy, astrophysics, planetary science

**Requirements:**
- NASA ADS API token (free from https://ui.adsabs.harvard.edu/user/settings/token)
- Set environment variable: `export NASA_ADS_API_TOKEN='your-token'`
- Or create Google Secret: `NASA_ADS_API_TOKEN`

**Usage:**
```bash
# Test mode (10 papers)
python3 acquire_nasa_ads_batch.py --test

# Acquire papers
python3 acquire_nasa_ads_batch.py --count 5000
```

**Output:** Saves papers to `metadata-database/papers/physics/nasa_ads/`

### 4. `acquire_crossref_batch.py`
Acquires papers using Crossref API for DOI-based and journal-based searches.

**Target:** Flexible (can be used for specific journals or DOI lists)  
**Focus:** Multi-publisher coverage

**Requirements:**
- Standard library only (uses `requests` if available, otherwise `urllib`)

**Usage:**
```bash
# Test mode (10 papers)
python3 acquire_crossref_batch.py --test

# Search by journal ISSN
python3 acquire_crossref_batch.py --journal-issn "1234-5678" --count 1000

# Search by query
python3 acquire_crossref_batch.py --query "machine learning" --count 1000

# Acquire from DOI list file
python3 acquire_crossref_batch.py --doi-file dois.txt

# With year filters
python3 acquire_crossref_batch.py --journal-issn "1234-5678" --year-start 2020 --year-end 2025
```

**Output:** Saves papers to `metadata-database/papers/{discipline}/crossref/`

### 5. `deduplicate_papers.py`
Deduplicates papers across multiple sources using DOI matching, title similarity, and author overlap.

**Capabilities:**
- Exact DOI matching (highest confidence)
- Exact arXiv ID matching
- Exact PubMed ID matching
- Exact NASA ADS bibcode matching
- Title similarity + author overlap matching (configurable thresholds)

**Usage:**
```bash
# Test mode (100 papers)
python3 deduplicate_papers.py --test

# Deduplicate all papers in papers/ directory
python3 deduplicate_papers.py

# Deduplicate specific sources
python3 deduplicate_papers.py --sources biology chemistry physics

# Custom output directory
python3 deduplicate_papers.py --output papers_deduplicated
```

**Output:** Saves deduplicated papers to `metadata-database/papers_deduplicated/` with deduplication report

## Installation

### Required packages:
```bash
pip install biopython  # For PubMed acquisition only
pip install requests   # Optional but recommended (all scripts work without it)
```

### API Keys/Tokens:

1. **PubMed API Key** (optional but recommended):
   - Get from: https://www.ncbi.nlm.nih.gov/account/settings/
   - Set: `export PUBMED_API_KEY='your-key'`
   - Or create Google Secret: `PUBMED_API_KEY`

2. **NASA ADS API Token** (required for NASA ADS):
   - Get from: https://ui.adsabs.harvard.edu/user/settings/token
   - Set: `export NASA_ADS_API_TOKEN='your-token'`
   - Or create Google Secret: `NASA_ADS_API_TOKEN`

## Integration with Knowledge Engine

These scripts implement the **Ingestion** capability (Capability 1) of the Knowledge Engine framework:

1. **Ingestion** ✅ - Multi-source, multi-modal acquisition (these scripts)
2. **Digestion** - Processing into structured forms (next step)
3. **Analysis** - Pattern identification
4. **Calculation** - Mathematical computation
5. **Comparison** - Similarity assessment
6. **Connection** - Relationship discovery (knowledge graph)
7. **Association** - Correlation analysis
8. **Analogy** - Cross-domain mapping
9. **Communication** - Multi-modal expression

The acquired papers feed into the Knowledge Engine's knowledge graph, enabling the other eight capabilities through systematic data collection and organization.

## Directory Structure

```
metadata-database/papers/
├── biology/
│   ├── recent/          # PubMed recent papers
│   └── classic/         # PubMed classic papers
├── chemistry/
├── physics/
│   ├── nasa_ads/        # NASA ADS papers
│   └── arxiv_recent/    # arXiv papers
├── mathematics/
│   └── arxiv_recent/
├── computer_science/
│   └── arxiv_recent/
└── interdisciplinary/
    └── arxiv_recent/

metadata-database/papers_deduplicated/
├── biology/
├── chemistry/
├── physics/
├── mathematics/
├── computer_science/
├── interdisciplinary/
└── deduplication_report.json
```

## Metadata Schema and Validation

### Unified Metadata Schema

All papers follow a **unified JSON schema** (`metadata_schema.json`) that supports NSF Objective 2: Unified Multi-Modal Metadata Representation.

**Schema Features:**
- Standardized fields across all sources
- Required fields: `id`, `title`, `source`, `acquired_date`
- Quality fields: `authors`, `journal`, `year`, `abstract`, `doi`, `url`, `category`
- Source-specific identifiers: `pmid`, `arxiv_id`, `bibcode`
- Cross-modal linking support: `doi`, identifiers, `categories`

**Validate Metadata Quality:**
```bash
# Validate a single file
python3 validate_metadata.py papers/biology/recent/pubmed_12345678.json

# Validate entire directory
python3 validate_metadata.py papers/biology/ --recursive

# JSON output
python3 validate_metadata.py papers/ --recursive --json > validation_report.json
```

**NSF Success Criteria:**
- Metadata quality >=85% (validated by `validate_metadata.py`)
- Citation integrity >=95% (DOI/arXiv ID validation)
- Grounding rate >=90% (source tracking for every paper)

## Next Steps

After acquiring papers:

1. **Validate metadata quality**: `python3 validate_metadata.py papers/`
2. **Run deduplication**: `python3 deduplicate_papers.py`
3. **Review deduplication report**: Check `deduplication_report.json`
4. **Process papers** (Digestion capability):
   - Entity extraction (genes, proteins, compounds)
   - Metadata normalization
   - Quality assessment
5. **Integrate with Knowledge Engine**:
   - Build knowledge graph connections
   - Generate vector embeddings
   - Enable RAG queries
   - Link to processes and podcasts

## Notes

- All scripts respect rate limits and include delays between requests
- Scripts are designed to be resumable (check for existing papers before fetching)
- Test modes are available for all scripts to verify functionality
- Output format is consistent JSON across all scripts for easy integration
- Papers include source tracking for provenance and quality assessment
- All papers conform to unified metadata schema (`metadata_schema.json`)
- Metadata validation ensures NSF proposal success criteria (quality >=85%)

## NSF Proposal Compliance

These scripts directly support **NSF Objective 2: Unified Multi-Modal Metadata Representation**:

✅ **Canonical Schema Design** - Unified JSON schema (`metadata_schema.json`)  
✅ **Metadata Generation Pipelines** - Automated acquisition scripts  
✅ **Cross-Modal Linking Foundation** - Structured identifiers (DOI, arXiv, PMID)  
✅ **Quality Assurance** - Validation script ensures >=85% metadata quality  
✅ **Source Tracking** - Every paper tracks provenance (required for reliability)  
✅ **Citation Integrity** - DOI/arXiv ID validation (target: >=95%)

**Timeline Alignment:** Year 1, Months 7-9 - "Unified metadata schema design and implementation" ✅

## Tools and Utilities

### `validate_metadata.py`
Validates paper metadata against unified schema and NSF quality requirements.

**Usage:**
```bash
# Validate single file
python3 validate_metadata.py path/to/paper.json

# Validate directory (recursive)
python3 validate_metadata.py papers/biology/ --recursive

# JSON output for reporting
python3 validate_metadata.py papers/ --recursive --json > validation_report.json

# Custom quality threshold
python3 validate_metadata.py papers/ --threshold 0.90
```

**Output:**
- Validation status (valid/invalid)
- Quality score (0.0 to 1.0)
- Field completeness analysis
- Error reporting
- NSF compliance check (>=85% quality threshold)

---

**Part of the CopernicusAI Knowledge Engine**  
**NSF Proposal:** CopernicusAI Knowledge Engine (CISE Core Programs - IIS)  
**Objective 2:** Unified Multi-Modal Metadata Representation

© 2025 Gary Welz. All rights reserved.
