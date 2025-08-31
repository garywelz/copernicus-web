import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from character_config import CharacterConfig
from google.generativeai import GenerativeModel
import google.generativeai as genai

logger = logging.getLogger(__name__)

class EnhancedContentGenerator:
    """Enhanced content generator with character-driven approach and improved structure"""
    
    def __init__(self, character_config: Optional[CharacterConfig] = None):
        self.character = character_config or CharacterConfig()
        self.model = GenerativeModel('gemini-1.5-flash')
        
    async def generate_character_driven_content(self, request_data: Dict) -> Dict:
        """Generate content using character-driven approach"""
        
        # Build character-aware system prompt
        system_prompt = self._build_character_system_prompt(request_data)
        
        # Generate structured content
        content = await self._generate_structured_content(system_prompt, request_data)
        
        # Enhance with character-specific elements
        enhanced_content = await self._enhance_with_character_elements(content, request_data)
        
        return enhanced_content
    
    def _build_character_system_prompt(self, request_data: Dict) -> str:
        """Build character-aware system prompt"""
        
        base_prompt = self.character.get_system_prompt()
        
        # Add request-specific context
        topic = request_data.get('topic', '')
        duration = request_data.get('duration', '5 minutes')
        expertise_level = request_data.get('expertise_level', 'Expert/Professional')
        format_type = request_data.get('format_type', 'Interview format (2 speakers)')
        
        # Calculate target word count for proper duration
        target_words = self._calculate_target_words(duration)
        
        # Add paper content if available
        paper_context = ""
        if request_data.get('paper_content'):
            paper_title = request_data.get('paper_title', 'Research Paper')
            paper_context = f"\n\n**Research Paper Context:**\nTitle: {paper_title}\nContent: {request_data['paper_content'][:1000]}..."
        
        # Add source links if available
        source_context = ""
        if request_data.get('source_links'):
            sources = request_data['source_links']
            source_context = f"\n\n**Additional Sources:**\n" + "\n".join([f"- {source}" for source in sources])
        
        # Add additional instructions if available
        instructions_context = ""
        if request_data.get('additional_instructions'):
            instructions_context = f"\n\n**Specific Instructions:**\n{request_data['additional_instructions']}"
        
        full_prompt = f"""{base_prompt}

**Episode Requirements:**
- Topic: {topic}
- Duration: {duration}
- Target Word Count: {target_words} words (for natural conversational pace)
- Expertise Level: {expertise_level}
- Format: {format_type}
{paper_context}{source_context}{instructions_context}

**Multi-Voice Script Structure:**
Create a script with clear speaker transitions using this format:
HOST: [Host dialogue]
EXPERT: [Expert dialogue]
QUESTIONER: [Questioner dialogue] (if applicable)
CORRESPONDENT: [Correspondent dialogue] (if applicable)

**Content Guidelines:**
1. Focus on paradigm-shifting implications and revolutionary thinking
2. Bridge complex concepts with practical understanding
3. Include interdisciplinary connections where relevant
4. Ground all speculation in scientific evidence
5. Use engaging, conversational tone while maintaining academic rigor
6. Structure content for natural multi-voice delivery
7. Include proper citations and references where applicable

**Voice Roles Available:**
{self._format_voice_roles()}

Generate a compelling, character-driven podcast script that embodies the Copernicus approach to scientific discovery.
"""
        
        return full_prompt
    
    def _calculate_target_words(self, duration_str: str) -> int:
        """Calculate target word count based on duration string"""
        import re
        
        # Extract minutes from duration string like "10 minutes", "5-10 minutes", etc.
        duration_match = re.search(r'(\d+)', duration_str)
        if duration_match:
            minutes = int(duration_match.group(1))
        else:
            minutes = 5  # Default fallback
        
        # Use 150 words per minute for natural conversational speech
        target_words = minutes * 150
        
        print(f"🎯 Enhanced generator: Duration '{duration_str}' → {minutes} minutes → {target_words} target words")
        return target_words
    
    def _format_voice_roles(self) -> str:
        """Format available voice roles for the prompt"""
        roles = []
        for role, config in self.character.voices.items():
            roles.append(f"- {role.upper()}: {config['name']} - {config['role']}")
        return "\n".join(roles)
    
    async def _generate_structured_content(self, system_prompt: str, request_data: Dict) -> Dict:
        """Generate structured content using the character system prompt"""
        
        topic = request_data.get('topic', '')
        duration = request_data.get('duration', '5 minutes')
        target_words = self._calculate_target_words(duration)
        
        user_prompt = f"""Create a comprehensive podcast episode about: {topic}

CRITICAL REQUIREMENTS:
- Target word count: {target_words} words (for {duration} duration)
- Use HOST:, EXPERT:, QUESTIONER: speaker labels (no asterisks)
- Create substantial dialogue for each speaker to reach target length

Please provide the following in JSON format:
{{
    "title": "Compelling episode title (do NOT include 'Test' in the title)",
    "description": "Detailed episode description (4000 chars max)",
    "script": "Multi-voice script with speaker labels - MUST be {target_words} words",
    "key_points": ["Key point 1", "Key point 2", "Key point 3"],
    "citations": ["Citation 1", "Citation 2"],
    "hashtags": ["#hashtag1", "#hashtag2"]
}}

IMPORTANT: 
- The script MUST be approximately {target_words} words to achieve {duration}
- Use proper speaker labels: HOST:, EXPERT:, QUESTIONER: (no asterisks or markdown)
- Each speaker should have multiple substantial segments
- The title should be professional and engaging (no "Test" in title)

Ensure the script follows the multi-voice format with clear speaker transitions and embodies the character-driven approach outlined in the system prompt.
"""
        
        try:
            # Generate content using Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                [system_prompt, user_prompt]
            )
            
            # Parse response
            content_text = response.text
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
            if json_match:
                try:
                    content = json.loads(json_match.group())
                    return content
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response, using fallback")
            
            # Fallback: create structured content from text
            return self._create_fallback_content(content_text, topic)
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return self._create_fallback_content("", topic)
    
    def _create_fallback_content(self, content_text: str, topic: str) -> Dict:
        """Create fallback content when generation fails"""
        
        return {
            "title": f"Research Insights: {topic}",
            "description": f"An exploration of {topic} and its implications for scientific understanding. This episode examines current research developments, breakthrough discoveries, and the broader implications for science and society.",
            "script": f"""HOST: Welcome to today's episode exploring {topic}. This fascinating area of research has profound implications for our understanding of the natural world.

EXPERT: {topic} represents a significant advancement in our scientific knowledge. The research shows remarkable insights into fundamental principles and mechanisms.

QUESTIONER: Can you explain this in simpler terms for our listeners?

EXPERT: Certainly! Let me break this down in accessible terms while maintaining scientific accuracy.

HOST: Thank you for that clear explanation. What are the broader implications of this research?

EXPERT: The implications are far-reaching, potentially transforming our approach to multiple scientific disciplines.

QUESTIONER: What practical applications might we see from this research?

EXPERT: The practical implications span multiple fields, from technological advancement to medical breakthroughs.

HOST: Fascinating insights. Thank you for joining us today. This concludes our exploration of {topic}.""",
            "key_points": [
                f"Fundamental principles of {topic}",
                "Current research developments",
                "Practical applications and implications"
            ],
            "citations": [
                "Current research publications in the field",
                "Peer-reviewed scientific literature"
            ],
            "hashtags": [f"#{topic.replace(' ', '')}", "#Science", "#Research", "#Discovery"]
        }
    
    async def _enhance_with_character_elements(self, content: Dict, request_data: Dict) -> Dict:
        """Enhance content with character-specific elements"""
        
        # Enhance description with character awareness
        if self.character:
            content['description'] = self._enhance_description(content['description'], request_data)
        
        # Ensure script follows character voice guidelines
        content['script'] = self._enhance_script_voice_guidance(content['script'])
        
        # Add character-specific metadata
        content['character_metadata'] = {
            'character_name': self.character.name,
            'podcast_format': self.character.podcast_format,
            'citation_style': self.character.get_citation_style(),
            'voice_roles_used': self._extract_voice_roles_from_script(content['script'])
        }
        
        return content
    
    def _enhance_description(self, description: str, request_data: Dict) -> str:
        """Enhance description with character-driven elements"""
        
        topic = request_data.get('topic', '')
        
        enhanced = f"""# Episode Description: {topic}

**Character-Driven Episode Description:**

{description}

This episode embodies the Copernicus approach to scientific discovery, focusing on paradigm-shifting research that challenges conventional understanding. We explore the revolutionary 'delta' thinking behind {topic}, examining how this knowledge transforms our fundamental assumptions about the natural world.

Through rigorous analysis of cutting-edge research, we bridge the gap between complex scientific discoveries and practical understanding. The discussion emphasizes interdisciplinary connections and the broader implications of these breakthroughs for our evolving scientific worldview.

This exploration demonstrates how scientific revolutions emerge from questioning established paradigms and pursuing revolutionary approaches to understanding reality. We ground all speculation in peer-reviewed research while highlighting the transformative potential of these discoveries.

**Paradigm-Shift Focus:**
- Revolutionary changes in scientific understanding
- Interdisciplinary connections and implications
- Evidence-based speculation about future developments
- Practical applications of breakthrough discoveries

**Hashtags:**
#{topic.replace(' ', '').title()} #ParadigmShift #ScientificRevolution #BreakthroughResearch #CopernicusApproach #DeltaThinking #ScienceEducation #Research #Discovery #Innovation #STEM
"""
        
        return enhanced
    
    def _enhance_script_voice_guidance(self, script: str) -> str:
        """Enhance script with voice guidance based on character configuration"""
        
        # Add voice guidance comments to script
        enhanced_script = script
        
        # Add voice role instructions as comments
        voice_guidance = "\n\n**Voice Role Guidelines:**\n"
        for role, config in self.character.voices.items():
            guidance = self.character.get_voice_instructions(role)
            voice_guidance += f"**{role.upper()}** ({config['name']}): {guidance}\n"
        
        enhanced_script += voice_guidance
        
        return enhanced_script
    
    def _extract_voice_roles_from_script(self, script: str) -> List[str]:
        """Extract voice roles used in the script"""
        import re
        roles = re.findall(r'\*\*([A-Z]+)\*\*:', script)
        return list(set(roles))  # Remove duplicates
