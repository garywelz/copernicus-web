# Fix All Issues Plan

## Issues to Fix:

1. **Revert 5 news podcasts** from `ever-` format back to `news-` format:
   - news-bio-28032025 -> ever-bio-250041
   - news-chem-28032025 -> ever-chem-250022
   - news-compsci-28032025 -> ever-compsci-250031
   - news-math-28032025 -> ever-math-250041
   - news-phys-28032025 -> ever-phys-250043

2. **Fix podcast titles** - Remove "Copernicus AI: Frontiers of Science - " prefix:
   - "Copernicus AI: Frontiers of Science - AI-Designed Materials: A Paradigm Shift" → "AI-Designed Materials: A Paradigm Shift"
   - "Copernicus AI: Frontiers of Science - Prime Number Theory: A Paradigm Shift?" → "Prime Number Theory: A Paradigm Shift?"

3. **Fix subscriber podcast lists** - Only show podcasts created by that subscriber (already fixed in code)

4. **Fix admin dashboard counts** - Ensure counts match database

## Endpoints to Create:

1. `POST /api/admin/podcasts/revert-news` - Revert news podcasts
2. `POST /api/admin/podcasts/fix-titles` - Remove title prefix

