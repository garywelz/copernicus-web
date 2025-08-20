"""
Enhanced Research Service - Production Quality
Integrates sophisticated patterns from legacy Copernicus architecture:
- Multi-paper synthesis and connection analysis
- Essay-to-podcast conversion with theme extraction
- Structured JSON prompts with validation
- Quality control workflows
"""

import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
import re
from research_pipeline import ComprehensiveResearchPipeline, ResearchSource

@dataclass
class PaperAnalysis:
    """Enhanced paper analysis following legacy architecture patterns"""
    title: str
    summary: str
    key_findings: List[str]
    methodology: str
    implications: str
    related_work: str
    technical_complexity: str  # 'low', 'medium', 'high'
    suggested_questions: List[str]
    keywords: List[str]
    paradigm_shift_potential: str
    interdisciplinary_connections: List[str]
    practical_applications: List[str]
    future_research_directions: List[str]

@dataclass
class ThemeAnalysis:
    """Theme extraction for essay-to-podcast conversion"""
    theme: str
    expansion_directives: str
    technical_depth: str
    estimated_duration: int  # seconds
    speaker_assignments: List[str]
    key_concepts: List[str]

@dataclass
class PodcastSegment:
    """Structured podcast segment following legacy patterns"""
    speaker: str
    content: str
    tone: str
    duration_seconds: int
    pause_after: bool = False
    voice_config: Optional[Dict[str, Any]] = None

@dataclass
class EnhancedPodcastScript:
    """Complete podcast script with production metadata"""
    title: str
    introduction: str
    segments: List[PodcastSegment]
    conclusion: str
    total_duration: int
    speakers: List[str]
    themes: List[str]
    citations: List[str]
    hashtags: List[str]

class EnhancedResearchService:
    """
    Production-quality research service integrating legacy architecture patterns
    """
    
    def __init__(self, google_api_key: str):
        self.google_api_key = google_api_key
        self.research_pipeline = ComprehensiveResearchPipeline()
        
        # Voice configuration patterns from legacy architecture
        self.voice_configs = {
            "host": {
                "voice": "en-US-Neural2-J",  # Professional female
                "speed": 1.0,
                "stability": 0.8,
                "similarity_boost": 0.7,
                "style": 0.6
            },
            "expert": {
                "voice": "en-US-Neural2-D",  # Authoritative male
                "speed": 0.95,
                "stability": 0.75,
                "similarity_boost": 0.8,
                "style": 0.7
            },
            "questioner": {
                "voice": "en-US-Neural2-A",  # Curious female
                "speed": 1.05,
                "stability": 0.7,
                "similarity_boost": 0.75,
                "style": 0.5
            }
        }
        
        # Production prompts following legacy structured approach
        self.analysis_prompts = {
            "paper_analysis": self._get_paper_analysis_prompt(),
            "theme_extraction": self._get_theme_extraction_prompt(),
            "dialogue_generation": self._get_dialogue_generation_prompt(),
            "connection_analysis": self._get_connection_analysis_prompt()
        }

    async def analyze_multiple_papers(
        self, 
        papers: List[ResearchSource], 
        complexity: str = "intermediate"
    ) -> List[PaperAnalysis]:
        """
        Analyze multiple papers and find connections (legacy PaperAnalyzer pattern)
        """
        print(f"🔬 Analyzing {len(papers)} papers with {complexity} complexity...")
        
        # Analyze each paper individually
        analyses = []
        for i, paper in enumerate(papers):
            print(f"📄 Analyzing paper {i+1}/{len(papers)}: {paper.title[:50]}...")
            analysis = await self._analyze_single_paper(paper, complexity)
            analyses.append(analysis)
        
        # Find connections between papers (legacy pattern)
        if len(papers) > 1:
            print("🔗 Finding connections between papers...")
            connections = await self._find_paper_connections(analyses)
            
            # Add connection insights to each analysis
            for i, analysis in enumerate(analyses):
                if i < len(connections):
                    analysis.related_work += f"\n\nConnections to other papers:\n" + "\n".join(connections[i])
        
        return analyses

    async def _analyze_single_paper(
        self, 
        paper: ResearchSource, 
        complexity: str
    ) -> PaperAnalysis:
        """
        Analyze a single paper with structured prompts (legacy pattern)
        """
        prompt = self.analysis_prompts["paper_analysis"].format(
            title=paper.title,
            authors=", ".join(paper.authors),
            abstract=paper.abstract,
            complexity=complexity
        )
        
        try:
            response = await self._call_google_ai(prompt, max_tokens=1500)
            analysis_data = json.loads(response)
            return self._validate_paper_analysis(analysis_data)
        except Exception as e:
            print(f"❌ Paper analysis error: {e}")
            return self._create_fallback_analysis(paper)

    async def _find_paper_connections(
        self, 
        analyses: List[PaperAnalysis]
    ) -> List[List[str]]:
        """
        Find meaningful connections between papers (legacy pattern)
        """
        prompt = self.analysis_prompts["connection_analysis"].format(
            num_papers=len(analyses),
            paper_summaries="\n".join([
                f"Paper {i+1}: {analysis.title}\nSummary: {analysis.summary}\nKey Findings: {', '.join(analysis.key_findings)}"
                for i, analysis in enumerate(analyses)
            ])
        )
        
        try:
            response = await self._call_google_ai(prompt, max_tokens=1000)
            connections = json.loads(response)
            return connections if isinstance(connections, list) else [[] for _ in analyses]
        except Exception as e:
            print(f"❌ Connection analysis error: {e}")
            return [[] for _ in analyses]

    async def generate_podcast_from_research(
        self,
        topic: str,
        research_analyses: List[PaperAnalysis],
        duration_minutes: int = 8,
        expertise_level: str = "intermediate"
    ) -> EnhancedPodcastScript:
        """
        Generate podcast script from research analyses (legacy multi-stage pattern)
        """
        print(f"🎙️ Generating {duration_minutes}-minute podcast from {len(research_analyses)} research analyses...")
        
        # Stage 1: Extract themes from research
        themes = await self._extract_themes_from_research(research_analyses, topic)
        print(f"📋 Extracted {len(themes)} themes: {[t.theme for t in themes]}")
        
        # Stage 2: Generate core dialogue segments
        core_segments = []
        for theme in themes:
            print(f"🗣️ Generating dialogue for theme: {theme.theme}")
            dialogue = await self._generate_theme_dialogue(theme, expertise_level)
            core_segments.append({
                "theme": theme.theme,
                "script": dialogue,
                "duration": theme.estimated_duration
            })
        
        # Stage 3: Assemble full podcast script
        podcast_script = await self._assemble_podcast_script(
            topic, core_segments, duration_minutes, research_analyses
        )
        
        return podcast_script

    async def _extract_themes_from_research(
        self,
        analyses: List[PaperAnalysis],
        topic: str
    ) -> List[ThemeAnalysis]:
        """
        Extract themes from research analyses (legacy theme extraction pattern)
        """
        research_summary = "\n".join([
            f"Paper: {analysis.title}\nKey Findings: {', '.join(analysis.key_findings)}\nImplications: {analysis.implications}"
            for analysis in analyses
        ])
        
        prompt = self.analysis_prompts["theme_extraction"].format(
            topic=topic,
            research_summary=research_summary
        )
        
        try:
            response = await self._call_google_ai(prompt, max_tokens=1200)
            themes_data = json.loads(response)
            
            themes = []
            for theme_data in themes_data.get("themes", []):
                theme = ThemeAnalysis(
                    theme=theme_data.get("theme", ""),
                    expansion_directives=theme_data.get("expansion_directives", ""),
                    technical_depth=theme_data.get("technical_depth", "medium"),
                    estimated_duration=theme_data.get("estimated_duration", 90),
                    speaker_assignments=theme_data.get("speaker_assignments", ["host", "expert"]),
                    key_concepts=theme_data.get("key_concepts", [])
                )
                themes.append(theme)
            
            return themes
        except Exception as e:
            print(f"❌ Theme extraction error: {e}")
            return self._create_fallback_themes(topic)

    async def _generate_theme_dialogue(
        self,
        theme: ThemeAnalysis,
        expertise_level: str
    ) -> str:
        """
        Generate dialogue for a specific theme (legacy dialogue generation pattern)
        """
        prompt = self.analysis_prompts["dialogue_generation"].format(
            theme=theme.theme,
            expansion_directives=theme.expansion_directives,
            technical_depth=theme.technical_depth,
            expertise_level=expertise_level,
            duration=theme.estimated_duration,
            speakers=", ".join(theme.speaker_assignments),
            key_concepts=", ".join(theme.key_concepts)
        )
        
        try:
            response = await self._call_google_ai(prompt, max_tokens=1000)
            return response.strip()
        except Exception as e:
            print(f"❌ Dialogue generation error: {e}")
            return f"HOST: Let's explore {theme.theme}.\nEXPERT: This is a fascinating area of research with significant implications."

    async def _assemble_podcast_script(
        self,
        topic: str,
        core_segments: List[Dict],
        duration_minutes: int,
        research_analyses: List[PaperAnalysis]
    ) -> EnhancedPodcastScript:
        """
        Assemble complete podcast script (legacy assembly pattern)
        """
        # Generate introduction
        introduction = await self._generate_introduction(topic, research_analyses)
        
        # Process segments with voice configurations
        podcast_segments = []
        for segment_data in core_segments:
            segments = self._parse_dialogue_to_segments(
                segment_data["script"], 
                segment_data["duration"]
            )
            podcast_segments.extend(segments)
        
        # Generate conclusion
        conclusion = await self._generate_conclusion(topic, research_analyses)
        
        # Calculate total duration
        total_duration = sum(seg.duration_seconds for seg in podcast_segments) + 30 + 30  # intro + outro
        
        # Extract citations and hashtags
        citations = self._extract_citations(research_analyses)
        hashtags = self._generate_hashtags(topic, research_analyses)
        
        return EnhancedPodcastScript(
            title=f"Copernicus AI: {topic}",
            introduction=introduction,
            segments=podcast_segments,
            conclusion=conclusion,
            total_duration=total_duration,
            speakers=["host", "expert", "questioner"],
            themes=[seg["theme"] for seg in core_segments],
            citations=citations,
            hashtags=hashtags
        )

    def _parse_dialogue_to_segments(
        self, 
        dialogue: str, 
        total_duration: int
    ) -> List[PodcastSegment]:
        """
        Parse dialogue text into structured segments with voice configs
        """
        segments = []
        lines = dialogue.split('\n')
        
        # Estimate duration per line
        duration_per_line = total_duration // max(len([l for l in lines if l.strip()]), 1)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse speaker and content
            if ':' in line:
                speaker_part, content = line.split(':', 1)
                speaker = speaker_part.strip().lower()
                content = content.strip()
                
                # Map speaker to voice config
                if speaker in ['host', 'interviewer']:
                    voice_speaker = "host"
                elif speaker in ['expert', 'researcher', 'scientist']:
                    voice_speaker = "expert"
                else:
                    voice_speaker = "questioner"
                
                segment = PodcastSegment(
                    speaker=voice_speaker,
                    content=content,
                    tone="conversational",
                    duration_seconds=duration_per_line,
                    voice_config=self.voice_configs.get(voice_speaker)
                )
                segments.append(segment)
        
        return segments

    async def _generate_introduction(
        self, 
        topic: str, 
        analyses: List[PaperAnalysis]
    ) -> str:
        """Generate podcast introduction"""
        key_findings = []
        for analysis in analyses[:3]:  # Top 3 papers
            key_findings.extend(analysis.key_findings[:2])
        
        return f"""Welcome to Copernicus AI, where we explore the frontiers of scientific discovery. 
I'm your host, and today we're diving deep into {topic}. 
We'll be examining cutting-edge research that reveals {', '.join(key_findings[:3])}. 
Let's explore what these findings mean for science and society."""

    async def _generate_conclusion(
        self, 
        topic: str, 
        analyses: List[PaperAnalysis]
    ) -> str:
        """Generate podcast conclusion"""
        implications = [analysis.implications for analysis in analyses if analysis.implications]
        
        return f"""As we wrap up our exploration of {topic}, it's clear that this research opens up fascinating new possibilities. 
The implications span from {', '.join(implications[:2]) if implications else 'fundamental science to practical applications'}. 
Thank you for joining us on this journey through the latest scientific discoveries. 
Until next time, keep questioning, keep exploring, and keep pushing the boundaries of knowledge."""

    def _extract_citations(self, analyses: List[PaperAnalysis]) -> List[str]:
        """Extract formatted citations from analyses"""
        citations = []
        for analysis in analyses:
            citation = f"{analysis.title}. {', '.join(analysis.keywords[:3])}."
            citations.append(citation)
        return citations

    def _generate_hashtags(self, topic: str, analyses: List[PaperAnalysis]) -> List[str]:
        """Generate relevant hashtags"""
        hashtags = ["#CopernicusAI", "#SciencePodcast", "#Research"]
        
        # Add topic-specific hashtags
        topic_words = topic.lower().split()
        for word in topic_words:
            if len(word) > 3:
                hashtags.append(f"#{word.capitalize()}")
        
        # Add keywords from analyses
        all_keywords = []
        for analysis in analyses:
            all_keywords.extend(analysis.keywords[:2])
        
        for keyword in set(all_keywords[:5]):
            hashtags.append(f"#{keyword.replace(' ', '')}")
        
        return hashtags[:10]  # Limit to 10 hashtags

    async def _call_google_ai(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call Google AI API with structured prompts"""
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.google_api_key
        }
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    raise Exception(f"Google AI API error: {response.status}")

    def _validate_paper_analysis(self, analysis_data: dict) -> PaperAnalysis:
        """Validate and create PaperAnalysis object"""
        required_fields = [
            "title", "summary", "key_findings", "methodology",
            "implications", "related_work", "technical_complexity",
            "suggested_questions", "keywords"
        ]
        
        for field in required_fields:
            if field not in analysis_data:
                analysis_data[field] = self._get_default_value(field)
        
        # Add enhanced fields
        analysis_data.setdefault("paradigm_shift_potential", "medium")
        analysis_data.setdefault("interdisciplinary_connections", [])
        analysis_data.setdefault("practical_applications", [])
        analysis_data.setdefault("future_research_directions", [])
        
        return PaperAnalysis(**analysis_data)

    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            "title": "Research Paper",
            "summary": "Analysis not available",
            "key_findings": [],
            "methodology": "Not specified",
            "implications": "Further research needed",
            "related_work": "Context not available",
            "technical_complexity": "medium",
            "suggested_questions": [],
            "keywords": []
        }
        return defaults.get(field, "")

    def _create_fallback_analysis(self, paper: ResearchSource) -> PaperAnalysis:
        """Create fallback analysis when AI processing fails"""
        return PaperAnalysis(
            title=paper.title,
            summary=paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract,
            key_findings=["Research findings require further analysis"],
            methodology="Methodology analysis pending",
            implications="Implications to be determined",
            related_work="Related work analysis pending",
            technical_complexity="medium",
            suggested_questions=["What are the key implications of this research?"],
            keywords=["research", "analysis"],
            paradigm_shift_potential="unknown",
            interdisciplinary_connections=[],
            practical_applications=[],
            future_research_directions=[]
        )

    def _create_fallback_themes(self, topic: str) -> List[ThemeAnalysis]:
        """Create fallback themes when extraction fails"""
        return [
            ThemeAnalysis(
                theme=f"Introduction to {topic}",
                expansion_directives="Provide overview and context",
                technical_depth="medium",
                estimated_duration=120,
                speaker_assignments=["host", "expert"],
                key_concepts=[topic]
            ),
            ThemeAnalysis(
                theme=f"Current Research in {topic}",
                expansion_directives="Discuss recent developments",
                technical_depth="high",
                estimated_duration=180,
                speaker_assignments=["expert", "questioner"],
                key_concepts=["research", "methodology"]
            )
        ]

    def _get_paper_analysis_prompt(self) -> str:
        """Structured paper analysis prompt (legacy pattern)"""
        return """
Analyze this research paper with {complexity} complexity level.
Focus on making the content accessible while maintaining accuracy.

Title: {title}
Authors: {authors}
Abstract: {abstract}

Provide analysis in JSON format:
{{
    "title": "Paper title in accessible terms",
    "summary": "Clear explanation of main points",
    "key_findings": ["Array of key findings"],
    "methodology": "Research approach description",
    "implications": "Real-world impact and applications",
    "related_work": "Context within the field",
    "technical_complexity": "low/medium/high",
    "suggested_questions": ["Discussion questions"],
    "keywords": ["Relevant keywords"],
    "paradigm_shift_potential": "low/medium/high",
    "interdisciplinary_connections": ["Connected fields"],
    "practical_applications": ["Real-world uses"],
    "future_research_directions": ["Next steps"]
}}
"""

    def _get_theme_extraction_prompt(self) -> str:
        """Theme extraction prompt for essay-to-podcast conversion"""
        return """
Analyze this research and extract 3-4 core themes for podcast discussion.

Topic: {topic}
Research Summary:
{research_summary}

Return JSON with themes array:
{{
    "themes": [
        {{
            "theme": "Theme title",
            "expansion_directives": "Detailed guidance for dialogue",
            "technical_depth": "low/medium/high",
            "estimated_duration": 90,
            "speaker_assignments": ["host", "expert"],
            "key_concepts": ["concept1", "concept2"]
        }}
    ]
}}
"""

    def _get_dialogue_generation_prompt(self) -> str:
        """Dialogue generation prompt with natural first names"""
        return """
Generate {duration}-second natural conversation for this theme using exactly three speakers with FIRST NAMES ONLY.

Theme: {theme}
Expansion Directives: {expansion_directives}
Technical Depth: {technical_depth}
Expertise Level: {expertise_level}
Key Concepts: {key_concepts}

Speaker Roles:
- SARAH (Host): Guides the conversation, introduces topics, provides transitions
- TOM (Expert): Provides technical explanations, research insights, scientific details
- MARY (Questioner): Asks curious questions, seeks clarifications, represents audience perspective

Required format:
SARAH: [natural introduction or transition]
TOM: [technical explanation in accessible language]
MARY: [thoughtful question or clarification request]

CRITICAL RULES:
- Use ONLY first names: SARAH:, TOM:, MARY: (never HOST, EXPERT, QUESTIONER)
- Write as natural conversation, not formal presentation
- Each speaker should have 3-5 segments minimum
- Avoid repetitive phrases like "That's fascinating" or "Great question"
- No academic titles, degrees, or formal language
- Make it sound like friends discussing interesting science
- Keep technical accuracy but use conversational tone
- Vary sentence structure and speaking patterns
- Include natural interruptions and follow-up questions
"""

    def _get_connection_analysis_prompt(self) -> str:
        """Connection analysis prompt for multi-paper synthesis"""
        return """
Analyze these {num_papers} papers and identify meaningful connections.
Focus on shared themes, complementary findings, and synthesis opportunities.

{paper_summaries}

Return JSON array of connection descriptions for each paper:
[
    ["connections for paper 1"],
    ["connections for paper 2"],
    ...
]
"""
