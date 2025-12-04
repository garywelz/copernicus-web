# Comprehensive Diagnosis and Fix Plan

## Issue 1: Missing Podcasts (64 → 61)

**Status**: Parkinson's Disease podcast found (`ever-bio-250039`)
**Action Needed**: Find the 3 missing podcasts

**Solution**: Create endpoint that:
- Counts ALL podcast_jobs entries
- Counts ALL episodes entries
- Compares with database count
- Lists any podcasts not in database

## Issue 2: YouTube Audio Corruption (6 podcasts)

**Failed Episodes**:
1. "Quantum Computing Advances"
2. "Silicon compounds"
3. "Quantum Computing chip advances"
4. "Prime Number Theory update"
5. "New materials created using AI"
6. "Matrix Multiplication advances"

**Solution**: Create endpoint that:
- Finds each podcast by title
- Checks if audio file exists in GCS
- Verifies audio file integrity (downloads and checks)
- Regenerates audio if corrupt
- Updates RSS feed

## Endpoints to Create

1. `GET /api/admin/podcasts/find-all` - Find ALL podcasts with complete counts
2. `POST /api/admin/podcasts/diagnose-youtube-errors` - Diagnose YouTube audio issues
3. `POST /api/admin/podcasts/fix-youtube-audio` - Fix corrupt audio files

