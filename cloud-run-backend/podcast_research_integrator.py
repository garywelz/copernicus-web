"""
Podcast Research Integrator - Brings the Spirit of Copernicus to Life
Integrates all research capabilities for authentic, paradigm-shifting podcast generation

This module coordinates:
- research_pipeline.py: Multi-API research discovery
- enhanced_research_service.py: Multi-paper analysis and synthesis  
- paper_processor.py: Deep paper analysis with Gemini
- copernicus_character.py: Character-driven prompting

The spirit of Copernicus: Revolutionary "delta" thinking, paradigm shifts,
interdisciplinary connections, rigorous evidence, accessible communication.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from research_pipeline import ComprehensiveResearchPipeline, ResearchSource
from enhanced_research_service import EnhancedResearchService, PaperAnalysis
from paper_processor import analyze_paper_with_gemini, ResearchPaper, AnalyzeOptions, PaperAnalysis as GeminiPaperAnalysis
from copernicus_character import get_copernicus_character, get_character_prompt, CopernicusCharacter
from utils.script_validation import calculate_minimum_words_for_duration

@dataclass
class PodcastResearchContext:
    """Complete research context for podcast generation"""
    topic: str
    research_sources: List[ResearchSource]
    paper_analyses: List[PaperAnalysis]
    paradigm_shifts: List[str]
    interdisciplinary_connections: List[str]
    key_findings: List[str]
    real_citations: List[str]
    research_quality_score: float
    recommended_expertise_level: str

class PodcastResearchIntegrator:
    """
    Integrates all research capabilities to create authentic Copernicus podcasts
    """
    
    def __init__(self, google_api_key: str):
        self.google_api_key = google_api_key
        self.research_pipeline = ComprehensiveResearchPipeline()
        self.enhanced_research_service = EnhancedResearchService(google_api_key)
        self.character = get_copernicus_character()
        
    async def comprehensive_research_for_podcast(
        self,
        topic: str,
        additional_context: str = "",
        source_links: List[str] = None,
        expertise_level: str = "intermediate",
        require_minimum_sources: int = 3
    ) -> PodcastResearchContext:
        """
        Perform comprehensive research following Copernicus philosophy:
        1. Discover research across multiple sources
        2. Analyze for paradigm shifts and revolutionary implications
        3. Find interdisciplinary connections
        4. Extract authentic citations and findings
        5. Assess research quality
        """
        
        print(f"🔬 COPERNICUS RESEARCH PIPELINE: {topic}")
        print(f"   Philosophy: Revolutionary delta thinking, paradigm shifts, evidence-based")
        
        # PHASE 1: RESEARCH DISCOVERY (Multi-API)
        print(f"\n📡 Phase 1: Research Discovery")
        research_sources = await self.research_pipeline.comprehensive_search(
            subject=topic,
            additional_context=additional_context,
            source_links=source_links or [],
            depth="comprehensive",
            include_preprints=True,
            include_social_trends=True  # Critical for current events like 3i/ATLAS
        )
        
        print(f"✅ Found {len(research_sources)} sources:")
        source_breakdown = {}
        for source in research_sources:
            source_breakdown[source.source] = source_breakdown.get(source.source, 0) + 1
        for source_type, count in source_breakdown.items():
            print(f"   - {source_type}: {count}")
        
        # VALIDATE: Minimum sources required
        if len(research_sources) < require_minimum_sources:
            raise Exception(
                f"Insufficient research for '{topic}': "
                f"Found {len(research_sources)} sources, need ≥{require_minimum_sources}. "
                f"Cannot generate authentic Copernicus content without rigorous research base."
            )
        
        # PHASE 2: MULTI-PAPER ANALYSIS (Paradigm Shifts & Connections)
        print(f"\n🧠 Phase 2: Multi-Paper Analysis & Synthesis")
        paper_analyses = await self.enhanced_research_service.analyze_multiple_papers(
            research_sources[:10],  # Top 10 most relevant
            complexity=expertise_level
        )
        
        print(f"✅ Analyzed {len(paper_analyses)} papers")
        
        # PHASE 3: DEEP ANALYSIS WITH GEMINI (for top papers)
        print(f"\n🔍 Phase 3: Deep Analysis with Gemini (top 3 papers)")
        gemini_analyses = []
        for i, source in enumerate(research_sources[:3]):
            print(f"   Analyzing: {source.title[:60]}...")
            paper = ResearchPaper(
                title=source.title,
                authors=source.authors,
                content=source.abstract,  # Use abstract for analysis
                abstract=source.abstract,
                doi=source.doi
            )
            options = AnalyzeOptions(
                focus_areas=["paradigm_shifts", "implications", "methodology"],
                analysis_depth="comprehensive",
                include_citations=True,
                paradigm_shift_analysis=True,
                interdisciplinary_connections=True
            )
            try:
                gemini_analysis = await analyze_paper_with_gemini(paper, options, self.google_api_key)
                gemini_analyses.append(gemini_analysis)
            except Exception as e:
                print(f"   ⚠️ Gemini analysis failed: {e}")
        
        # PHASE 4: SYNTHESIS (Extract Paradigm Shifts & Connections)
        print(f"\n🔗 Phase 4: Synthesis & Connection Analysis")
        
        paradigm_shifts = []
        interdisciplinary_connections = []
        key_findings = []
        real_citations = []
        
        # From enhanced research service analyses
        for analysis in paper_analyses:
            if analysis.paradigm_shift_potential not in ["none", "low"]:
                paradigm_shifts.append(f"{analysis.title}: {analysis.paradigm_shift_potential}")
            interdisciplinary_connections.extend(analysis.interdisciplinary_connections)
            key_findings.extend(analysis.key_findings)
        
        # From Gemini deep analyses
        for gemini_analysis in gemini_analyses:
            paradigm_shifts.extend(gemini_analysis.paradigm_shifts)
            interdisciplinary_connections.extend(gemini_analysis.interdisciplinary_connections)
            key_findings.extend(gemini_analysis.key_findings)
            real_citations.extend(gemini_analysis.citations)
        
        # Add citations from research sources
        for source in research_sources[:10]:
            if source.doi:
                citation = f"{', '.join(source.authors[:3])}{'et al.' if len(source.authors) > 3 else ''} ({source.publication_date[:4] if source.publication_date else 'Recent'}). {source.title}. DOI: {source.doi}"
                real_citations.append(citation)
            elif source.url:
                citation = f"{', '.join(source.authors[:3])}{'et al.' if len(source.authors) > 3 else ''} ({source.publication_date[:4] if source.publication_date else 'Recent'}). {source.title}. Available: {source.url}"
                real_citations.append(citation)
        
        # PHASE 5: QUALITY ASSESSMENT
        research_quality_score = self._assess_research_quality(
            research_sources, 
            paper_analyses,
            paradigm_shifts,
            interdisciplinary_connections
        )
        
        print(f"\n📊 Research Quality Score: {research_quality_score:.2f}/10")
        print(f"   - Paradigm Shifts Identified: {len(paradigm_shifts)}")
        print(f"   - Interdisciplinary Connections: {len(interdisciplinary_connections)}")
        print(f"   - Key Findings: {len(key_findings)}")
        print(f"   - Real Citations: {len(real_citations)}")
        
        # Recommend expertise level based on research complexity
        recommended_level = self._recommend_expertise_level(paper_analyses)
        
        return PodcastResearchContext(
            topic=topic,
            research_sources=research_sources,
            paper_analyses=paper_analyses,
            paradigm_shifts=paradigm_shifts[:10],  # Top 10
            interdisciplinary_connections=interdisciplinary_connections[:10],
            key_findings=key_findings[:15],
            real_citations=real_citations[:10],
            research_quality_score=research_quality_score,
            recommended_expertise_level=recommended_level
        )
    
    def _assess_research_quality(
        self,
        sources: List[ResearchSource],
        analyses: List[PaperAnalysis],
        paradigm_shifts: List[str],
        connections: List[str]
    ) -> float:
        """
        Assess research quality (0-10 scale) based on Copernicus criteria:
        - Source diversity and quality
        - Paradigm shift potential
        - Interdisciplinary connections
        - Peer-review status
        """
        score = 0.0
        
        # Source quality (0-3 points)
        if len(sources) >= 10:
            score += 2.0
        elif len(sources) >= 5:
            score += 1.0
        
        # Source diversity (0-2 points)
        unique_sources = len(set(s.source for s in sources))
        if unique_sources >= 3:
            score += 2.0
        elif unique_sources >= 2:
            score += 1.0
        
        # Paradigm shifts (0-2 points)
        if len(paradigm_shifts) >= 3:
            score += 2.0
        elif len(paradigm_shifts) >= 1:
            score += 1.0
        
        # Interdisciplinary connections (0-2 points)
        if len(connections) >= 5:
            score += 2.0
        elif len(connections) >= 2:
            score += 1.0
        
        # Recent research (0-1 point)
        recent_sources = sum(1 for s in sources if s.publication_date and "2024" in s.publication_date or "2023" in s.publication_date)
        if recent_sources >= 3:
            score += 1.0
        
        return min(score, 10.0)
    
    def _recommend_expertise_level(self, analyses: List[PaperAnalysis]) -> str:
        """Recommend expertise level based on research complexity"""
        if not analyses:
            return "intermediate"
        
        high_complexity_count = sum(1 for a in analyses if a.technical_complexity == "high")
        
        if high_complexity_count >= len(analyses) * 0.7:
            return "advanced"
        elif high_complexity_count >= len(analyses) * 0.3:
            return "intermediate"
        else:
            return "beginner"
    
    def build_2_speaker_research_prompt(
        self,
        research_context: PodcastResearchContext,
        duration: str,
        format_type: str,
        additional_instructions: str = "",
        host_voice_id: str = None,
        expert_voice_id: str = None
    ) -> str:
        """
        Build comprehensive 2-speaker prompt with all research context
        Embodies the spirit of Copernicus: paradigm shifts, evidence, accessibility
        
        Args:
            host_voice_id: ElevenLabs voice ID for host (determines speaker name)
            expert_voice_id: ElevenLabs voice ID for expert (determines speaker name)
        """
        
        # Map voice IDs to names (ElevenLabs voices)
        VOICE_ID_TO_NAME = {
            "XrExE9yKIg1WjnnlVkGX": "Matilda",  # Female, Professional
            "EXAVITQu4vr4xnSDxMaL": "Bella",     # Female, British (was swapped!)
            "JBFqnCBsd6RMkjVDRZzb": "Sam",       # Female, American
            "pNInz6obpgDQGcFmaJgB": "Adam",      # Male, Authoritative
            "pqHfZKP75CvOlQylNhV4": "Bryan",     # Male, American (was swapped!)
            "onwK4e9ZLuTAKqWW03F9": "Daniel"     # Male, British
        }
        
        # Determine speaker names from voice IDs
        host_name = VOICE_ID_TO_NAME.get(host_voice_id, "Matilda") if host_voice_id else "Matilda"
        expert_name = VOICE_ID_TO_NAME.get(expert_voice_id, "Adam") if expert_voice_id else "Adam"
        
        # Get character prompt
        character_prompt = get_character_prompt(self.character)
        
        # Build research evidence section
        research_evidence = self._format_research_evidence(research_context)
        
        prompt = f"""{character_prompt}

═══════════════════════════════════════════════════════════════
🎙️ PODCAST GENERATION: {research_context.topic}
═══════════════════════════════════════════════════════════════

**THE COPERNICUS SPIRIT:**
You are creating a podcast that embodies revolutionary "delta" thinking - 
challenging conventional understanding, highlighting paradigm shifts, finding 
interdisciplinary connections, and making cutting-edge research accessible.

**2-SPEAKER FORMAT:**
Your podcast has TWO speakers only:

1. **{host_name.upper()}** (Host/Interviewer)
   - Voice: {host_name}
   - Introduces topic, asks insightful questions
   - Represents curious, intelligent audience
   - Guides conversation to highlight revolutionary implications

2. **{expert_name.upper()}** (Research Expert)
   - Voice: {expert_name}
   - Explains research findings with evidence
   - Discusses paradigm shifts and implications
   - Cites actual papers and researchers

**CRITICAL RULES:**
- Use ONLY "{host_name.upper()}:" and "{expert_name.upper()}:" as speaker labels
- NO other names, titles, or speakers
- Names match the ElevenLabs voices selected by the user
- Create natural conversational flow
- Each speaker: 10-15 speaking turns
- Target duration: {duration}
- Format: {format_type}

**CONTENT LENGTH REQUIREMENTS - CRITICAL:**
- **MINIMUM REQUIRED: {calculate_minimum_words_for_duration(duration)} words** (based on 150 words per minute)
- **TARGET: {int(calculate_minimum_words_for_duration(duration) / 0.9)} words** for full duration coverage
- **FAILURE WARNING: Scripts under {calculate_minimum_words_for_duration(duration)} words will be REJECTED and generation will fail - ensure you meet or exceed this minimum**

**CITATION STYLE IN DIALOGUE:**
- When citing papers, mention: Author names, publication, and title
- DO NOT read out URLs, DOIs, or long links in the dialogue
- Instead say: "the link is in the description" or "we'll link to that in the description"
- Example: "According to Smith and colleagues in Nature, their 2024 study on quantum entanglement—link in the description—found that..."

═══════════════════════════════════════════════════════════════
📚 REAL RESEARCH EVIDENCE (YOU MUST USE THIS)
═══════════════════════════════════════════════════════════════

{research_evidence}

═══════════════════════════════════════════════════════════════
🎯 YOUR TASK
═══════════════════════════════════════════════════════════════

Create a compelling dialogue where MATILDA interviews ADAM about the actual 
research provided above. Focus on:

1. **Paradigm Shifts** - What revolutionary changes does this research represent?
2. **Evidence** - Cite specific papers, authors, findings from research above
3. **Connections** - Highlight interdisciplinary implications
4. **Accessibility** - Make complex concepts understandable without oversimplifying
5. **Future Impact** - Discuss what this means for the field and beyond

**DIALOGUE STRUCTURE:**

{host_name.upper()}: Welcome to Copernicus AI: Frontiers of Science. I'm {host_name}, and today 
we're exploring {research_context.topic}. {expert_name}, what makes this research so revolutionary?

{expert_name.upper()}: Thanks {host_name}. [Cites specific paper from research] This research represents 
a paradigm shift because [explain using actual findings]...

{host_name.upper()}: That's fascinating. [Asks probing question about implications]...

{expert_name.upper()}: [Answers with evidence, cites another paper]...

[Continue natural back-and-forth]

{host_name.upper()}: [Summarizes key insights] Thank you {expert_name} for breaking down this 
groundbreaking research. [Final thought on future implications]

{expert_name.upper()}: [Brief closing remark]

═══════════════════════════════════════════════════════════════

{additional_instructions}

**OUTPUT FORMAT (JSON):**
{{
    "title": "Engaging title closely matching '{research_context.topic}' - should directly reference the topic with compelling wording",
    "script": "Full dialogue script with {host_name.upper()}: and {expert_name.upper()}: labels",
    "description": "Comprehensive but CONCISE episode description (MUST be under 3000 characters) with:
        - Episode overview (1-2 paragraphs, concise)
        - Key concepts explored (3-4 bullet points, brief)
        - Research insights (1 paragraph citing actual papers)
        - Practical applications (1 paragraph, concise)
        - Future directions (1 paragraph, brief)
        - ## References section (list ALL citations with authors, titles, publications, DOIs/URLs)
        
        CRITICAL: Keep main content BRIEF to ensure References section is COMPLETE and under 3000 chars total
    ",
    "keywords": ["comma", "separated", "keywords", "from", "research"],
    "paradigm_shifts_discussed": ["list", "of", "paradigm", "shifts"],
    "citations_used": ["list", "of", "actual", "DOIs", "or", "URLs", "cited"]
}}

**CRITICAL:** Use ONLY the real research provided. DO NOT make up fake references.
If asked about something not in the research, ADAM should acknowledge the gap.
"""
        
        return prompt
    
    def _format_research_evidence(self, context: PodcastResearchContext) -> str:
        """Format all research evidence for prompt"""
        
        evidence = []
        
        # Top research sources
        evidence.append("**PRIMARY RESEARCH SOURCES:**\n")
        for i, source in enumerate(context.research_sources[:8], 1):
            evidence.append(f"{i}. **{source.title}**")
            evidence.append(f"   Authors: {', '.join(source.authors[:3])}{'et al.' if len(source.authors) > 3 else ''}")
            evidence.append(f"   Source: {source.source}")
            if source.doi:
                evidence.append(f"   DOI: {source.doi}")
            if source.url:
                evidence.append(f"   URL: {source.url}")
            evidence.append(f"   Published: {source.publication_date or 'Recent'}")
            evidence.append(f"   Abstract: {source.abstract[:300]}...")
            evidence.append("")
        
        # Paradigm shifts identified
        if context.paradigm_shifts:
            evidence.append("\n**PARADIGM SHIFTS IDENTIFIED:**")
            for shift in context.paradigm_shifts:
                evidence.append(f"- {shift}")
            evidence.append("")
        
        # Interdisciplinary connections
        if context.interdisciplinary_connections:
            evidence.append("\n**INTERDISCIPLINARY CONNECTIONS:**")
            for connection in context.interdisciplinary_connections:
                evidence.append(f"- {connection}")
            evidence.append("")
        
        # Key findings
        if context.key_findings:
            evidence.append("\n**KEY FINDINGS:**")
            for finding in context.key_findings[:10]:
                evidence.append(f"- {finding}")
            evidence.append("")
        
        # Real citations to use
        if context.real_citations:
            evidence.append("\n**REAL CITATIONS (Use these in your script and description):**")
            for citation in context.real_citations:
                evidence.append(f"- {citation}")
            evidence.append("")
        
        return "\n".join(evidence)

