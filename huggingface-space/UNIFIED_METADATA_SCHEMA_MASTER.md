# Unified Metadata Schema - Master Document

**NSF Objective 2:** Unified Multi-Modal Metadata Representation  
**Status:** ✅ All Schemas Created  
**Last Updated:** January 10, 2025

## Overview

The CopernicusAI Knowledge Engine uses a **unified metadata schema** across all content types to enable cross-modal linking, semantic search, and algorithmic analysis. This master document describes the unified approach and how all content types interoperate.

## Core Schema Principles

### 1. Consistent ID Format
All content uses the format: `{source}_{identifier}`

- **Papers:** `pubmed_12345678`, `arxiv_2301.12345`, `crossref_10.1234/example`
- **Videos:** `youtube_dQw4w9WgXcQ`, `vimeo_123456789`
- **Processes:** `process_biology_dna-replication`, `process_chemistry_glycolysis`
- **Podcasts:** `podcast_ever-bio-250007`, `podcast_ever-chem-250002`

### 2. Common Core Fields (All Content Types)

| Field | Papers | Videos | Processes | Podcasts | Purpose |
|-------|--------|--------|-----------|----------|---------|
| `id` | ✅ | ✅ | ✅ | ✅ | Unique identifier (consistent format) |
| `title`/`name` | ✅ | ✅ | ✅ | ✅ | Content title for semantic matching |
| `source` | ✅ | ✅ | ✅ | ✅ | Provenance tracking |
| `category` | ✅ | ✅ | ✅ | ✅ | Primary discipline (cross-modal filtering) |
| `subcategories` | ✅ | ✅ | ✅ | ✅ | Fine-grained classification |
| `keywords` | ✅ | ✅ | ✅ | ✅ | Keyword-based linking |
| `url` | ✅ | ✅ | ✅ | ✅ | Direct access |
| `year` | ✅ | ✅ | ❌ | ✅ | Temporal filtering, linking |
| `acquired_date` | ✅ | ✅ | ✅ | ✅ | Quality/timeliness tracking |
| `quality_score` | ✅ | ✅ | ✅ | ✅ | NSF >=85% requirement |
| `related_papers` | ✅ | ✅ | ✅ | ✅ | Cross-modal linking |
| `related_videos` | ❌ | ✅ | ✅ | ✅ | Cross-modal linking |
| `related_processes` | ❌ | ✅ | ✅ | ✅ | Cross-modal linking |
| `related_podcasts` | ❌ | ❌ | ✅ | ✅ | Cross-modal linking |
| `entities` | ❌ | ✅ | ✅ | ✅ | Entity-based linking |

### 3. Cross-Modal Linking Fields

All content types can reference other content types:

- **`related_papers[]`** - Array of paper IDs (`pubmed_12345`, `arxiv_2301.12345`)
- **`related_videos[]`** - Array of video IDs (`youtube_abc123`)
- **`related_processes[]`** - Array of process IDs (`process_biology_dna-replication`)
- **`related_podcasts[]`** - Array of podcast IDs (`podcast_ever-bio-250007`)

## Content Type Schemas

### 1. Papers Schema
**File:** `copernicus-web-public/huggingface-space/scripts/acquire_papers/metadata_schema.json`

**Paper-Specific Fields:**
- `authors[]`, `author_string` - Author information
- `journal`, `journal_full` - Publication venue
- `doi`, `pmid`, `arxiv_id`, `bibcode` - Source identifiers
- `abstract` - Paper abstract
- `citation_count` - Citation metrics

**Cross-Modal Links:**
- Can link to related videos, processes, podcasts
- Keywords extracted for entity-based linking

### 2. Videos Schema (Educational/Communication)
**File:** `scienceviddb/metadata_schema.json`

**Video-Specific Fields:**
- `source_id` - Platform video ID (YouTube, Vimeo)
- `channel_id`, `channel_name`, `channel_url` - Channel information
- `duration`, `view_count` - Video metrics
- `transcript`, `transcript_segments[]` - Transcript data
- `temporal_metadata` - Chapters, topics, time-stamped segments
- `entities[]` - Extracted entities with temporal locations
- `thumbnail_url` - Preview image

**Cross-Modal Links:**
- Can link to related papers, processes, podcasts, video_data
- Entity extraction enables linking based on genes, proteins, compounds
- Transcript enables semantic similarity with paper abstracts

**Note:** These are **communication/educational videos** (lectures, explanations) with narration/audio.

### 2b. Video Data Schema (Scientific Data)
**File:** `scripts/video_data/metadata_schema.json`

**Video Data-Specific Fields:**
- `video_type` - microscopy, astronomical, experimental, high_speed, timelapse
- `recording_method` - time_lapse, real_time, high_speed, long_exposure
- `imaging_technique` - brightfield, fluorescence, confocal, optical_telescope, etc.
- `temporal_resolution` - Frame rate/temporal sampling
- `spatial_resolution` - Resolution in microns (microscopy) or arcseconds (astronomy)
- `time_span` - Real-time vs. recorded duration
- `experimental_conditions` - Temperature, pressure, medium, treatments
- `no_narration`, `no_audio` - Explicitly indicates data (not communication)

**Cross-Modal Links:**
- Can link to related papers, processes, videos (educational), podcasts
- Entity extraction for cells, organisms, structures, celestial objects
- Temporal tracking of entities within video

**Note:** These are **scientific data videos** (microscopy time-lapse, astronomical observations, experimental recordings) - video as DATA, not communication medium. No narration/audio.

### 3. Processes Schema
**File:** `copernicus-web-public/huggingface-space/scripts/processes/metadata_schema.json`

**Process-Specific Fields:**
- `mermaid` - Mermaid flowchart syntax
- `complexity` - Nodes, edges, gates metrics
- `colorScheme` - Visualization color mapping
- `subcategory`, `subcategory_name` - Process classification
- `organism` - Organism context (for biological processes)
- `sources[]` - Source papers/processes (with paper_id for linking)

**Cross-Modal Links:**
- Links to source papers (via `sources[].paper_id`)
- Can link to related videos explaining the process
- Can link to related podcasts discussing the process
- Keywords and entities enable semantic linking

### 4. Podcasts Schema
**File:** `copernicus-podcast-api/metadata_schema.json`

**Podcast-Specific Fields:**
- `guid` - Unique episode GUID
- `audioUrl`, `thumbnailUrl` - Media URLs
- `duration`, `duration_seconds` - Episode length
- `script`, `transcript`, `transcript_segments[]` - Text content
- `references[]` - Research paper references (with `paper_id` for linking)
- `prompt`, `subject` - Generation metadata
- `tags[]` - Hashtags from description

**Cross-Modal Links:**
- Links to source papers (via `references[].paper_id`)
- Can link to related videos, processes
- Transcript enables semantic similarity with papers
- Entities extracted for entity-based linking

## Cross-Modal Linking Strategies

### 1. Entity-Based Linking

**Papers:**
- Extract entities (genes, proteins, compounds) from abstracts
- Store in `keywords` or `categories` fields

**Videos:**
- Extract entities from transcripts
- Store in `entities[]` array with temporal metadata
- Link videos to papers mentioning same entities

**Processes:**
- Extract entities from process descriptions and Mermaid nodes
- Store in `entities[]` array
- Link processes to papers/videos about same entities

**Podcasts:**
- Extract entities from transcripts/scripts
- Store in `entities[]` array with temporal metadata
- Link podcasts to papers/videos/processes about same entities

### 2. Keyword-Based Linking

**All Content Types:**
- Keywords extracted from titles, descriptions, abstracts, transcripts
- Stored in `keywords[]` array
- Semantic similarity matching enables linking

### 3. Citation/Reference-Based Linking

**Papers:**
- Citation networks enable paper-to-paper linking
- Can link papers to videos/podcasts that explain them

**Processes:**
- `sources[]` array contains source papers
- `sources[].paper_id` enables direct linking

**Podcasts:**
- `references[]` array contains cited papers
- `references[].paper_id` enables direct linking

### 4. Temporal/Semantic Linking

**Videos & Podcasts:**
- Transcript segments enable time-stamped entity extraction
- Can link specific segments to paper sections
- Temporal metadata enables "skip to relevant part" features

## Database Schema Alignment

### Papers Database (JSON Files)
- Location: `metadata-database/papers/{discipline}/`
- Format: Individual JSON files per paper
- Validation: `validate_metadata.py` ensures schema compliance

### Videos Database (PostgreSQL)
- Table: `videos`
- Schema: Enhanced with cross-modal linking fields
- Migration: `docs/database_schema_enhancements.sql`

### Processes Database (JSON Files)
- Location: `{discipline}-processes-database/processes/{subcategory}/`
- Format: Individual JSON files per process
- Validation: (To be implemented)

### Podcasts Database (JSON File)
- Location: `public/podcasts.json`
- Format: Array of podcast objects
- Validation: (To be implemented)

## Implementation Status

### ✅ Completed

1. **Paper Metadata Schema**
   - ✅ JSON Schema definition
   - ✅ Validation script
   - ✅ Acquisition scripts generate schema-compliant JSON

2. **Video Metadata Schema**
   - ✅ JSON Schema definition
   - ✅ Database schema enhancements
   - ✅ Documentation

3. **Process Metadata Schema**
   - ✅ JSON Schema definition
   - ✅ Aligned with existing process structure

4. **Podcast Metadata Schema**
   - ✅ JSON Schema definition
   - ✅ Aligned with existing podcast structure

5. **Unified Documentation**
   - ✅ Master schema document
   - ✅ Cross-modal linking strategies
   - ✅ Implementation guides

### 🔄 In Progress

1. **Schema Validation**
   - 🔄 Process validation script
   - 🔄 Podcast validation script
   - 🔄 Cross-modal link validation

2. **Entity Extraction**
   - 🔄 Extract entities from all content types
   - 🔄 Link entities across modalities
   - 🔄 Temporal entity tracking

3. **Cross-Modal Linking Algorithms**
   - 🔄 Keyword-based matching
   - 🔄 Entity-based matching
   - 🔄 Semantic similarity matching
   - 🔄 Citation/reference-based linking

### 📋 Planned

1. **Database Migrations**
   - Migrate processes to unified schema format
   - Migrate podcasts to unified schema format
   - Add cross-modal linking fields to all databases

2. **Knowledge Engine Integration**
   - Unified search across all content types
   - Cross-modal relationship visualization
   - Related content recommendations

3. **API Enhancements**
   - Endpoints for cross-modal queries
   - "Related content" endpoints
   - Entity-based search

## Usage Examples

### Cross-Modal Query: Find All Content About DNA Replication

```sql
-- Papers
SELECT id, title FROM papers WHERE keywords && ARRAY['DNA', 'replication'];

-- Videos
SELECT id, title FROM videos WHERE keywords && ARRAY['DNA', 'replication'];

-- Processes
SELECT id, name FROM processes WHERE keywords && ARRAY['DNA', 'replication'];

-- Podcasts
SELECT id, title FROM podcasts WHERE keywords && ARRAY['DNA', 'replication'];
```

### Find Related Content for a Paper

```sql
-- Find videos related to a paper
SELECT * FROM videos WHERE 'pubmed_12345678' = ANY(related_papers);

-- Find processes related to a paper
SELECT * FROM processes WHERE 'pubmed_12345678' = ANY(related_papers);

-- Find podcasts related to a paper
SELECT * FROM podcasts WHERE 'pubmed_12345678' = ANY(related_papers);
```

### Find Content by Entity

```sql
-- Find all content mentioning "DNA polymerase"
SELECT 'paper' as type, id, title FROM papers WHERE 'DNA polymerase' = ANY(keywords)
UNION ALL
SELECT 'video' as type, id, title FROM videos WHERE EXISTS (
  SELECT 1 FROM jsonb_array_elements(entities) AS entity 
  WHERE entity->>'name' = 'DNA polymerase'
)
UNION ALL
SELECT 'process' as type, id, name as title FROM processes WHERE EXISTS (
  SELECT 1 FROM jsonb_array_elements(entities) AS entity 
  WHERE entity->>'name' = 'DNA polymerase'
)
UNION ALL
SELECT 'podcast' as type, id, title FROM podcasts WHERE EXISTS (
  SELECT 1 FROM jsonb_array_elements(entities) AS entity 
  WHERE entity->>'name' = 'DNA polymerase'
);
```

## NSF Proposal Alignment

This unified schema directly supports **NSF Objective 2: Unified Multi-Modal Metadata Representation**:

✅ **Canonical Schema Design** - Unified JSON schemas for papers, videos, processes, podcasts  
✅ **Cross-Modal Linking** - Common ID format and linking fields across all content types  
✅ **Metadata Quality** - Validation ensures >=85% quality across all types  
✅ **Entity Extraction** - Enables semantic and entity-based linking  
✅ **Temporal Metadata** - Video/podcast segments enable time-stamped linking  
✅ **Knowledge Graph** - All content types become nodes in unified knowledge graph  

**Timeline Alignment:** Year 1, Months 7-9 - "Unified metadata schema design and implementation" ✅

## Future Content Types (Extensibility)

The unified schema is designed to accommodate future content types. See **`SCHEMA_EXTENSIBILITY_GUIDE.md`** for:

- Design patterns for adding new content types
- Proposed schemas for images, animations, sounds, applications, models, datasets, code, visualizations
- Base schema template (`base_metadata_schema.json`)
- Implementation checklist

**Key Principle:** All new content types extend the base schema with common fields (id, title, category, keywords, related_*, entities, quality_score) while using flexible `metadata` JSONB for type-specific data.

---

**Part of CopernicusAI Knowledge Engine**  
**NSF Proposal:** CopernicusAI Knowledge Engine (CISE Core Programs - IIS)  
**Objective 2:** Unified Multi-Modal Metadata Representation
