# Revert News Podcasts Endpoint

Need to create an endpoint to revert these:
- news-bio-28032025 -> ever-bio-250041
- news-chem-28032025 -> ever-chem-250022
- news-compsci-28032025 -> ever-compsci-250031
- news-math-28032025 -> ever-math-250041
- news-phys-28032025 -> ever-phys-250043

The endpoint should:
1. Find podcasts with the current (wrong) canonical filenames
2. Update them back to the original news- format
3. Update Firestore (both podcast_jobs and episodes)
4. Update RSS feed if present
5. Update GCS file references if needed

