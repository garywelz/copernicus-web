# Fix for Topic Mismatch Bug

## Summary

The podcast about "number theory" generated content about "neuro anatomy" because:
1. Research discovery returned 0 sources
2. Empty research_context was passed to content generation
3. LLM hallucinated content without real research

## Root Cause

The `research_context` object is empty, which means either:
- Research discovery failed but exception wasn't raised
- Research context serialization failed
- Empty context was passed through validation

## The Fix

We need to add validation at multiple points:

### 1. Add Validation After Research Context Creation

In `generate_content_from_research_context()`:

```python
# Validate research context before building prompt
if not research_context or len(research_context.research_sources) == 0:
    raise Exception(f"No research sources found for topic: {request.topic}. Cannot generate content without research.")
    
if not research_context.topic or research_context.topic != request.topic:
    raise Exception(f"Research context topic mismatch. Expected: {request.topic}, Got: {research_context.topic}")
```

### 2. Check Research Evidence Before Sending to LLM

```python
research_evidence = self._format_research_evidence(research_context)
if not research_evidence or len(research_evidence.strip()) < 100:
    raise Exception(f"Insufficient research evidence for topic: {request.topic}. Cannot generate authentic content.")
```

### 3. Log Research Context Before Prompt Building

Add detailed logging to see what's actually in the research_context when building the prompt.

---

## Immediate Action

Check Cloud Run logs for the job to see:
1. What research sources were found (should show 0)
2. Why the exception wasn't raised
3. What prompt was actually sent to the LLM

---

**Next:** Let me create a fix that adds these validations.



