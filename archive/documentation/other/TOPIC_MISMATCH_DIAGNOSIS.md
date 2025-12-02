# Topic Mismatch Diagnosis: Number Theory → Neuro Anatomy

## The Problem

**Requested:** "Recent advances in number theory" (Mathematics)  
**Got:** Podcast about neuro anatomy / myotome mapping (Medicine)

---

## Root Cause Analysis

### What I Found:

1. **Research Context is EMPTY** (`{}` in Firestore)
   - No research sources (0 sources)
   - No topic set in research_context
   - No key findings, paradigm shifts, etc.

2. **Research Phase Should Have Failed**
   - Code requires `require_minimum_sources=3`
   - But somehow it passed with 0 sources

3. **Prompt Sent to LLM**
   - Prompt includes: `🎙️ PODCAST GENERATION: {research_context.topic}`
   - Research evidence section was empty
   - LLM had no actual research sources to work with

4. **LLM Behavior**
   - Given prompt about "number theory" but NO research sources
   - LLM hallucinated content about neuro anatomy instead
   - Generated coherent, well-formatted content but completely wrong topic

---

## Why This Happened

### Scenario 1: Research Discovery Failed Silently
- Research APIs returned 0 sources for "number theory"
- Exception wasn't raised properly
- Empty research_context was created and passed through

### Scenario 2: Research Context Not Saved
- Research was found but not serialized to Firestore
- In-memory research_context was empty by the time prompt was built
- Firestore shows empty `{}` which suggests serialization issue

### Scenario 3: Topic Lost in Translation
- Request topic: "Recent advances in number theory"
- Research_context.topic was not set
- Prompt used empty/undefined topic

---

## Evidence

From Firestore:
```python
request.topic = "Recent advances in number theory"
research_context = {}  # EMPTY!
research_sources_count = 0
```

From Generated Content:
- References neuro anatomy papers (Sonoo, Evans)
- Completely different field
- But well-formatted, coherent structure

---

## The Fix Needed

1. **Fail Fast on Empty Research**
   - If research sources = 0, raise exception immediately
   - Don't proceed to content generation

2. **Validate Research Context**
   - Ensure `research_context.topic` matches `request.topic`
   - Ensure at least 3 sources before proceeding

3. **Better Error Handling**
   - If research fails, store error in job
   - Don't generate content with empty context

4. **LLM Prompt Validation**
   - Check that research_evidence is not empty
   - If empty, fail before sending to LLM

---

## Next Steps

1. Check Cloud Run logs for the research phase
2. See why research discovery returned 0 sources
3. Fix the validation to prevent this
4. Consider adding topic validation in the prompt

---

**This is actually encouraging** - the generation pipeline works! We just need to ensure research is found before generating content.



