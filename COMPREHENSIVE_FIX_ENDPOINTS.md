# Comprehensive Fix Endpoints

## Endpoints to Create

### 1. `GET /api/admin/podcasts/find-all`
Finds ALL podcasts including:
- All podcast_jobs entries
- All episodes entries
- Compares counts
- Identifies missing podcasts

### 2. `POST /api/admin/podcasts/diagnose-youtube-errors`
Diagnoses YouTube audio corruption:
- Finds podcasts by title
- Checks if audio files exist
- Verifies file integrity
- Returns diagnosis report

### 3. `POST /api/admin/podcasts/fix-youtube-audio`
Fixes corrupt audio:
- Regenerates audio for failed podcasts
- Updates RSS feed
- Returns fix results

## Implementation Status

Due to the large file size (8166 lines), I'll create these endpoints in a focused manner. The endpoints will be added to handle both issues comprehensively.

