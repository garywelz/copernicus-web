# Paper Acquisition Scripts - Changelog

## Version 1.0.0 - January 10, 2025

### Added
- **Paper Acquisition Scripts:**
  - `acquire_pubmed_batch.py` - PubMed/NCBI acquisition (30,000 papers target)
  - `acquire_arxiv_batch.py` - arXiv acquisition (10,000 papers target)
  - `acquire_nasa_ads_batch.py` - NASA ADS acquisition (5,000 papers target)
  - `acquire_crossref_batch.py` - Crossref acquisition (flexible/journal-based)
  - `deduplicate_papers.py` - Cross-database deduplication

- **Schema and Validation:**
  - `metadata_schema.json` - Formal JSON Schema (Draft 7) for unified metadata representation
  - `validate_metadata.py` - Metadata validation and quality assessment tool

- **Documentation:**
  - `README.md` - Comprehensive usage guide and documentation
  - `NSF_PROPOSAL_ALIGNMENT.md` - Alignment with NSF proposal objectives
  - `CHANGELOG.md` - This file

### Features
- Unified JSON metadata schema across all sources
- Automated quality validation (>=85% threshold for NSF compliance)
- Cross-source deduplication with multiple matching strategies
- Citation integrity validation (DOI/arXiv ID/PMID format checking)
- Source tracking for provenance (NSF Objective 3: Reliability)
- Rate limiting and respectful API usage
- Test modes for all scripts
- Comprehensive error handling and logging

### NSF Proposal Alignment
- ✅ **Objective 2:** Unified Multi-Modal Metadata Representation
- ✅ **Objective 3:** Reliability and Trust Mechanisms (citation verification, source tracking)
- ✅ **Timeline:** Year 1, Months 7-9 - "Unified metadata schema design and implementation"

### Technical Details
- **Schema Version:** 1.0
- **Validation Threshold:** 85% (NSF requirement)
- **Citation Integrity Target:** >=95% (NSF requirement)
- **Supported Sources:** PubMed, arXiv, NASA ADS, Crossref
- **Output Format:** JSON (unified schema)

### Known Issues
- None currently

### Future Enhancements
- [ ] Add support for bioRxiv/medRxiv
- [ ] Add support for Zenodo
- [ ] Enhanced entity extraction (genes, proteins, compounds)
- [ ] Integration with Knowledge Engine knowledge graph
- [ ] Automated quality improvement suggestions

---

**Part of the CopernicusAI Knowledge Engine**  
**NSF Proposal:** CopernicusAI Knowledge Engine (CISE Core Programs - IIS)
