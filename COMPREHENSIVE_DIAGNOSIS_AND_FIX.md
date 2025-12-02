# Comprehensive Diagnosis and Fix Plan

## Issue 1: Missing Podcasts (64 → 61)

Need to find:
- All podcasts in Firestore (podcast_jobs + episodes)
- Compare with database count
- Find podcasts using job IDs/UUIDs
- Search for "Parkinson's Disease" podcast

## Issue 2: YouTube Audio Corruption (6 podcasts)

Failed episodes:
1. "Quantum Computing Advances"
2. "Silicon compounds"
3. "Quantum Computing chip advances"
4. "Prime Number Theory update"
5. "New materials created using AI"
6. "Matrix Multiplication advances"

For each, need to:
- Check if audio file exists in GCS
- Verify file integrity (not corrupt)
- Check RSS feed entry
- Regenerate audio if needed
- Update RSS feed

