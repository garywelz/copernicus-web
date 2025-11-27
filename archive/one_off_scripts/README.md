# Archived One-Off Scripts

This directory contains one-time migration scripts, utility scripts, and test scripts that were used during development but are no longer actively used in the production codebase.

## Directory Structure

- `root/` - Scripts from the project root directory
- `cloud-run-backend/` - Scripts from the cloud-run-backend directory

## Script Categories

### Migration Scripts
One-time scripts used to migrate or fix data:
- `assign_unknown_podcasts.py` - Assigned podcasts with missing subscriber IDs
- `fix_podcast_assignment.py` - Fixed podcast-to-subscriber assignments
- `sync_rss_status.py` - Synchronized RSS status across collections
- `fix_rss_feed.py` - Fixed RSS feed issues

### RSS Feed Scripts
One-time RSS feed generation/processing scripts:
- `generate_mvp_rss_lxml.py`
- `generate_mvp_rss.py`
- `generate_rss_from_csv.py`
- `rewrite_and_upload_rss.py`
- `remove_duplicate_old_items.py`

### Validation/Utility Scripts
One-time scripts for validation or analysis:
- `check_slugs.py`
- `check_news_files.py`
- `check_canonical_files.py`
- `list_rss_titles_and_guids.py`
- `list_unmatched_episodes.py`
- `compare_mapping_to_feed.py`
- `find_duplicate_enclosures.py`
- `find_unused_gcs_files.py`
- `list_subscribers.py`

### Database Scripts
One-time database analysis/generation scripts:
- `podcast-database-generator.py`
- `glmp-database-analyzer.py`

### Test Scripts
Development/test scripts:
- `test-drive.py`
- `test_canonical_naming.py`
- `test_gemini_3.py`
- `test_small_segments.py`
- `test_vertex_ai.py`
- `validate_apis.py`
- `discover_models.py`
- `research_discovery_apis.py`

## Note

These scripts are kept for historical reference but are not part of the active codebase. They may contain hardcoded values, outdated API calls, or assumptions about the database state at the time they were written.

**Do not run these scripts without reviewing and updating them first.**

