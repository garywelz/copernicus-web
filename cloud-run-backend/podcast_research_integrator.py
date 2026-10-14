"""
Podcast Research Integrator - Brings the Spirit of Copernicus to Life
Integrates all research capabilities for evidence-based podcast generation

This module coordinates:
- research_pipeline.py: Multi-API research discovery
- enhanced_research_service.py: Multi-paper analysis and synthesis  
- paper_processor.py: Deep paper analysis with Gemini
- copernicus_character.py: Character-driven prompting

The spirit of Copernicus: what the research changes in how we see a question (the "delta"), stated plainly and only as far as the papers
support, interdisciplinary connections, rigorous evidence, accessible communication.
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field

from research_pipeline import ComprehensiveResearchPipeline, ResearchSource
from enhanced_research_service import EnhancedResearchService, PaperAnalysis
from paper_processor import analyze_paper_with_gemini, ResearchPaper, AnalyzeOptions, PaperAnalysis as GeminiPaperAnalysis
from copernicus_character import get_copernicus_character, get_character_prompt, CopernicusCharacter
from utils.script_validation import calculate_minimum_words_for_duration, calculate_maximum_words_for_duration
from attribution_check import MAX_ABSTRACT_CHARS
from relevance_gate import RELEVANCE_THRESHOLD, apply_gate, outside_zenodo, relevance_scores
from paper_confirmation import (
    confirm_sources, confirm_requested_paper, as_research_source, format_citation_line, InsufficientConfirmedPapers,
    PaperNotConfirmed, Dropped,
)

def aggregate_enhanced_analyses(paper_analyses: List["PaperAnalysis"], pid_by_title: Optional[Dict[str, str]] = None):
    """Fold a list of PaperAnalysis into (significance,
    interdisciplinary_connections, key_findings).

    B5 fix: skips any analysis with analysis_failed=True (the generic
    placeholder object enhanced_research_service._create_fallback_analysis
    returns when AI processing failed for that paper) entirely -- none of
    its placeholder text ("Research findings require further analysis",
    significance="unknown") is allowed to reach the model or
    a published description.
    """
    significance: List[str] = []
    interdisciplinary_connections: List[str] = []
    key_findings: List[str] = []
    for analysis in paper_analyses:
        if getattr(analysis, "analysis_failed", False):
            continue
        # Gap 3 fix 1 (C4): findings carry the P number of the confirmed paper they came from, so the generator can
        # name the right paper (and, with fix 3, put a marker on the claim).
        tag = f"[{pid_by_title[analysis.title]}] " if pid_by_title and analysis.title in pid_by_title else ""
        if (analysis.significance or "").strip().lower() not in ("", "none", "none stated", "unknown"):
            significance.append(f"{tag}{analysis.title}: {analysis.significance}")
        interdisciplinary_connections.extend(analysis.interdisciplinary_connections)
        key_findings.extend(f"{tag}{f}" for f in analysis.key_findings)
    return significance, interdisciplinary_connections, key_findings


def format_real_citation_line(source: ResearchSource) -> Optional[str]:
    """One line for the 'REAL CITATIONS' evidence block shown to the model.

    B1/B2 fix: never fabricate a DOI or a year. Omit the DOI field
    entirely when source.doi is empty (falling back to Available: URL,
    exactly as before) instead of ever writing a placeholder-shaped DOI;
    omit the year parenthetical entirely when source.publication_date is
    unknown instead of substituting the literal string "Recent" -- the
    model was being told to "use these in your script and description",
    so a literal "(Recent)" here was copied verbatim into published text.

    Returns None (no citation line) when neither a DOI nor a URL is known,
    matching the original if/elif behavior.
    """
    author_str = ', '.join(source.authors[:3]) + ('et al.' if len(source.authors) > 3 else '')
    year = source.publication_date[:4] if source.publication_date else ''
    year_part = f" ({year})" if year else ""
    base = f"{author_str}{year_part}. {source.title}"
    if source.doi:
        return f"{base}. DOI: {source.doi}"
    elif source.url:
        return f"{base}. Available: {source.url}"
    return None


@dataclass
class PodcastResearchContext:
    """Complete research context for podcast generation"""
    topic: str
    research_sources: List[ResearchSource]
    paper_analyses: List[PaperAnalysis]
    significance: List[str]  # what the analyses say the papers change in how we see the question (neutral notes, may be empty)
    interdisciplinary_connections: List[str]
    key_findings: List[str]
    real_citations: List[str]
    research_quality_score: float
    recommended_expertise_level: str
    # Gap 3 fix 1: the confirmed papers (ConfirmedPaper records, P1..Pn), what was dropped and why, and which one
    # (if any) is the directly requested paper. research_sources is built from confirmed_papers.
    confirmed_papers: List[Any] = field(default_factory=list)
    dropped_candidates: List[Any] = field(default_factory=list)
    relevance_scores: Dict[str, float] = field(default_factory=dict)  # similarity of every confirmed paper to the topic (fix 1b)
    confirmation_stats: Dict[str, Any] = field(default_factory=dict)  # registry requests made by confirmation; records reused from search
    requested_pid: Optional[str] = None

class PodcastResearchIntegrator:
    """
    Integrates all research capabilities to create authentic Copernicus podcasts
    """
    
    def __init__(self, google_api_key: str, embed_batch=None):
        self.google_api_key = google_api_key
        self.embed_batch = embed_batch  # relevance gate: texts -> vectors; None means the OpenAI embedding service
        self.research_pipeline = ComprehensiveResearchPipeline()
        if google_api_key:  # fix 4 (i): a model proposes the focused arXiv queries; without a key the fallback in search_queries is used
            from named_work_check import make_gemini_llm_call
            self.research_pipeline.query_llm = make_gemini_llm_call(google_api_key)
        self.enhanced_research_service = EnhancedResearchService(google_api_key)
        self.character = get_copernicus_character()
        
    async def comprehensive_research_for_podcast(
        self,
        topic: str,
        additional_context: str = "",
        source_links: List[str] = None,
        expertise_level: str = "intermediate",
        require_minimum_sources: int = 3,
        required_paper: Optional[Dict[str, Any]] = None
    ) -> PodcastResearchContext:
        """
        Perform comprehensive research following Copernicus philosophy:
        1. Discover research across multiple sources
        2. Analyze what each paper shows and what it says it changes in how we see the question
        3. Find interdisciplinary connections
        4. Extract authentic citations and findings
        5. Assess research quality
        """
        
        print(f"🔬 COPERNICUS RESEARCH PIPELINE: {topic}")
        print(f"   Philosophy: the delta, stated plainly and only as far as the papers support; evidence-based")
        
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
        
        # Gap 3 fix 1 (C1/C7): only papers confirmed in their registry by identifier go any further. A directly requested
        # paper must itself be confirmed (PaperNotConfirmed) and becomes P1. Fewer than ``require_minimum_sources``
        # confirmed papers fails the episode before any generation (InsufficientConfirmedPapers); an unreachable
        # registry raises RegistryUnavailable instead, so an outage is not mistaken for a thin topic.
        required = None
        if required_paper and required_paper.get("title"):
            required = await confirm_requested_paper(required_paper.get("doi"), required_paper["title"])
        found = len(research_sources) + (1 if required else 0)  # candidates found, counting the requested paper
        confirmation = await confirm_sources(research_sources, required_first=required)
        print(f"   Confirmed {len(confirmation.confirmed)} of {found} candidates; dropped: {confirmation.drop_counts()}")
        if len(confirmation.confirmed) < require_minimum_sources:
            raise InsufficientConfirmedPapers(topic, found, len(confirmation.confirmed), require_minimum_sources, confirmation.drop_counts(),
                                              [d.to_dict() for d in confirmation.dropped])

        # Fix 1b (b): a confirmed paper must also be about the topic. Papers scoring below RELEVANCE_THRESHOLD against the
        # topic are dropped (a directly requested paper is exempt), and at least ``require_minimum_sources`` of the kept
        # papers must come from arXiv, PubMed or Crossref: Zenodo records do not count toward the minimum.
        scores = await relevance_scores(f"{topic} {additional_context}".strip(), confirmation.confirmed, self.embed_batch)
        kept, off_topic = apply_gate(confirmation.confirmed, scores, exempt_pids=["P1"] if required else [])
        if off_topic:
            print(f"   Dropped {len(off_topic)} off-topic paper(s) (similarity below {RELEVANCE_THRESHOLD}): "
                  + "; ".join(f"{d.title[:50]} ({d.score})" for d in off_topic))

        def check_minimums(papers) -> None:
            counts: Dict[str, int] = {}
            for d in dropped_list:
                counts[d.reason] = counts.get(d.reason, 0) + 1
            outside = outside_zenodo(papers)
            if len(papers) < require_minimum_sources or outside < require_minimum_sources:
                raise InsufficientConfirmedPapers(topic, found, len(papers), require_minimum_sources, counts,
                                                  [d.to_dict() for d in dropped_list], outside_zenodo=outside)

        confirmed_list = list(kept)
        dropped_list = list(confirmation.dropped) + off_topic
        check_minimums(confirmed_list)
        research_sources = [as_research_source(c) for c in confirmed_list]
        pid_by_title = {c.title: c.pid for c in confirmed_list}

        # A paper whose analysis failed to parse holds only placeholder text. It is dropped here, before any prompt is built
        # (it stays out of the evidence block, the References and Further reading); if that leaves fewer than the minimum,
        # the episode fails through the same path as too few confirmed papers.

        def drop_failed(failed_pids: Set[str]) -> None:
            nonlocal research_sources, confirmed_list
            if not failed_pids:
                return
            if required and "P1" in failed_pids:
                raise PaperNotConfirmed("The requested paper's analysis could not be parsed, so it cannot be used for this episode.")
            for c in confirmed_list:
                if c.pid in failed_pids:
                    dropped_list.append(Dropped(c.title, "analysis_failed", dict(c.ids or {})))
            confirmed_list = [c for c in confirmed_list if c.pid not in failed_pids]
            research_sources = [x for x in research_sources if x.pid not in failed_pids]
            print(f"   Dropped {len(failed_pids)} paper(s) whose analysis could not be parsed; {len(confirmed_list)} remain")
            check_minimums(confirmed_list)

        # PHASE 2: MULTI-PAPER ANALYSIS (Paradigm Shifts & Connections)
        print(f"\n🧠 Phase 2: Multi-Paper Analysis & Synthesis")
        paper_analyses = await self.enhanced_research_service.analyze_multiple_papers(
            research_sources[:10],  # Top 10 most relevant
            complexity=expertise_level
        )
        
        analysed = research_sources[:10]
        drop_failed({s.pid for s, a in zip(analysed, paper_analyses) if getattr(a, "analysis_failed", False)})
        kept = {s.pid for s in research_sources}
        paper_analyses = [a for s, a in zip(analysed, paper_analyses) if s.pid in kept]
        analysed = [s for s in analysed if s.pid in kept]

        print(f"✅ Analyzed {len(paper_analyses)} papers")
        
        # PHASE 3: DEEP ANALYSIS WITH GEMINI (for top papers)
        print(f"\n🔍 Phase 3: Deep Analysis with Gemini (top 3 papers)")
        gemini_analyses = []
        gemini_pids = []
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
                focus_areas=["significance", "implications", "methodology"],
                analysis_depth="comprehensive",
                include_citations=True,
                significance_analysis=True,
                interdisciplinary_connections=True
            )
            try:
                gemini_analysis = await analyze_paper_with_gemini(paper, options, self.google_api_key)
                gemini_analyses.append(gemini_analysis)
                gemini_pids.append(source.pid)
            except Exception as e:
                print(f"   ⚠️ Gemini analysis failed: {e}")
        
        drop_failed({p for g, p in zip(gemini_analyses, gemini_pids) if getattr(g, "analysis_failed", False)})
        kept = {s.pid for s in research_sources}
        paper_analyses = [a for s, a in zip(analysed, paper_analyses) if s.pid in kept]
        pairs = [(g, p) for g, p in zip(gemini_analyses, gemini_pids) if p in kept]
        gemini_analyses, gemini_pids = [g for g, _ in pairs], [p for _, p in pairs]

        # PHASE 4: SYNTHESIS (significance notes & connections)
        print(f"\n🔗 Phase 4: Synthesis & Connection Analysis")
        
        real_citations = []

        # From enhanced research service analyses (B5 fix: excludes failed
        # analyses -- see aggregate_enhanced_analyses's docstring)
        significance, interdisciplinary_connections, key_findings = \
            aggregate_enhanced_analyses(paper_analyses, pid_by_title)

        # From Gemini deep analyses
        for gemini_analysis, gpid in zip(gemini_analyses, gemini_pids):
            significance.extend(f"[{gpid}] {x}" for x in gemini_analysis.significance)
            interdisciplinary_connections.extend(gemini_analysis.interdisciplinary_connections)
            key_findings.extend(f"[{gpid}] {x}" for x in gemini_analysis.key_findings)
            # (C2) gemini_analysis.citations -- model-written citation strings -- are no longer used anywhere.

        # (C2) Reference lines are built by code from the confirmed registry records only. This list is the interim
        # source for the existing description fallback until C6 replaces it with the code-built References section.
        real_citations = [format_citation_line(c) for c in confirmed_list[:10]]

        # PHASE 5: QUALITY ASSESSMENT
        research_quality_score = self._assess_research_quality(
            research_sources, 
            paper_analyses,
            significance,
            interdisciplinary_connections
        )
        
        print(f"\n📊 Research Quality Score: {research_quality_score:.2f}/10")
        print(f"   - Significance notes: {len(significance)}")
        print(f"   - Interdisciplinary Connections: {len(interdisciplinary_connections)}")
        print(f"   - Key Findings: {len(key_findings)}")
        print(f"   - Real Citations: {len(real_citations)}")
        
        # Recommend expertise level based on research complexity
        recommended_level = self._recommend_expertise_level(paper_analyses)
        
        return PodcastResearchContext(
            topic=topic,
            research_sources=research_sources,
            paper_analyses=paper_analyses,
            significance=significance[:10],  # Top 10
            interdisciplinary_connections=interdisciplinary_connections[:10],
            key_findings=key_findings[:15],
            real_citations=real_citations[:10],
            confirmed_papers=confirmed_list,
            dropped_candidates=dropped_list,
            confirmation_stats=dict(getattr(confirmation, "stats", {}) or {}),
            relevance_scores=dict(scores),
            requested_pid="P1" if required else None,
            research_quality_score=research_quality_score,
            recommended_expertise_level=recommended_level
        )
    
    def _assess_research_quality(
        self,
        sources: List[ResearchSource],
        analyses: List[PaperAnalysis],
        significance: List[str],
        connections: List[str]
    ) -> float:
        """
        Assess research quality (0-10 scale) based on Copernicus criteria:
        - Source diversity and quality
        - Significance notes
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
        
        # Significance notes (0-2 points)
        if len(significance) >= 3:
            score += 2.0
        elif len(significance) >= 1:
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
        expert_voice_id: str = None,
        source_paper_citation: str = "",
    ) -> str:
        """
        Build comprehensive 2-speaker prompt with all research context
        Embodies the spirit of Copernicus: the delta without hype, evidence, accessibility
        
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
        
        source_paper_block = ""
        if source_paper_citation:
            source_paper_block = f"""
**SOURCE PAPER (this episode is about this paper — cite it by journal, not PubMed/arXiv):**
{source_paper_citation}
PubMed and arXiv are indexes, not journals. If a journal name is present, say that journal. Never say "published in PubMed" or "published in arXiv".
"""

        prompt = f"""{character_prompt}

═══════════════════════════════════════════════════════════════
🎙️ PODCAST GENERATION: {research_context.topic}
═══════════════════════════════════════════════════════════════

**THE COPERNICUS SPIRIT:**
You are creating a podcast that keeps the "delta" idea without hype: what this research changes in how we see the question,
stated plainly and only as far as the papers support, with the interdisciplinary connections they show, and making current
research accessible.

**2-SPEAKER FORMAT:**
Your podcast has TWO speakers only:

1. **{host_name.upper()}** (Host/Interviewer)
   - Voice: {host_name}
   - Introduces topic, asks insightful questions
   - Represents curious, intelligent audience
   - Guides the conversation to what the papers show and what they leave open

2. **{expert_name.upper()}** (Research Expert)
   - Voice: {expert_name}
   - Explains research findings with evidence
   - Discusses the findings and what they imply, with the papers' own caveats
   - Cites actual papers and researchers

**CRITICAL RULES:**
- Use ONLY "{host_name.upper()}:" and "{expert_name.upper()}:" as speaker labels
- NO other names, titles, or speakers
- Names match the ElevenLabs voices selected by the user
- Create natural conversational flow
- Each speaker: 10-15 speaking turns
- Target duration: {duration}
- Format: {format_type}

**CONTENT LENGTH REQUIREMENTS - ABSOLUTELY CRITICAL:**
- **MINIMUM REQUIRED: {calculate_minimum_words_for_duration(duration)} words** (based on 150 words per minute)
- **TARGET: {int(calculate_minimum_words_for_duration(duration) / 0.8)} words** for full duration coverage
- **MANDATORY: Your script MUST be at least {calculate_minimum_words_for_duration(duration)} words long**
- **FAILURE WARNING: Scripts under {calculate_minimum_words_for_duration(duration)} words will be REJECTED and generation will fail - ensure you meet or exceed this minimum**
- **MAXIMUM: {calculate_maximum_words_for_duration(duration)} words.** The audio must stay within the requested length; a script over this maximum is REJECTED and must be shortened.
- **WORD COUNT CHECK: Before submitting, count the words in your script. If it's under {calculate_minimum_words_for_duration(duration)} words, you MUST expand it with more dialogue, examples, and detailed explanations.**

**CITATION STYLE IN DIALOGUE:**
- You may name ONLY the papers in the numbered list below ([P1], [P2], ...), by their authors and year, in speech.
  Do NOT name, quote or allude to any other paper, author or study, even if you know it. If the list lacks something you
  need, say it is outside what was reviewed. Do not name a paper you do not discuss.
- When you cite a listed paper, mention the first author's surname (and "and colleagues" or the second author), the year and, if the list gives a journal, the journal.
- DO NOT read out URLs, DOIs, or long links in the dialogue
- Say "the link is in the description" ONLY right after naming a paper from the list, never otherwise.
- Example of the form (use only listed papers): "According to <first author> and colleagues in <journal from the list>, their <year> study—link in the description—found that..."
- NEVER say "published in PubMed" or "published in arXiv". Those are indexes. Use the journal name from the source list. If no journal is given, name the authors and year only.

═══════════════════════════════════════════════════════════════
📚 REAL RESEARCH EVIDENCE (YOU MUST USE THIS)
═══════════════════════════════════════════════════════════════

{source_paper_block}
{research_evidence}

═══════════════════════════════════════════════════════════════
🎯 YOUR TASK
═══════════════════════════════════════════════════════════════

Create a clear, well-paced dialogue where MATILDA interviews ADAM about the actual 
research provided above. Focus on:

1. **The question** - What do the listed papers actually show about "{research_context.topic}"? Answer the specific question asked, not the field in general. Use plain, neutral wording for every finding; report what the papers found.
2. **Evidence** - Cite specific papers, authors, findings from research above
3. **Connections** - Note interdisciplinary connections the papers themselves make
4. **Accessibility** - Make complex concepts understandable without oversimplifying
5. **What is still open** - Say what the papers leave unresolved or suggest as next steps; do not predict impact beyond what they claim

**DIALOGUE STRUCTURE:**

{host_name.upper()}: Welcome to Copernicus AI: Frontiers of Science. I'm {host_name}, and today 
we're exploring {research_context.topic}. {expert_name}, what do the papers reviewed here tell us about it?

{expert_name.upper()}: Thanks {host_name}. [Cites specific paper from research] This research matters 
because [explain using actual findings]...

{host_name.upper()}: I see. [Asks a probing question about what the papers show or leave open]...

{expert_name.upper()}: [Answers with evidence, cites another paper]...

[Continue natural back-and-forth]

{host_name.upper()}: [Summarizes key insights] Thank you {expert_name} for breaking down this 
research. [Final thought on what is still open]

{expert_name.upper()}: [Brief closing remark]

═══════════════════════════════════════════════════════════════

{additional_instructions}

**OUTPUT FORMAT (JSON):**
{{
    "title": "A clear, specific title that closely matches '{research_context.topic}' and says what the papers examine; no superlatives or promotional wording",
    "script": "Full dialogue script with {host_name.upper()}: and {expert_name.upper()}: labels. **CRITICAL: This script MUST be at least {calculate_minimum_words_for_duration(duration)} words long. Count the words before submitting. If under {calculate_minimum_words_for_duration(duration)} words, expand it with more dialogue, examples, and detailed explanations until it reaches the minimum.**",
    "description": "Episode description, SHORT: 1500-2200 characters in total (it shares a 4000-character limit with the reference list, so a longer description is cut) with:
        - Opening overview: 2 short paragraphs saying what the episode covers, what question it asks and what the papers found. Say only what the papers support: no claims about importance or impact that they do not make. NO section header - just start with the content directly.
        - Key concepts explored: 4 bullet points, one or two sentences each
        - Research insights: 1 paragraph about what the papers found, their methods, and what they leave open
        - Practical applications: 1 short paragraph on the uses the papers themselves describe; if they describe none, say that the papers do not discuss applications
        - Future directions: 1 short paragraph about the directions the papers themselves suggest, and what they leave open
        - Do NOT write a References section or any list of references: it is added for you from the papers you name.

        CRITICAL: Write a concise, clear description in plain, neutral wording, with no promotional or superlative language. Stay within 2200 characters. Do not name any paper that is not in the numbered list.
    ",
    "keywords": ["comma", "separated", "keywords", "from", "research"]
}}

**CRITICAL:** Use ONLY the real research provided. DO NOT make up fake references.
If asked about something not in the research, ADAM should acknowledge the gap.

**HONESTY AND FOCUS (do not violate; these override any earlier wish for strong or promotional language):**
- Stay on the question asked: "{research_context.topic}". Most of the episode must answer it from the listed papers (what they measured, built or found about it), not general background on the field. A listed paper that is only loosely related may be used only for the point it really supports, or left out.
- No absolute or certainty claims beyond what a listed paper itself states. Do not write that something is certain, error-free, guaranteed or true in every case unless the paper says exactly that, and then say it is that paper's claim. Use the hedging the papers use ("suggests", "in the cases studied", "in the library examined").
- Attribute only what was said. Never write "as you put it", "as you said" or similar unless that speaker said it earlier in this script; never put words into a researcher's or a speaker's mouth that are not in the evidence above.
- If the evidence is thin on part of the question, say so plainly ("the papers reviewed here do not measure that") instead of filling the gap.

**Naming rules (do not violate):**
- Name only papers from the numbered list; never invent or recall a paper, author or study that is not in it.
- Never write a DOI, URL or reference line anywhere in the script or description; references are added for you.
- Never write the labels [P1], [P2], ... anywhere in the script or description: they are for your reference only, and the script is read aloud.
- The script is read aloud, so write every symbol, formula and particle or chemical notation as plain words ("K short", "pi plus", "D sub s plus", "x squared", "10 to the minus 3"). Never use LaTeX, dollar signs or backslashes in the script or the description.
- Never write "(Recent)" or "(Year)" as a publication year. If the year is unknown, omit it.
"""
        
        return prompt
    
    def _format_research_evidence(self, context: PodcastResearchContext) -> str:
        """Format all research evidence for prompt"""
        
        evidence = []
        
        # Top research sources
        evidence.append("**CONFIRMED PAPERS YOU MAY NAME (numbered; name no other paper):**\n")
        for i, source in enumerate(context.research_sources[:12], 1):
            evidence.append(f"[{getattr(source, 'pid', None) or 'P' + str(i)}] **{source.title}**")
            evidence.append(f"   Authors: {', '.join(source.authors[:3])}{'et al.' if len(source.authors) > 3 else ''}")
            journal = (getattr(source, "journal", None) or "").strip()
            index_name = (source.source or "").strip().lower()
            if journal and journal.lower() not in {
                "pubmed", "arxiv", "biorxiv", "medrxiv", "pmc", "crossref"
            }:
                evidence.append(f"   Journal: {journal}")
            elif index_name not in {"pubmed", "arxiv", "biorxiv", "medrxiv", "pmc"}:
                evidence.append(f"   Venue: {source.source}")
            if source.doi:
                evidence.append(f"   DOI: {source.doi}")
            if source.url:
                evidence.append(f"   URL: {source.url}")
            pub = (source.publication_date or "").strip()
            if pub and pub.lower() not in {"recent", "n.d.", "nd"}:
                evidence.append(f"   Year: {pub[:4] if pub[:4].isdigit() else pub}")
            # The whole abstract, up to the length the attribution check reads, so the script is written from the text it is checked against.
            abstract = " ".join((source.abstract or "").split())
            evidence.append(f"   Abstract: {abstract[:MAX_ABSTRACT_CHARS]}{'...' if len(abstract) > MAX_ABSTRACT_CHARS else ''}")
            evidence.append("")
        
        # What the analyses say the papers change in how we see the question
        if context.significance:
            evidence.append("\n**CHANGES IN THINKING THE ANALYSES POINT TO (check each against the abstract before using it):**")
            for note in context.significance:
                evidence.append(f"- {note}")
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
        
        return "\n".join(evidence)

