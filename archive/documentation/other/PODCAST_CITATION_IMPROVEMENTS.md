# Podcast Citation & Description Improvements

**Deployed:** October 27, 2025  
**Revision:** `copernicus-podcast-api-00084-grx`

---

## ✅ Changes Implemented

### 1. **Natural Citation Style in Dialogue**

**Problem:** Speakers were reading out long URLs and DOIs in the audio, which sounded awkward.

**Solution:** Updated the prompt to instruct speakers to:
- ✅ Mention **author names, publication, and title**
- ✅ Say **"the link is in the description"** instead of reading URLs
- ✅ Keep citations natural and conversational

**Example Citation (NEW style):**
> "According to Smith and colleagues in Nature, their 2024 study on quantum entanglement—link in the description—found that..."

**Location:** `cloud-run-backend/podcast_research_integrator.py` lines 304-308

---

### 2. **Guaranteed Complete References in Description**

**Problem:** References were sometimes cut off due to the 4000-character podcast description limit.

**Solution:** Implemented intelligent description trimming that:
- ✅ **Prioritizes preserving full References section**
- ✅ Trims middle content (overview, key concepts) first if needed
- ✅ Keeps all citations complete with DOIs/URLs
- ✅ Preserves hashtags section

**Algorithm:**
1. Check if description exceeds 4000 characters
2. Identify References sections (contains "References", DOI, URLs, etc.)
3. Identify Hashtags sections (starts with #)
4. Calculate space needed for References + Hashtags + buffer
5. Trim other sections to fit while preserving full citations
6. Rebuild description with complete References at the end

**Location:** `cloud-run-backend/main.py` lines 1180-1216

---

### 3. **LLM Instructed to Generate Concise Descriptions**

**Problem:** LLM was generating verbose descriptions that didn't leave enough room for references.

**Solution:** Updated prompt to:
- ✅ Specify **MUST be under 3000 characters** (leaving 1000 char buffer)
- ✅ Request **concise** overview, key concepts, and insights
- ✅ Emphasize importance of **COMPLETE References section**
- ✅ Instruct to keep main content BRIEF to ensure references fit

**New Prompt Instructions:**
```
"description": "Comprehensive but CONCISE episode description (MUST be under 3000 characters) with:
    - Episode overview (1-2 paragraphs, concise)
    - Key concepts explored (3-4 bullet points, brief)
    - Research insights (1 paragraph citing actual papers)
    - Practical applications (1 paragraph, concise)
    - Future directions (1 paragraph, brief)
    - ## References section (list ALL citations with authors, titles, publications, DOIs/URLs)
    
    CRITICAL: Keep main content BRIEF to ensure References section is COMPLETE and under 3000 chars total
"
```

**Location:** `cloud-run-backend/podcast_research_integrator.py` lines 356-364

---

## 📊 Expected Results

### In Audio/Script:
- ✅ Natural citations: "Smith et al. in Nature 2024—link in description—found..."
- ✅ No long URLs read aloud
- ✅ Professional, conversational tone

### In Description:
- ✅ Full references with complete DOIs/URLs
- ✅ All citations from the research included
- ✅ No truncation of reference section
- ✅ Total length ≤ 4000 characters

---

## 🧪 Testing Recommendations

Generate a new podcast with:
- **Multiple research papers** (5+ sources)
- **Check the audio**: Verify no URLs are read aloud
- **Check the description**: Confirm all references are complete with DOIs/URLs

Expected behavior:
1. Speakers say "link in the description" instead of reading URLs
2. Description includes full References section at the end
3. If description is too long, middle content is trimmed but references are preserved
4. Total description length stays under 4000 characters

---

## 🔗 Related Files

- `cloud-run-backend/main.py` - Description upload and trimming logic
- `cloud-run-backend/podcast_research_integrator.py` - Prompt generation with citation instructions
- `copernicus.character.json` - Character configuration (includes voice definitions)

---

## 📝 Notes

- The 4000-character limit is based on the memory [[memory:2236697]] about podcast description length
- The trimming algorithm prioritizes References and Hashtags over middle content
- If a description is under 4000 chars, no trimming occurs
- The LLM is now instructed to generate descriptions under 3000 chars to ensure references always fit

---

**Status:** ✅ Deployed and Ready for Testing


