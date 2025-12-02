# Find and Fix All Issues

## Findings from Script

✅ Parkinson's Disease podcast found: `ever-bio-250039`
✅ Database shows 61 podcasts
✅ 1 podcast missing canonical (news-bio-28032025 - already identified)

## Still Need To:

1. **Find the 3 missing podcasts** (64 → 61)
   - Need to check ALL podcast_jobs entries
   - Check if any use job IDs instead of canonical filenames
   - Compare total counts

2. **Fix YouTube Audio Corruption** (6 podcasts):
   - "Quantum Computing Advances"
   - "Silicon compounds"
   - "Quantum Computing chip advances"
   - "Prime Number Theory update"
   - "New materials created using AI"
   - "Matrix Multiplication advances"

   Need to:
   - Check if audio files exist
   - Verify file integrity
   - Regenerate if corrupt
   - Update RSS feed

