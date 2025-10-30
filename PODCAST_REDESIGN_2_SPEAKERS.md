# 🎙️ Podcast Format Redesign: 2-Speaker System

**Date:** October 16, 2025  
**Change Request:** Simplify to 2 speakers with ElevenLabs voice names  
**Requester:** Gary Welz

---

## 🎯 New Podcast Format

### Speakers (2 Only)

**1. Matilda** (Female Host/Interviewer)
- **ElevenLabs Voice ID:** `XrExE9yKIg1WjnnlVkGX`
- **Role:** Host and interviewer, asks questions, guides conversation
- **Character:** Warm, engaging, curious, represents the audience perspective
- **Voice Description:** Professional female voice

**2. Adam** (Male Expert)
- **ElevenLabs Voice ID:** `pNInz6obpgDQGcFmaJgB`
- **Role:** Research expert, explains concepts, provides insights
- **Character:** Knowledgeable, authoritative but approachable, researcher
- **Voice Description:** Authoritative male voice

### Format Structure

```
MATILDA: [Introduces topic, sets context, asks questions]
ADAM: [Explains research, provides technical details, answers questions]
MATILDA: [Follow-up questions, clarifications, audience perspective]
ADAM: [Deeper dive, implications, future directions]
MATILDA: [Summary, final thoughts]
```

---

## 🔧 Implementation Changes

### 1. Update Voice Configurations

**File:** `cloud-run-backend/main.py`

```python
# NEW 2-speaker configuration
COPERNICUS_VOICES = {
    "matilda": {
        "voice_id": "XrExE9yKIg1WjnnlVkGX",
        "role": "host",
        "gender": "female",
        "description": "Professional host, warm and engaging"
    },
    "adam": {
        "voice_id": "pNInz6obpgDQGcFmaJgB", 
        "role": "expert",
        "gender": "male",
        "description": "Expert researcher, authoritative but approachable"
    }
}

def get_speaker_labels():
    """Return the 2 speaker labels used in scripts"""
    return ["MATILDA", "ADAM"]
```

### 2. Update Prompt Templates

**Old Format (3+ speakers):**
```python
prompt = """Create a natural dialogue between HOST, EXPERT, and QUESTIONER..."""
```

**New Format (2 speakers):**
```python
prompt = f"""Create a natural research dialogue between two speakers:

**MATILDA** (Host/Interviewer):
- Introduces the topic
- Asks insightful questions
- Represents audience curiosity
- Guides the conversation
- Summarizes key points

**ADAM** (Research Expert):
- Explains the research findings
- Provides technical details from the actual papers
- Answers questions with evidence
- Discusses implications and future directions

**CRITICAL RULES:**
- Use ONLY "MATILDA:" and "ADAM:" as speaker labels
- NO titles, NO surnames, NO other names
- These names match the ElevenLabs voices exactly
- Matilda is female, Adam is male - voices will match
- Create natural back-and-forth dialogue
- Each speaker should have 10-15 speaking turns
- Target duration: {request.duration}

**RESEARCH SOURCES PROVIDED:**
{research_context}

Generate a script that discusses the ACTUAL research above.
MATILDA: Welcome to Copernicus AI! Today we're exploring {topic}. Adam, what makes this research so exciting?
ADAM: Thanks Matilda. The latest findings show...
[Continue natural dialogue]
"""
```

### 3. Update Script Parsing

**File:** `cloud-run-backend/main.py`

```python
def parse_script_for_audio(script: str) -> List[Dict]:
    """Parse script into audio segments for 2-speaker format"""
    segments = []
    
    # Split by speaker labels
    lines = script.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match MATILDA: or ADAM: labels
        if line.startswith('MATILDA:'):
            text = line.replace('MATILDA:', '').strip()
            segments.append({
                'speaker': 'matilda',
                'text': text,
                'voice_id': COPERNICUS_VOICES['matilda']['voice_id']
            })
        elif line.startswith('ADAM:'):
            text = line.replace('ADAM:', '').strip()
            segments.append({
                'speaker': 'adam',
                'text': text,
                'voice_id': COPERNICUS_VOICES['adam']['voice_id']
            })
    
    return segments
```

### 4. Update All Prompt Generation Functions

Files to modify:
- `generate_topic_research_content()` - Line 622
- `generate_topic_research_content_vertex()` - Line 882
- `generate_podcast_from_analysis()` - Line 479
- `generate_podcast_from_analysis_vertex()` - Line 777

Replace all 3-speaker references with 2-speaker format:
- `HOST` → `MATILDA`
- `EXPERT` → `ADAM`
- Remove `QUESTIONER` entirely

### 5. Update Character Configuration

**File:** `cloud-run-backend/copernicus_character.py`

```python
def get_copernicus_character():
    """Get Copernicus AI character configuration for 2-speaker format"""
    return {
        "name": "Copernicus AI",
        "show_title": "Copernicus AI: Frontiers of Science",
        "speakers": {
            "matilda": {
                "name": "Matilda",
                "voice_id": "XrExE9yKIg1WjnnlVkGX",
                "role": "host",
                "personality": "Warm, curious, engaging interviewer"
            },
            "adam": {
                "name": "Adam",
                "voice_id": "pNInz6obpgDQGcFmaJgB",
                "role": "expert",
                "personality": "Knowledgeable researcher, clear communicator"
            }
        },
        "structure": [
            "MATILDA introduces the topic and today's focus",
            "ADAM provides context and background from research",
            "MATILDA asks about key findings and methodology",
            "ADAM explains technical details with examples",
            "MATILDA probes implications and applications",
            "ADAM discusses future directions and open questions",
            "MATILDA summarizes and thanks Adam for insights"
        ],
        "format": "10-20 minute research dialogue",
        "style": "Professional but accessible, evidence-based discussions"
    }
```

---

## 🔬 Integration with Research Pipeline

### New Workflow

```python
async def run_podcast_generation_job(job_id: str, request: PodcastRequest, subscriber_id: Optional[str] = None):
    """Generate research-driven podcast with 2-speaker format"""
    
    # STEP 1: PERFORM REAL RESEARCH
    print(f"🔍 Step 1: Researching topic: {request.topic}")
    research_pipeline = ComprehensiveResearchPipeline()
    
    research_sources = await research_pipeline.comprehensive_search(
        subject=request.topic,
        additional_context=request.additional_instructions or "",
        source_links=request.source_links,
        depth="comprehensive",
        include_preprints=True,
        include_social_trends=True
    )
    
    print(f"📚 Found {len(research_sources)} research sources")
    
    # STEP 2: VALIDATE RESEARCH
    if len(research_sources) < 3:
        error_msg = f"Insufficient research sources ({len(research_sources)}). Need at least 3 quality sources for {request.topic}."
        print(f"❌ {error_msg}")
        
        # Update job status to failed
        job_ref.update({
            'status': 'failed',
            'error': error_msg,
            'error_type': 'insufficient_research',
            'updated_at': datetime.utcnow().isoformat()
        })
        raise Exception(error_msg)
    
    # STEP 3: GENERATE CONTENT FROM REAL RESEARCH
    print(f"🎙️ Step 2: Generating 2-speaker podcast from research")
    content = await generate_content_from_research(request, research_sources)
    
    # STEP 4: PARSE SCRIPT FOR 2 SPEAKERS
    print(f"🔊 Step 3: Parsing script for Matilda and Adam")
    segments = parse_script_for_audio(content['script'])
    
    print(f"✅ Script has {len(segments)} segments")
    matilda_count = sum(1 for s in segments if s['speaker'] == 'matilda')
    adam_count = sum(1 for s in segments if s['speaker'] == 'adam')
    print(f"   - Matilda: {matilda_count} segments")
    print(f"   - Adam: {adam_count} segments")
    
    # STEP 5: GENERATE AUDIO WITH ELEVENLABS
    print(f"🎵 Step 4: Generating audio with ElevenLabs")
    audio_url = await generate_multi_speaker_audio(segments, canonical_filename)
    
    # ... rest of pipeline
```

### Generate Content from Research

```python
async def generate_content_from_research(request: PodcastRequest, research_sources: List[ResearchSource]) -> dict:
    """Generate 2-speaker podcast content from real research"""
    
    # Build research context from REAL papers
    research_context = "\n\n".join([
        f"**Paper {i+1}: {source.title}**\n"
        f"Authors: {', '.join(source.authors[:3])}{'...' if len(source.authors) > 3 else ''}\n"
        f"Published: {source.publication_date}\n"
        f"Source: {source.source}\n"
        f"DOI: {source.doi or 'N/A'}\n"
        f"Abstract: {source.abstract[:500]}...\n"
        for i, source in enumerate(research_sources[:10])
    ])
    
    prompt = f"""You are creating a Copernicus AI podcast with 2 speakers about {request.topic}.

**THE TWO SPEAKERS:**

MATILDA (Host/Interviewer):
- Introduces the topic and asks questions
- Represents the curious, intelligent audience
- Guides the conversation naturally
- Female voice on ElevenLabs

ADAM (Research Expert):
- Explains the actual research findings provided below
- Answers MATILDA's questions with evidence from the papers
- Discusses implications and future directions
- Male voice on ElevenLabs

**REAL RESEARCH SOURCES YOU MUST USE:**
{research_context}

**YOUR TASK:**
Create a natural 2-person dialogue where MATILDA interviews ADAM about the research above.

**CRITICAL REQUIREMENTS:**
1. Use ONLY "MATILDA:" and "ADAM:" as speaker labels
2. NO other names, NO titles, NO surnames
3. Cite ONLY the real papers, authors, and DOIs provided above
4. DO NOT make up fake references
5. If asked about something not in the research, ADAM should acknowledge the gap
6. Target duration: {request.duration}
7. Expertise level: {request.expertise_level}
8. Each speaker should have 10-15 speaking turns
9. Make it conversational but information-dense

**EXAMPLE FORMAT:**
MATILDA: Welcome to Copernicus AI! I'm Matilda, and today we're diving into {request.topic}. Adam, thanks for joining me. What's the latest research telling us?

ADAM: Thanks for having me, Matilda. The most exciting development comes from [cite actual paper from research above]...

MATILDA: That's fascinating. Can you explain what [specific concept from the paper] means for...

[Continue natural back-and-forth]

Return JSON with:
{{
    "title": "Engaging title about {request.topic}",
    "script": "Full dialogue script with MATILDA: and ADAM: labels",
    "description": "Comprehensive episode description with real references from the research above",
    "references": [list of actual DOIs/URLs from the research sources]
}}
"""
    
    # Call LLM (Vertex AI or Google AI)
    if vertex_ai_model:
        return await call_vertex_ai(prompt)
    else:
        google_key = get_google_api_key()
        return await call_google_ai(prompt, google_key)
```

---

## ✅ Benefits of 2-Speaker Format

1. **No Voice-Name Confusion** - Names match ElevenLabs voices exactly
2. **Simpler Scripts** - Easier for LLM to generate natural dialogue
3. **Clear Roles** - Matilda asks, Adam explains
4. **Better Flow** - Interview format is more natural than 3-4 way conversation
5. **Cost Effective** - Fewer voice synthesis calls
6. **Quality Control** - Easier to validate script structure

---

## 🧪 Testing Checklist

After implementation, test with:

### Test 1: 3i/ATLAS Comet
- **Expected:** Adam explains latest NASA ADS papers about the comet
- **Expected:** Matilda asks about its trajectory, composition, significance
- **Validate:** Real DOIs from arXiv/NASA ADS papers
- **Validate:** Male voice for Adam, female voice for Matilda

### Test 2: CRISPR Gene Editing
- **Expected:** Adam cites Doudna/Charpentier Nobel work
- **Expected:** Matilda asks about applications and ethical considerations
- **Validate:** Real references to Nature, Science publications

### Test 3: Obscure Topic (Should Fail)
- **Topic:** "Quantum Flibbertigibbet Theory"
- **Expected:** Job fails with "Insufficient research sources" error
- **Validate:** NO fake content generated

---

## 📊 Implementation Timeline

### Phase 1: Core Changes (2-3 hours)
- [ ] Update voice configurations to 2-speaker model
- [ ] Modify all prompt templates
- [ ] Update script parsing for MATILDA/ADAM labels
- [ ] Remove fake fallback template

### Phase 2: Research Integration (2-3 hours)
- [ ] Import research_pipeline.py
- [ ] Add research validation
- [ ] Integrate research sources into content generation
- [ ] Add proper error handling

### Phase 3: Testing & Deployment (1-2 hours)
- [ ] Test with 3i/ATLAS
- [ ] Test with established science topics
- [ ] Test failure cases
- [ ] Deploy to Cloud Run

**Total Estimated Time:** 5-8 hours

---

*This redesign addresses both the quality issues (fake research) and the voice-name confusion by simplifying to 2 speakers whose names match their ElevenLabs voices exactly.*

