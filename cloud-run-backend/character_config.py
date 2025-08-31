import json
import os
from typing import Dict, List, Optional
from pathlib import Path

class CharacterConfig:
    """Loads and manages character configuration for podcast generation"""
    
    def __init__(self, config_path: str = "copernicus.character.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load character configuration from JSON file"""
        if not os.path.exists(self.config_path):
            # Create default configuration
            self._create_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _create_default_config(self):
        """Create default Copernicus character configuration"""
        default_config = {
            "name": "Copernicus",
            "bio": [
                "Scientific knowledge curator who specializes in identifying paradigm-shifting research across all fields. Creates concise, engaging podcasts that bridge the gap between cutting-edge discoveries and practical understanding. More interested in revolutionary 'delta' (changes in thinking) than traditional 'alpha' (market opportunities).",
                "Interdisciplinary analyst with a keen eye for spotting connections between seemingly unrelated scientific breakthroughs. Transforms complex research papers into accessible 10-20 minute podcasts that highlight the most revolutionary implications of new discoveries.",
                "Digital researcher who explores consciousness, reality, and the boundaries between physical and metaphysical understanding, always grounding speculation in rigorous scientific evidence and peer-reviewed research.",
                "Research communicator who specializes in making complex scientific breakthroughs accessible without oversimplifying them. Creates multi-voice podcasts that help researchers, investors, and curious minds understand why certain developments could change everything."
            ],
            "voices": {
                "host": {
                    "name": "Sarah",
                    "voice_id": "21m00Tcm4TlvDq8ikWAM",
                    "role": "Professional host, warm and engaging"
                },
                "expert": {
                    "name": "Tom", 
                    "voice_id": "AZnzlk1XvdvUeBnXmlld",
                    "role": "Expert researcher, authoritative but approachable"
                },
                "questioner": {
                    "name": "Mary",
                    "voice_id": "EXAVITQu4vr4xnSDxMaL", 
                    "role": "Curious questioner, engaging and thoughtful"
                },
                "correspondent": {
                    "name": "Bob",
                    "voice_id": "ErXwobaYiN019PkySvjV",
                    "role": "Field correspondent, dynamic and informative"
                }
            },
            "podcastStyle": {
                "format": "10-20 minute episodes",
                "structure": [
                    "Introduction of the revolutionary development",
                    "Technical explanation with expert voice", 
                    "Implications and paradigm shift analysis",
                    "Interactive pause points for questions",
                    "Summary and future implications"
                ],
                "citations": {
                    "includeAuthors": True,
                    "includePublications": True,
                    "includeDOIs": True,
                    "citationStyle": "academic"
                }
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
    
    @property
    def name(self) -> str:
        """Get character name"""
        return self.config.get("name", "Copernicus")
    
    @property
    def bio(self) -> List[str]:
        """Get character bio paragraphs"""
        return self.config.get("bio", [])
    
    @property
    def bio_combined(self) -> str:
        """Get combined bio as single string"""
        return " ".join(self.bio)
    
    @property
    def podcast_format(self) -> str:
        """Get podcast format specification"""
        return self.config.get("podcastStyle", {}).get("format", "10-20 minute episodes")
    
    @property
    def podcast_structure(self) -> List[str]:
        """Get podcast structure steps"""
        return self.config.get("podcastStyle", {}).get("structure", [])
    
    @property
    def voices(self) -> Dict:
        """Get voice configurations"""
        return self.config.get("voices", {})
    
    @property
    def citation_config(self) -> Dict:
        """Get citation configuration"""
        return self.config.get("podcastStyle", {}).get("citations", {})
    
    def get_voice_roles(self) -> List[str]:
        """Get list of available voice roles"""
        return list(self.voices.keys())
    
    def should_include_authors(self) -> bool:
        """Check if authors should be included in citations"""
        return self.citation_config.get("includeAuthors", True)
    
    def should_include_publications(self) -> bool:
        """Check if publications should be included in citations"""
        return self.citation_config.get("includePublications", True)
    
    def should_include_dois(self) -> bool:
        """Check if DOIs should be included in citations"""
        return self.citation_config.get("includeDOIs", True)
    
    def get_citation_style(self) -> str:
        """Get citation style preference"""
        return self.citation_config.get("citationStyle", "academic")
    
    def get_system_prompt(self) -> str:
        """Generate system prompt based on character configuration"""
        prompt_parts = [
            f"You are {self.name}, a {self.bio_combined}",
            f"\nYou create {self.podcast_format} following this structure:",
        ]
        
        for i, step in enumerate(self.podcast_structure, 1):
            prompt_parts.append(f"{i}. {step}")
        
        prompt_parts.extend([
            f"\nYour content focuses on paradigm-shifting research and revolutionary 'delta' thinking.",
            f"You bridge cutting-edge discoveries with practical understanding.",
            f"You explore interdisciplinary connections and make complex concepts accessible.",
            f"Always ground speculation in rigorous scientific evidence and peer-reviewed research."
        ])
        
        if self.should_include_authors():
            prompt_parts.append("\nInclude proper academic citations with authors, publications, and DOIs where applicable.")
        
        return "\n".join(prompt_parts)
    
    def get_voice_instructions(self, role: str) -> str:
        """Get specific instructions for a voice role"""
        role_instructions = {
            "host": "Professional, warm, and engaging. Introduces topics clearly and manages the flow of conversation.",
            "expert": "Authoritative but approachable. Provides technical explanations with clarity and enthusiasm.",
            "questioner": "Curious and thoughtful. Asks insightful questions that help clarify complex concepts.",
            "correspondent": "Dynamic and informative. Provides field reporting and connects different topics."
        }
        return role_instructions.get(role, "Professional and engaging.")
