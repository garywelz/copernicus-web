# Schema Extensibility Guide - Future Content Types

**Purpose:** Design patterns and guidelines for adding new content types to the unified metadata schema  
**NSF Objective 2:** Unified Multi-Modal Metadata Representation  
**Last Updated:** January 10, 2025

## Overview

The unified metadata schema is designed to be **extensible** to accommodate future content types while maintaining cross-modal interoperability. This guide provides patterns, best practices, and examples for adding new content types.

## Extensibility Principles

### 1. Core Common Fields (Required for All Types)

All new content types MUST include these fields:

```json
{
  "id": "{source}_{identifier}",           // Unique ID in consistent format
  "title": "Content Title",                // Or "name" for processes
  "source": "{content_source}",            // Where content originates
  "category": "{discipline}",              // Primary discipline
  "subcategories": [],                     // Fine-grained classification
  "keywords": [],                          // For cross-modal linking
  "url": "https://...",                    // Direct access URL
  "year": "YYYY",                          // Publication/creation year (if applicable)
  "acquired_date": "ISO8601",              // When metadata was acquired
  "quality_score": 0.0-1.0,                // Metadata quality (NSF >=0.85)
  "related_papers": [],                    // Cross-modal links
  "related_videos": [],
  "related_processes": [],
  "related_podcasts": [],
  "entities": []                           // Extracted entities
}
```

### 2. Flexible Type-Specific Fields

Use these patterns for type-specific data:

- **Type-specific arrays:** `related_{type}s[]` - Add new array for new content type
- **Flexible metadata:** `metadata JSONB` - Store type-specific data as structured JSON
- **Media-specific fields:** Store in `metadata` if not universally applicable

### 3. ID Format Rules

**Pattern:** `{content_type}_{source}_{identifier}`

- **Images:** `image_nasa_apod_20250110`, `image_hubble_jwst-001`
- **Animations:** `animation_scratch_protein-folding`, `animation_blender_mitosis`
- **Sounds:** `sound_librosa_sample-001`, `sound_bioacoustics_bird-call`
- **Applications:** `app_jupyter_notebook-dna`, `app_shiny_metabolomics`
- **Models:** `model_pytorch_deep-learning`, `model_3d_blender_molecule`, `model_mathematical_ecosystem`
- **Datasets:** `dataset_zenodo_123456`, `dataset_geo_gse12345`
- **Code Repositories:** `code_github_copernicusai/knowledge-engine`, `code_gitlab_protein-analysis`
- **Interactive Visualizations:** `viz_observable_dna-replication`, `viz_plotly_metabolomics`

### 4. Source Enum Extension

When adding new content types, extend the `source` enum:

```json
{
  "source": {
    "type": "string",
    "enum": [
      "existing_sources...",
      "image_repository",      // For images
      "animation_platform",    // For animations
      "sound_library",         // For sounds
      "application_repo",      // For applications
      "model_registry",        // For models
      "dataset_repository",    // For datasets
      "code_repository",       // For code
      "interactive_viz"        // For interactive visualizations
    ]
  }
}
```

## Proposed Future Content Types

### 1. Images (Scientific Graphics)

**Use Cases:**
- Microscopy images (cells, tissues)
- Telescope images (astronomy)
- Scientific illustrations
- Data visualizations
- Chemical structures
- Molecular models

**Type-Specific Fields:**
```json
{
  "content_type": "image",
  "image_url": "https://...",
  "thumbnail_url": "https://...",
  "format": "png|jpg|svg|tiff",
  "dimensions": {
    "width": 1920,
    "height": 1080,
    "resolution": "300dpi"
  },
  "image_type": "microscopy|telescope|illustration|visualization|structure|model",
  "imaging_technique": "fluorescence|electron_microscopy|X-ray|crystallography",
  "caption": "Image description",
  "license": "CC-BY|public_domain|copyright",
  "credits": "Attribution information",
  "metadata": {
    "camera_settings": {},
    "processing": {},
    "scale_bar": {},
    "annotations": []
  }
}
```

**Schema File:** `metadata_schema_images.json`

### 2. Animations

**Use Cases:**
- Molecular animations (protein folding, DNA replication)
- Process animations (cell division, chemical reactions)
- Time-lapse visualizations
- 3D animations
- Interactive animations

**Type-Specific Fields:**
```json
{
  "content_type": "animation",
  "animation_url": "https://...",
  "thumbnail_url": "https://...",
  "format": "mp4|gif|webm|html5",
  "duration": 30.5,  // seconds
  "frame_rate": 30,
  "dimensions": {
    "width": 1920,
    "height": 1080
  },
  "animation_type": "molecular|process|timelapse|3d|interactive",
  "interactive": false,
  "controls": ["play", "pause", "seek", "speed"],
  "metadata": {
    "frames": 900,
    "compression": "h264",
    "transcript": []  // If has narration
  }
}
```

**Schema File:** `metadata_schema_animations.json`

### 3. Video Data (Scientific Video/Film Data)

**Note:** Distinct from videos (communication medium like YouTube lectures) - this is video as **data**

**Use Cases:**
- Microscopy time-lapse recordings (cell division, protein movement)
- Astronomical observations (time-lapse of celestial events)
- Experimental recordings (without narration)
- High-speed camera recordings (chemical reactions, physical processes)
- Microscopic observations (bacterial growth, tissue development)
- Telescope recordings (planetary motion, stellar events)
- Scientific film archives (historical experimental footage)

**Type-Specific Fields:**
```json
{
  "content_type": "video_data",
  "video_url": "https://...",
  "thumbnail_url": "https://...",
  "format": "mp4|avi|mov|tiff_sequence",
  "duration": 300.5,  // seconds
  "frame_rate": 30,   // fps
  "dimensions": {
    "width": 1920,
    "height": 1080,
    "resolution_um_per_pixel": 0.1  // For microscopy
  },
  "video_type": "microscopy|astronomical|experimental|high_speed|timelapse|observation",
  "recording_method": "time_lapse|real_time|high_speed|long_exposure",
  "imaging_technique": "brightfield|fluorescence|phase_contrast|electron_microscopy|optical_telescope|radio_telescope",
  "temporal_resolution": "1fps|30fps|1000fps",  // Temporal sampling
  "spatial_resolution": {
    "x": 0.1,  // microns or arcseconds
    "y": 0.1,
    "z": 1.0   // For 3D/time-lapse
  },
  "time_span": {
    "start": "ISO8601",
    "end": "ISO8601",
    "duration_real_time": 3600  // Real time duration (if time-lapse)
  },
  "experimental_conditions": {
    "temperature": 37.0,  // Celsius
    "pressure": 1.0,      // atm
    "medium": "...",
    "strain": "...",
    "treatment": "..."
  },
  "metadata": {
    "microscope_type": "confocal|electron|light",
    "telescope_type": "optical|radio|space_based",
    "camera_settings": {},
    "processing": {},
    "annotations": [],
    "no_narration": true  // Explicitly indicates data, not educational
  }
}
```

**Schema File:** `metadata_schema_video_data.json`

**Distinction from "videos" (Communication):**
- **Videos:** Educational content, lectures, explanations, with narration/audio
- **Video Data:** Raw scientific observations, experimental recordings, without narration

### 4. Sounds (Scientific Audio Data)

**Note:** Distinct from podcasts (communication medium) - this is audio as **data**

**Use Cases:**
- Bioacoustic recordings (bird calls, whale songs)
- Sonification of scientific data
- Audio signals from experiments
- Environmental sound recordings
- Sound spectra from chemical reactions

**Type-Specific Fields:**
```json
{
  "content_type": "sound",
  "audio_url": "https://...",
  "format": "wav|mp3|flac|aac",
  "duration": 45.2,  // seconds
  "sample_rate": 44100,
  "bit_depth": 16,
  "channels": 1,  // mono or stereo
  "sound_type": "bioacoustic|sonification|experimental|environmental|spectrum",
  "recording_method": "field_recording|laboratory|synthesized",
  "frequency_range": {
    "min": 20,   // Hz
    "max": 20000 // Hz
  },
  "metadata": {
    "location": {},      // For field recordings
    "equipment": [],
    "processing": {},
    "transcript": []     // If contains speech/annotations
  }
}
```

**Schema File:** `metadata_schema_sounds.json`

### 5. Applications & Applets

**Use Cases:**
- Jupyter notebooks
- Interactive web applications (Shiny, Streamlit, Dash)
- Simulation tools
- Data analysis tools
- Educational apps
- Scientific calculators

**Type-Specific Fields:**
```json
{
  "content_type": "application",
  "application_url": "https://...",
  "code_repository_url": "https://github.com/...",
  "application_type": "jupyter_notebook|web_app|desktop_app|mobile_app|browser_extension",
  "runtime": "python|javascript|r|matlab|julia",
  "framework": "jupyter|shiny|streamlit|dash|react",
  "interactive": true,
  "requires_authentication": false,
  "deployment": "binder|colab|mybinder|custom",
  "dependencies": [
    "numpy>=1.20.0",
    "pandas>=1.3.0"
  ],
  "usage_instructions": "...",
  "metadata": {
    "version": "1.0.0",
    "last_updated": "ISO8601",
    "contributors": [],
    "license": "MIT|GPL|Apache"
  }
}
```

**Schema File:** `metadata_schema_applications.json`

### 6. Models (Scientific Models)

**Use Cases:**
- Machine learning models (PyTorch, TensorFlow)
- 3D models (Blender, molecular structures)
- Mathematical models (equations, simulations)
- Computational models (agent-based, system dynamics)
- Statistical models

**Type-Specific Fields:**
```json
{
  "content_type": "model",
  "model_url": "https://...",
  "model_file": "model.pth|model.obj|model.py",
  "model_type": "machine_learning|3d|mathematical|computational|statistical",
  "model_format": "pytorch|tensorflow|onnx|blender|obj|gltf|python",
  "framework": "pytorch|tensorflow|scikit-learn|blender|mathematica",
  "model_architecture": "CNN|RNN|Transformer|GAN|...",
  "parameters": {
    "total": 1000000,
    "trainable": 950000,
    "frozen": 50000
  },
  "training_data": ["dataset_zenodo_123456"],
  "performance_metrics": {
    "accuracy": 0.95,
    "f1_score": 0.93
  },
  "requirements": {
    "hardware": "GPU|CPU",
    "memory": "8GB",
    "runtime": "python>=3.8"
  },
  "metadata": {
    "training_epochs": 100,
    "loss_function": "cross_entropy",
    "optimizer": "adam"
  }
}
```

**Schema File:** `metadata_schema_models.json`

### 7. Datasets

**Use Cases:**
- Experimental datasets
- Simulation outputs
- Curated collections
- Reference datasets
- Benchmarks

**Type-Specific Fields:**
```json
{
  "content_type": "dataset",
  "dataset_url": "https://...",
  "download_url": "https://...",
  "dataset_format": "csv|hdf5|parquet|json|sqlite",
  "size": {
    "rows": 1000000,
    "columns": 50,
    "files": 10,
    "total_size_bytes": 500000000
  },
  "dataset_type": "experimental|simulation|curated|reference|benchmark",
  "license": "CC0|CC-BY|public_domain",
  "citation": "...",
  "schema": {
    "columns": [
      {"name": "column1", "type": "float", "description": "..."}
    ]
  },
  "metadata": {
    "collection_method": "...",
    "quality_control": {},
    "version": "1.0"
  }
}
```

**Schema File:** `metadata_schema_datasets.json`

### 8. Code Repositories

**Use Cases:**
- Research code
- Analysis scripts
- Tool libraries
- Pipelines

**Type-Specific Fields:**
```json
{
  "content_type": "code",
  "repository_url": "https://github.com/...",
  "repository_type": "github|gitlab|bitbucket|custom",
  "language": "python|r|julia|matlab|cpp",
  "license": "MIT|GPL|Apache",
  "stars": 150,
  "forks": 45,
  "contributors": 10,
  "last_updated": "ISO8601",
  "main_language": "python",
  "topics": ["machine-learning", "biology", "analysis"],
  "metadata": {
    "readme": "...",
    "documentation_url": "https://...",
    "ci_cd": true
  }
}
```

**Schema File:** `metadata_schema_code.json`

### 9. Interactive Visualizations

**Use Cases:**
- D3.js visualizations
- Observable notebooks
- Plotly dashboards
- Tableau workbooks
- Custom interactive tools

**Type-Specific Fields:**
```json
{
  "content_type": "visualization",
  "visualization_url": "https://...",
  "visualization_type": "d3|observable|plotly|tableau|custom",
  "interactive": true,
  "embed_code": "<iframe>...</iframe>",
  "data_source": ["dataset_zenodo_123456"],
  "visualization_library": "d3.js|plotly|observable|vega-lite",
  "metadata": {
    "interactions": ["zoom", "pan", "filter", "hover"],
    "responsive": true
  }
}
```

**Schema File:** `metadata_schema_visualizations.json`

## Additional Future Considerations

### 10. AR/VR Content
- 3D molecular visualizations in VR
- Immersive learning experiences
- Virtual lab environments

### 11. Interactive Documents
- Jupyter Book pages
- Observable articles
- Executable papers

### 12. API Endpoints
- REST APIs for scientific data
- GraphQL endpoints
- WebSocket streams

### 13. Educational Resources
- Course materials
- Tutorials
- Problem sets
- Solutions

## Schema Template for New Content Types

When adding a new content type, follow this template:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CopernicusAI Knowledge Engine - {ContentType} Metadata Schema",
  "description": "Unified metadata schema for {content type description} supporting NSF Objective 2",
  "type": "object",
  "required": [
    "id",
    "title",
    "source",
    "acquired_date"
  ],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique identifier in format: {content_type}_{source}_{identifier}"
    },
    "title": {
      "type": "string",
      "minLength": 1
    },
    "content_type": {
      "type": "string",
      "const": "{content_type_name}",
      "description": "Content type identifier"
    },
    "source": {
      "type": "string",
      "enum": ["...", "..."],
      "description": "Source platform/database"
    },
    "category": {
      "type": "string",
      "enum": ["biology", "chemistry", "physics", "mathematics", "computer_science", "interdisciplinary", "foundational"]
    },
    "subcategories": {
      "type": "array",
      "items": {"type": "string"}
    },
    "keywords": {
      "type": "array",
      "items": {"type": "string"}
    },
    "url": {
      "type": "string",
      "format": "uri"
    },
    "year": {
      "type": ["string", "null"]
    },
    "related_papers": {"type": "array", "items": {"type": "string"}},
    "related_videos": {"type": "array", "items": {"type": "string"}},
    "related_processes": {"type": "array", "items": {"type": "string"}},
    "related_podcasts": {"type": "array", "items": {"type": "string"}},
    "related_{new_type}s": {"type": "array", "items": {"type": "string"}},
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {"type": "string", "enum": ["gene", "protein", "compound", "concept", "method", "organism", "other"]},
          "name": {"type": "string"}
        }
      }
    },
    "quality_score": {
      "type": ["number", "null"],
      "minimum": 0.0,
      "maximum": 1.0
    },
    "acquired_date": {
      "type": "string",
      "format": "date-time"
    },
    "metadata": {
      "type": "object",
      "description": "Type-specific flexible metadata"
    }
  },
  "additionalProperties": true
}
```

## Implementation Checklist

When adding a new content type:

- [ ] Create JSON schema file following template
- [ ] Extend `source` enum in master schema
- [ ] Add `content_type` field to distinguish from other types
- [ ] Add `related_{type}s[]` arrays to all existing schemas
- [ ] Create validation script
- [ ] Document in master schema document
- [ ] Update Knowledge Engine search to include new type
- [ ] Add to cross-modal linking algorithms
- [ ] Update API endpoints
- [ ] Add to dashboard UI

## Database Schema Considerations

For new content types, consider:

1. **Storage Strategy:**
   - JSON files (like papers/processes) for static content
   - PostgreSQL table (like videos) for dynamic/queryable content
   - Hybrid approach based on access patterns

2. **Indexing:**
   - GIN indexes for arrays (`related_*`, `keywords`, `entities`)
   - Full-text search indexes for `title`, `description`
   - Vector embeddings for semantic search

3. **Cross-Modal Linking:**
   - Add `related_{type}s` columns/fields to existing tables
   - Use materialized views for efficient cross-type queries
   - Consider graph database for complex relationships

## Best Practices

1. **Maintain Consistency:**
   - Always include core common fields
   - Use consistent naming conventions
   - Follow ID format rules

2. **Flexibility:**
   - Use `metadata JSONB` for type-specific data
   - Don't over-specify in schema if not needed
   - Allow `additionalProperties: true` for extensibility

3. **Quality:**
   - Always include `quality_score`
   - Validate against schema
   - Track `acquired_date` for freshness

4. **Linking:**
   - Always support cross-modal linking
   - Include `related_*` arrays
   - Extract keywords and entities

5. **Documentation:**
   - Document new content type in master schema doc
   - Provide examples
   - Update this guide with new patterns

---

**Status:** ✅ Extensibility patterns defined  
**Next Steps:** Implement specific schemas as content types are added  
**NSF Alignment:** Supports future modalities mentioned in Objective 2
