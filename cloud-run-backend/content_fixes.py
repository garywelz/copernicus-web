#!/usr/bin/env python3
"""
Content fixes for podcast generation issues
Addresses voice assignment, DOI removal, and category classification
"""

import re
import unicodedata
from typing import Dict, List, Optional

def remove_dois_from_script(script: str) -> str:
    """
    Remove DOI numbers, publication details, and stage directions from spoken script content
    DOIs should only appear in transcripts and descriptions, not spoken content
    """
    # Remove DOI patterns from script
    doi_patterns = [
        r'DOI:\s*10\.\d{4}/[^\s]+',  # DOI: 10.xxxx/xxxx
        r'10\.\d{4}/[^\s]+',         # Just the DOI number
        r'doi:\s*10\.\d{4}/[^\s]+',  # Lowercase doi
    ]
    
    cleaned_script = script
    for pattern in doi_patterns:
        cleaned_script = re.sub(pattern, '', cleaned_script, flags=re.IGNORECASE)
    
    # Remove publication details that sound too technical when spoken
    publication_patterns = [
        r'\([0-9]{4}\)',              # Publication years like (2023)
        r'Volume\s+[0-9]+',           # Volume numbers
        r'Issue\s+[0-9]+',            # Issue numbers
        r'Pages?\s+[0-9\-]+',         # Page numbers
        r'pp\.\s*[0-9\-]+',           # Page abbreviations
        r'DOI:\s*10\.xxxx/xxxx',      # Placeholder DOIs
    ]
    
    for pattern in publication_patterns:
        cleaned_script = re.sub(pattern, '', cleaned_script, flags=re.IGNORECASE)
    
    # Remove stage directions and production notes
    stage_directions = [
        r'Pause for reflection',
        r'\[pause\]',
        r'\(pause\)',
        r'\[music\]',
        r'\(music\)',
        r'\[sound effect\]',
        r'\(sound effect\)',
        r'\[transition\]',
        r'\(transition\)',
        r'\[break\]',
        r'\(break\)',
        r'\[commercial break\]',
        r'\(commercial break\)',
        r'\[end\]',
        r'\(end\)',
        r'\[fade out\]',
        r'\(fade out\)',
        r'\[fade in\]',
        r'\(fade in\)'
    ]
    
    for direction in stage_directions:
        cleaned_script = re.sub(direction, '', cleaned_script, flags=re.IGNORECASE)
    
    # Remove any remaining bracketed text that looks like directions
    cleaned_script = re.sub(r'\[[^\]]*\]', '', cleaned_script)
    cleaned_script = re.sub(r'\([^)]*\)', '', cleaned_script)
    
    # Clean up any double spaces or punctuation issues
    cleaned_script = re.sub(r'\s+', ' ', cleaned_script)
    cleaned_script = re.sub(r'\s+([.!?])', r'\1', cleaned_script)
    cleaned_script = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_script)
    
    return cleaned_script.strip()

def classify_topic_category(topic: str) -> str:
    """
    Properly classify topic into scientific categories
    Instead of just taking the first word, use intelligent classification
    """
    topic_lower = topic.lower()
    
    # Computer Science topics
    if any(word in topic_lower for word in ['neural', 'network', 'machine learning', 'ai', 'artificial intelligence', 
                                          'algorithm', 'computing', 'computer', 'software', 'programming', 'data']):
        return 'Computer Science'
    
    # Biology topics
    if any(word in topic_lower for word in ['brain', 'neural', 'cell', 'dna', 'gene', 'protein', 'organism', 
                                          'biology', 'biological', 'genetic', 'molecular']):
        return 'Biology'
    
    # Physics topics
    if any(word in topic_lower for word in ['quantum', 'particle', 'energy', 'matter', 'physics', 'physical', 
                                          'mechanics', 'thermodynamics', 'electromagnetic']):
        return 'Physics'
    
    # Chemistry topics
    if any(word in topic_lower for word in ['chemical', 'molecule', 'reaction', 'catalyst', 'chemistry', 
                                          'synthesis', 'compound', 'element']):
        return 'Chemistry'
    
    # Mathematics topics
    if any(word in topic_lower for word in ['mathematics', 'math', 'mathematical', 'equation', 'theorem', 
                                          'proof', 'calculation', 'statistics']):
        return 'Mathematics'
    
    # Medicine topics
    if any(word in topic_lower for word in ['medical', 'medicine', 'clinical', 'treatment', 'therapy', 
                                          'diagnosis', 'patient', 'healthcare']):
        return 'Medicine'
    
    # Engineering topics
    if any(word in topic_lower for word in ['engineering', 'engineer', 'mechanical', 'electrical', 
                                          'civil', 'aerospace', 'robotics']):
        return 'Engineering'
    
    # Default to Science for general topics
    return 'Science'

def extract_speakers_from_script(script: str) -> set:
    """
    Extract speaker names from the script
    Returns a set of speaker names found in the script
    """
    speakers_found = set()
    
    # Look for speaker labels
    speaker_patterns = [
        r'^(HOST|EXPERT|QUESTIONER|CORRESPONDENT):',
        r'^(Sarah|Tom|Mary|Bob|Maya|James|Sophia|Noah|Aisha):'
    ]
    
    lines = script.split('\n')
    for line in lines:
        line = line.strip()
        for pattern in speaker_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                speaker = re.match(pattern, line, re.IGNORECASE).group(1).lower()
                speakers_found.add(speaker)
                break
    
    return speakers_found

def fix_voice_assignment(script: str) -> str:
    """
    Ensure proper voice assignment for panel discussion format
    Remove speaker labels from spoken content and ensure multi-voice format
    """
    # Remove speaker labels from the script content (they shouldn't be spoken)
    script = re.sub(r'\b(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*', '', script, flags=re.IGNORECASE)
    
    # Remove any remaining speaker labels that might be in the content
    script = re.sub(r'\n\s*(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\s*', '\n', script, flags=re.IGNORECASE)
    
    # Clean up any double spaces or line breaks
    script = re.sub(r'\n\s*\n', '\n\n', script)
    script = re.sub(r'\s+', ' ', script)
    
    return script.strip()

def fix_script_format_for_multi_voice(script: str) -> str:
    """
    Fix script format to ensure proper multi-voice structure with HOST:, EXPERT:, QUESTIONER: labels
    Converts narrative format to proper dialogue format
    """
    print(f"🔧 FIXING SCRIPT FORMAT - Input length: {len(script)} chars")
    print(f"🔧 First 200 chars: {script[:200]}...")
    
    # Fix markdown formatting if present
    if "**HOST:**" in script or "**EXPERT:**" in script:
        print(f"🔧 Fixing markdown formatting (**HOST:** → HOST:)")
        script = re.sub(r'\*\*(HOST|EXPERT|QUESTIONER|CORRESPONDENT):\*\*', r'\1:', script)
    
    # Check if script already has proper speaker labels
    if re.search(r'^(HOST|EXPERT|QUESTIONER):', script, re.MULTILINE | re.IGNORECASE):
        print(f"🔧 Script already has proper speaker labels - no fix needed")
        return script  # Already in correct format
    
    print(f"🔧 Script needs format fixing - converting narrative to dialogue")
    
    # Split into sentences/paragraphs
    sentences = re.split(r'(?<=[.!?])\s+', script)
    print(f"🔧 Split into {len(sentences)} sentences")
    
    # Define speaker rotation
    speakers = ["HOST", "EXPERT", "QUESTIONER"]
    speaker_index = 0
    
    formatted_script = []
    
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:  # Skip very short sentences
            continue
            
        # Clean the sentence
        sentence = re.sub(r'\s+', ' ', sentence)
        sentence = sentence.strip()
        
        if sentence:
            speaker = speakers[speaker_index % len(speakers)]
            formatted_script.append(f"{speaker}: {sentence}")
            speaker_index += 1
            
            if i < 5:  # Log first few conversions
                print(f"🔧 Sentence {i+1}: {speaker}: {sentence[:50]}...")
    
    # Join with line breaks
    result = '\n\n'.join(formatted_script)
    
    # Ensure it starts with HOST
    if not result.startswith('HOST:'):
        result = 'HOST: ' + result
    
    print(f"🔧 Format fix complete - Output length: {len(result)} chars")
    print(f"🔧 First 200 chars: {result[:200]}...")
    
    return result

def add_missing_speakers(script: str, existing_speakers: set) -> str:
    """
    Add missing speakers to ensure proper panel discussion format
    """
    # Define speaker names for different roles
    speaker_names = {
        'host': ['Sarah', 'Marcus', 'Elena'],
        'expert': ['Dr. Maya', 'Professor James', 'Dr. Sophia'],
        'questioner': ['Tom', 'Noah', 'Aisha']
    }
    
    # Count existing speakers
    host_count = sum(1 for s in existing_speakers if 'host' in s.lower())
    expert_count = sum(1 for s in existing_speakers if 'expert' in s.lower())
    questioner_count = sum(1 for s in existing_speakers if 'questioner' in s.lower())
    
    # Add missing speakers by inserting natural dialogue
    lines = script.split('\n')
    new_lines = []
    
    for line in lines:
        new_lines.append(line)
        
        # If we need more speakers, add natural transitions
        if len(existing_speakers) < 3:
            if 'HOST:' in line.upper() and expert_count == 0:
                new_lines.append("EXPERT: That's a fascinating point. Let me add that quantum entanglement represents one of the most profound mysteries in physics.")
                expert_count += 1
                existing_speakers.add('expert')
            elif 'EXPERT:' in line.upper() and questioner_count == 0:
                new_lines.append("QUESTIONER: I'm curious about the practical applications. How does this affect our understanding of quantum computing?")
                questioner_count += 1
                existing_speakers.add('questioner')
    
    return '\n'.join(new_lines)

def validate_script_quality(script: str) -> Dict[str, any]:
    """
    Validate script quality and return metrics
    """
    issues = []
    warnings = []
    
    # Check for DOI numbers in script
    if re.search(r'10\.\d{4}/[^\s]+', script):
        issues.append("DOIs found in spoken script")
    
    # Check for proper speaker distribution
    speaker_counts = {}
    for line in script.split('\n'):
        for speaker in ['host', 'expert', 'questioner', 'correspondent']:
            if re.match(f'^{speaker}:', line, re.IGNORECASE):
                speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
    
    if len(speaker_counts) < 2:
        issues.append("Insufficient speaker variety")
    elif len(speaker_counts) < 3:
        warnings.append("Limited speaker variety for interview format")
    
    # Check for natural speech patterns
    if re.search(r'\b(Dr\.|Professor|PhD)\b', script):
        warnings.append("Academic titles found in script")
    
    return {
        'issues': issues,
        'warnings': warnings,
        'speaker_distribution': speaker_counts,
        'quality_score': max(0, 100 - len(issues) * 20 - len(warnings) * 10)
    }

def generate_relevant_hashtags(topic: str, category: str, title: str = "", description: str = "") -> str:
    """
    Generate 10-15 relevant, specific hashtags that will attract the target audience
    Based on topic, category, title, and description content
    
    Rules:
    - Max 20 characters per hashtag (excluding #)
    - Extract key concepts from topic/description
    - Prioritize specific technical terms over generic terms
    - Generate topic-specific compound hashtags (e.g., #SupramolecularChemistry, #SelfAssembly)
    """
    # Base hashtags (reduced to allow more topic-specific ones)
    base_hashtags = ["#CopernicusAI", "#SciencePodcast", "#ResearchInsights"]
    
    # Generate topic-specific compound hashtags
    topic_specific_hashtags = []
    
    # Extract key technical terms from topic
    # Scan topic + title only. The generated description often invents
    # downstream applications (CRISPR, cancer) that the source paper never
    # discussed; tagging those pulls the episode off the paper.
    all_text = f"{topic} {title}".lower()
    compound_terms = {
        # Chemistry terms
        "supramolecular": "#SupramolecularChemistry",
        "self-assembly": "#SelfAssembly",
        "molecular": "#MolecularScience",
        "metalloenzyme": "#Metalloenzymes",
        "bioinspired": "#Bioinspired",
        "catalysis": "#Catalysis",
        "host-guest": "#HostGuest",
        "nanotechnology": "#Nanotechnology",
        "drug delivery": "#DrugDelivery",
        "materials science": "#MaterialsScience",
        
        # Biology terms
        "epigenetic": "#Epigenetics",
        "immunotherapy": "#Immunotherapy",
        "cancer": "#CancerResearch",
        "car-t": "#CART",
        "personalized": "#PersonalizedMedicine",
        "vaccine": "#Vaccine",
        "gene editing": "#GeneEditing",
        "crispr": "#CRISPR",
        
        # Computer Science terms
        "federated learning": "#FederatedLearning",
        "graph neural": "#GraphNeuralNets",
        "machine learning": "#MachineLearning",
        "artificial intelligence": "#AI",
        "deep learning": "#DeepLearning",
        "neural network": "#NeuralNetworks",
        "privacy": "#PrivacyPreserving",
        
        # Mathematics terms
        "topological data": "#TopologicalData",
        "persistent homology": "#PersistentHomology",
        "optimization": "#Optimization",
        "gradient-free": "#GradientFree",
        "evolutionary": "#EvolutionaryAlgorithms",
        
        # Physics terms
        "quantum sensing": "#QuantumSensing",
        "topological phases": "#TopologicalPhases",
        "majorana": "#MajoranaFermions",
        "quantum": "#QuantumPhysics",
        "condensed matter": "#CondensedMatter",
    }
    
    # Scan topic + title only. The generated description often invents
    # downstream applications (CRISPR, cancer) that the source paper never
    # discussed; tagging those pulls the episode off the paper.
    all_text = f"{topic} {title}".lower()
    for term, hashtag in compound_terms.items():
        if term.lower() in all_text and hashtag not in topic_specific_hashtags:
            if len(hashtag) <= 21:  # 20 chars + #
                topic_specific_hashtags.append(hashtag)
    
    # Do not mint hashtags from arbitrary title/topic words (#Identifying).
    # Category tags plus matched technical compounds are enough.
    
    # Category-based hashtags (select 1-2 most relevant)
    category_hashtags = {
        "Computer Science": ["#ComputerScience", "#TechResearch", "#AI", "#MachineLearning"],
        "Physics": ["#Physics", "#QuantumPhysics", "#TheoreticalPhysics", "#ExperimentalPhysics"],
        "Biology": ["#Biology", "#Biotech", "#Genomics", "#Biomedical"],
        "Chemistry": ["#Chemistry", "#Biochemistry", "#MaterialsScience", "#ChemicalEngineering"],
        "Mathematics": ["#Mathematics", "#AppliedMath", "#Statistics", "#DataScience"],
        "Engineering": ["#Engineering", "#BiomedicalEngineering", "#Robotics", "#Automation"],
        "Medicine": ["#Medicine", "#MedicalResearch", "#Healthcare", "#Biomedical"],
        "Psychology": ["#Psychology", "#CognitiveScience", "#BehavioralScience", "#Neuroscience"],
        "Economics": ["#Economics", "#BehavioralEconomics", "#DataScience", "#PolicyResearch"],
        "Environmental Science": ["#EnvironmentalScience", "#ClimateScience", "#Sustainability", "#Ecology"]
    }
    
    # Get 1-2 most relevant category-specific hashtags
    cat_hashtags = category_hashtags.get(category, ["#Science", "#Research"])[:2]
    
    # Extract additional specific technical terms from description
    additional_hashtags = []
    
    # Extended list of technical terms that make good hashtags
    technical_term_mapping = {
        # Chemistry/Biochemistry specific
        "supramolecular chemistry": "#SupramolecularChem",
        "self-assembly": "#SelfAssembly",
        "host-guest interactions": "#HostGuest",
        "molecular self-assembly": "#MolecularAssembly",
        "metalloenzymes": "#Metalloenzymes",
        "bioinspired catalysis": "#Bioinspired",
        "sustainable": "#SustainableChem",
        "green chemistry": "#GreenChemistry",
        "nanotechnology": "#Nanotechnology",
        "nanomaterials": "#Nanomaterials",
        "drug delivery": "#DrugDelivery",
        "materials science": "#MaterialsScience",
        "catalysis": "#Catalysis",
        "synthetic": "#Synthetic",
        "polymer": "#Polymer",
        
        # Biology specific
        "epigenetic": "#Epigenetics",
        "immunotherapy": "#Immunotherapy",
        "car-t": "#CART",
        "personalized medicine": "#PersonalizedMed",
        "cancer research": "#CancerResearch",
        "oncology": "#Oncology",
        "regenerative": "#Regenerative",
        "stem cell": "#StemCells",
        "protein": "#Proteins",
        "enzyme": "#Enzymes",
        "metabolism": "#Metabolism",
        
        # Computer Science specific
        "federated learning": "#FederatedLearning",
        "graph neural networks": "#GraphNeuralNets",
        "privacy-preserving": "#PrivacyPreserving",
        "differential privacy": "#DifferentialPrivacy",
        "secure aggregation": "#SecureAggregation",
        "machine learning": "#MachineLearning",
        "deep learning": "#DeepLearning",
        "neural networks": "#NeuralNetworks",
        "artificial intelligence": "#AI",
        
        # Mathematics specific
        "topological data analysis": "#TopologicalData",
        "persistent homology": "#PersistentHomology",
        "optimization": "#Optimization",
        "evolutionary algorithms": "#EvolutionaryAlg",
        "gradient-free": "#GradientFree",
        
        # Physics specific
        "quantum sensing": "#QuantumSensing",
        "quantum metrology": "#QuantumMetrology",
        "topological phases": "#TopologicalPhases",
        "majorana fermions": "#MajoranaFermions",
        "topological insulators": "#TopologicalInsul",
        "condensed matter": "#CondensedMatter",
        "quantum computing": "#QuantumComputing",
        
        # General technical terms
        "computational": "#Computational",
        "theoretical": "#Theoretical",
        "experimental": "#Experimental",
        "analytical": "#Analytical",
    }
    
    # PRIORITIZE title-specific hashtags - extract key terms directly from title
    title_lower = title.lower() if title else ""
    title_words = [w.strip('.,!?;:()[]') for w in title.split() if len(w.strip()) > 3]
    
    # Extract compound phrases from title
    title_compound_hashtags = []
    if len(title_words) >= 2:
        # Look for 2-3 word phrases in title that make good hashtags
        for i in range(len(title_words) - 1):
            phrase = f"{title_words[i]} {title_words[i+1]}"
            # Check if this phrase matches any technical term
            if phrase.lower() in technical_term_mapping:
                hashtag = technical_term_mapping[phrase.lower()]
                if hashtag not in topic_specific_hashtags and len(hashtag) <= 21:
                    title_compound_hashtags.append(hashtag)
    
    # Do not turn arbitrary title words into hashtags (#Unraveling, #Identifying).
    title_specific_words = []

    # Check for technical terms in text (prioritize title matches)
    for term, hashtag in technical_term_mapping.items():
        # Prioritize if found in title
        found_in_title = term.lower() in title_lower
        found_in_all = term.lower() in all_text
        
        if found_in_all and hashtag not in topic_specific_hashtags:
            if len(hashtag) <= 21:  # 20 chars + #
                # If found in title, add at the beginning
                if found_in_title:
                    additional_hashtags.insert(0, hashtag)
                else:
                    additional_hashtags.append(hashtag)
                if len(additional_hashtags) >= 8:  # Limit additional hashtags
                    break
    
    # Add significant individual words that aren't already covered (prioritize title words)
    for word in title_specific_words[:4]:
        if word not in topic_specific_hashtags and word not in additional_hashtags:
            additional_hashtags.insert(0, word)
    
    # Add title compound hashtags at the beginning
    for hashtag in title_compound_hashtags[:3]:
        if hashtag not in topic_specific_hashtags and hashtag not in additional_hashtags:
            additional_hashtags.insert(0, hashtag)
    
    # Combine all hashtags: base + category + topic-specific + additional
    all_hashtags = base_hashtags + cat_hashtags + topic_specific_hashtags[:5] + additional_hashtags
    
    # Remove duplicates while preserving order
    seen = set()
    unique_hashtags = []
    for tag in all_hashtags:
        if tag not in seen:
            seen.add(tag)
            unique_hashtags.append(tag)
    
    return " ".join(unique_hashtags[:15])

_PLACEHOLDER_DOI_RE = re.compile(r"DOI:\s*10\.xxxx/xxxx", re.IGNORECASE)
_SECTION_PLACEHOLDER_DOI_RE = re.compile(r"(?i)section\s+DOI:\s*10\.xxxx/xxxx")
_RECENT_YEAR_RE = re.compile(r"\(Recent\)", re.IGNORECASE)
_BARE_YEAR_PLACEHOLDER_RE = re.compile(r"\(Year\)", re.IGNORECASE)


def sanitize_reference_placeholders(text: str, known_year: Optional[str] = None) -> str:
    """Strip invented citation tokens the model copies from prompt examples.

    Never leave `DOI: 10.xxxx/xxxx` or `(Recent)` in reader-facing copy. A real
    four-digit year, if known, replaces `(Recent)`; otherwise the parenthetical
    is dropped. Markdown section headers that got concatenated onto truncated
    prose are put back on their own lines.
    """
    if not text:
        return text
    text = _SECTION_PLACEHOLDER_DOI_RE.sub("", text)
    text = _PLACEHOLDER_DOI_RE.sub("", text)
    text = _BARE_YEAR_PLACEHOLDER_RE.sub("", text)
    if known_year and re.fullmatch(r"\d{4}", known_year):
        text = _RECENT_YEAR_RE.sub(f"({known_year})", text)
    else:
        text = _RECENT_YEAR_RE.sub("", text)
    text = re.sub(r"[ \t]+DOI:\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[^\S\n]{2,}", " ", text)
    text = re.sub(
        r"([^\n])(## (?:References|Hashtags|Episode Details|Key Concepts Explored|Research Insights|Practical Applications|Future Directions))",
        r"\1\n\n\2",
        text,
    )
    text = re.sub(r"\n[ \t]*Hashtags\b", "\n## Hashtags", text)
    return text


def join_description_sections(main: str, *sections: str) -> str:
    """Join body + References/Hashtags with blank lines so headers never mash."""
    parts = []
    if main and main.strip():
        parts.append(main.rstrip())
    for section in sections:
        if section and str(section).strip():
            parts.append(str(section).strip())
    return "\n\n".join(parts)


def validate_academic_references(references_text: str) -> str:
    """Normalize reference lines. Never invent a DOI or a year."""
    if not references_text:
        return references_text

    references_text = sanitize_reference_placeholders(references_text)
    references = [ref.strip() for ref in references_text.split("\n") if ref.strip()]
    improved_refs = []
    for ref in references:
        ref = ref.replace("[", "").replace("]", "").strip()
        if not ref or ref.lower() in {"section", "section doi:"}:
            continue
        improved_refs.append(ref)
    return "\n".join(improved_refs)


INDEX_VENUE_NAMES = {
    "pubmed",
    "arxiv",
    "biorxiv",
    "medrxiv",
    "pmc",
    "europe pmc",
    "google scholar",
    "nasa ads",
    "zenodo",
    "core",
    "crossref",
}

_INDEX_PUBLISHED_IN_RE = re.compile(
    r"(?i)published\s+in\s+\*?(pubmed|arxiv|biorxiv|medrxiv|pmc)\*?"
)
_INDEX_DOT_VENUE_RE = re.compile(
    r"(?i)\.\s*(pubmed|arxiv|biorxiv|medrxiv|pmc)\s*\."
)


def spoken_journal_name(journal: Optional[str]) -> Optional[str]:
    """Reader/spoken venue. None if missing or an index name."""
    j = (journal or "").strip()
    if not j or j.lower() in INDEX_VENUE_NAMES:
        return None
    low = j.lower()
    if low.startswith("proceedings of the national academy"):
        return "the Proceedings of the National Academy of Sciences"
    return j


def rewrite_index_venues(text: str, journal: Optional[str] = None) -> str:
    """Stop PubMed/arXiv being spoken or listed as the journal.

    'published in pubmed' becomes 'published in {journal}' when we have a real
    venue, otherwise just 'published'. Trailing '. pubmed.' / '. arxiv.' in
    reference lines is dropped so we do not stamp the source paper's journal
    onto every related paper.
    """
    if not text:
        return text
    spoken = spoken_journal_name(journal)
    if spoken:
        text = _INDEX_PUBLISHED_IN_RE.sub(f"published in {spoken}", text)
    else:
        text = _INDEX_PUBLISHED_IN_RE.sub("published", text)
    text = _INDEX_DOT_VENUE_RE.sub(".", text)
    return text


def format_research_source_line(source) -> str:
    """One markdown reference line. Never use pubmed/arxiv as the venue."""
    if isinstance(source, dict):
        authors = source.get("authors") or []
        title = (source.get("title") or "").strip()
        journal = source.get("journal")
        index_name = source.get("source")
        doi = source.get("doi")
        url = source.get("url")
        pub = source.get("publication_date") or source.get("year") or ""
    else:
        authors = getattr(source, "authors", None) or []
        title = (getattr(source, "title", None) or "").strip()
        journal = getattr(source, "journal", None)
        index_name = getattr(source, "source", None)
        doi = getattr(source, "doi", None)
        url = getattr(source, "url", None)
        pub = getattr(source, "publication_date", None) or ""

    if isinstance(authors, str):
        author_str = authors
    else:
        names = [str(a) for a in authors if a]
        author_str = ", ".join(names[:2]) + (" et al." if len(names) > 2 else "")

    year = ""
    pub_s = str(pub).strip()
    if re.match(r"^\d{4}", pub_s):
        year = pub_s[:4]

    venue = spoken_journal_name(journal)
    if not venue:
        venue = None  # omit index names

    line = f"* {author_str}. {title}".strip()
    if year:
        line += f" ({year})"
    if venue:
        line += f". {venue}"
    line += "."
    if doi:
        line += f" DOI: {doi}"
    elif url:
        line += f" Available: {url}"
    return line


def ensure_source_paper_reference(description: str, citation: str) -> str:
    """Put the KE source-paper citation first in ## References."""
    if not description:
        return description
    citation = (citation or "").strip()
    if not citation:
        return description
    if not citation.startswith(("*", "-", "•")):
        citation = f"* {citation}"

    if "## References" not in description:
        return description.rstrip() + "\n\n## References\n" + citation

    before, after = description.split("## References", 1)
    if "##" in after:
        refs, rest = after.split("##", 1)
        tail = "##" + rest
    else:
        refs, tail = after, ""

    refs_body = refs.strip()
    marker = citation.split("DOI:")[-1].strip() if "DOI:" in citation else citation[2:40]
    if marker and marker in refs_body:
        # already present; still move a matching line first if needed
        return description
    return before + "## References\n" + citation + "\n" + refs_body + ("\n\n" + tail if tail else "")


def dalle_thumbnail_attempts(title: str, topic: str) -> list:
    """Image API payloads to try before the geometric fallback.

    dall-e-3 is gone on this OpenAI account (`The model 'dall-e-3' does not exist`).
    Use gpt-image-1 / gpt-image-1-mini with low/medium quality, no style param.
    """
    topic_bit = (topic or title or "scientific research").strip()[:160]
    title_bit = (title or topic_bit).strip()[:120]
    compact = (
        f"Abstract scientific illustration for a research podcast titled '{title_bit}'. "
        f"Subject: {topic_bit}. Geometric molecular or cellular motifs, cinematic lighting, "
        "deep blue and emerald, no photorealistic people, no living tissue, no blood, "
        "no text, no letters, no labels, no watermarks."
    )
    shorter = (
        "Abstract square scientific artwork of a DNA helix and molecular geometry, "
        "deep cosmic blue and emerald green, cinematic light, no text, no letters, no labels."
    )
    return [
        {"model": "gpt-image-1", "quality": "medium", "prompt": compact[:1000]},
        {"model": "gpt-image-1", "quality": "low", "prompt": shorter},
        {"model": "gpt-image-1-mini", "quality": "medium", "prompt": shorter},
    ]


# TTS-only name respellings. Do NOT run on stored scripts, transcripts, or
# descriptions — those must keep the scholarly spelling (Gödel / Godel / Kleene).
# Applied in ElevenLabsVoiceService._preprocess_text_for_natural_speech.
# Apostrophe class covers ASCII ' and Unicode right single quotation mark.
_TTS_POSSESSIVE = r"(?:['\u2019]s)?"
_TTS_PRONUNCIATION_PATTERNS = (
    # Gödel / Godel / Goedel → English "girdle" (GER-dl / ˈɡɜːrdəl)
    (re.compile(rf"\bG(?:ö|oe|o)del{_TTS_POSSESSIVE}\b", re.IGNORECASE), "Girdle"),
    # Kleene → "cleanee" / KLAY-nee / ˈkleɪni
    (re.compile(rf"\bKleene{_TTS_POSSESSIVE}\b", re.IGNORECASE), "Klaynee"),
)


def apply_tts_pronunciation_hints(text: str) -> str:
    """Respell names ElevenLabs mispronounces. TTS audio only — not transcripts.

    Gödel/Godel/Goedel → Girdle; Kleene → Klaynee. Possessives are kept
    (Gödel's → Girdle's). Displayed scripts must still show the original names.
    """
    if not text:
        return text

    text = unicodedata.normalize("NFC", text)

    def _spoken(match: re.Match, alias: str) -> str:
        original = match.group(0)
        possessive = ""
        if original.endswith(("'s", "\u2019s")):
            possessive = original[-2:]
            stem = original[:-2]
        else:
            stem = original
        if stem.isupper():
            spoken = alias.upper()
        elif stem[:1].islower():
            spoken = alias.lower()
        else:
            spoken = alias
        return spoken + possessive

    for pattern, alias in _TTS_PRONUNCIATION_PATTERNS:
        text = pattern.sub(lambda m, spoken=alias: _spoken(m, spoken), text)
    return text


def expand_contractions_for_tts(script: str) -> str:
    """
    Expand contractions to avoid TTS pronunciation issues
    """
    # Common contractions that cause TTS issues
    contractions = {
        "it's": "it is",
        "can't": "cannot",
        "won't": "will not",
        "don't": "do not",
        "doesn't": "does not",
        "didn't": "did not",
        "haven't": "have not",
        "hasn't": "has not",
        "hadn't": "had not",
        "wouldn't": "would not",
        "shouldn't": "should not",
        "couldn't": "could not",
        "isn't": "is not",
        "aren't": "are not",
        "wasn't": "was not",
        "weren't": "were not",
        "I'm": "I am",
        "you're": "you are",
        "he's": "he is",
        "she's": "she is",
        "we're": "we are",
        "they're": "they are",
        "I've": "I have",
        "you've": "you have",
        "we've": "we have",
        "they've": "they have",
        "I'll": "I will",
        "you'll": "you will",
        "he'll": "he will",
        "she'll": "she will",
        "we'll": "we will",
        "they'll": "they will",
        "I'd": "I would",
        "you'd": "you would",
        "he'd": "he would",
        "she'd": "she would",
        "we'd": "we would",
        "they'd": "they would",
        "there's": "there is",
        "that's": "that is",
        "here's": "here is",
        "what's": "what is",
        "who's": "who is",
        "where's": "where is",
        "when's": "when is",
        "why's": "why is",
        "how's": "how is"
    }
    
    # Replace contractions with expanded forms
    for contraction, expanded in contractions.items():
        script = script.replace(contraction, expanded)
        script = script.replace(contraction.capitalize(), expanded.capitalize())
    
    return script

def apply_content_fixes(script: str, topic: str) -> str:
    """
    Apply all content fixes to improve podcast quality
    """
    # Expand contractions for TTS compatibility
    script = expand_contractions_for_tts(script)
    
    # Remove DOIs from spoken content
    script = remove_dois_from_script(script)
    
    # Fix voice assignment for interview format
    script = fix_voice_assignment(script)
    
    # Add missing speakers if needed
    existing_speakers = extract_speakers_from_script(script)
    if len(existing_speakers) < 2:
        script = add_missing_speakers(script, existing_speakers)
    
    return script

def clean_placeholder_text_from_description(description: str) -> str:
    """
    Remove repeated placeholder text from descriptions.
    Detects and removes duplicate placeholder entries in Key Concepts sections.
    """
    if not description:
        return description
    
    # Placeholder texts to detect
    placeholder_patterns = [
        r"research findings require further analysis",
        r"methodology analysis pending",
        r"implications to be determined",
        r"analysis pending",
        r"further analysis required"
    ]
    
    # Find the Key Concepts section
    if "## Key Concepts Explored" not in description:
        return description
    
    # Split by Key Concepts section
    parts = description.split("## Key Concepts Explored")
    if len(parts) < 2:
        return description
    
    before_concepts = parts[0]
    after_concepts = "## Key Concepts Explored".join(parts[1:])
    
    # Extract the concepts section (until next section or end)
    next_section_markers = ["## Research Insights", "## Practical Applications", "## Future Directions", "## References", "## Episode Details", "## Hashtags"]
    
    concepts_section = after_concepts
    rest_of_description = ""
    
    for marker in next_section_markers:
        if marker in after_concepts:
            split_parts = after_concepts.split(marker, 1)
            concepts_section = split_parts[0]
            rest_of_description = marker + split_parts[1]
            break
    
    # Split into individual concept lines
    concept_lines = concepts_section.strip().split('\n')
    unique_concepts = []
    seen_texts = set()
    
    for line in concept_lines:
        line_stripped = line.strip()
        if not line_stripped or not line_stripped.startswith('-'):
            # Keep non-concept lines (empty lines, etc.)
            if line_stripped:
                unique_concepts.append(line)
            continue
        
        # Extract the concept text (everything after "- " or "- **")
        concept_text = re.sub(r'^-\s*\*\*?', '', line_stripped).strip()
        concept_text = re.sub(r'\*\*?:.*$', '', concept_text).strip()  # Remove ": explanation" part
        
        # Check if this is a placeholder
        is_placeholder = any(re.search(pattern, concept_text, re.IGNORECASE) for pattern in placeholder_patterns)
        
        # Check if we've seen this exact concept text before (case-insensitive)
        concept_key = concept_text.lower().strip()
        
        if is_placeholder or concept_key in seen_texts:
            # Skip placeholder text or duplicates
            continue
        
        seen_texts.add(concept_key)
        unique_concepts.append(line)
    
    # If we removed all concepts and left it empty, add a default
    if not any(line.strip().startswith('-') for line in unique_concepts):
        unique_concepts.insert(0, "- **Recent research developments**: Current studies are revealing new insights into fundamental mechanisms and processes.")
    
    # Reconstruct the description
    cleaned_concepts_section = '\n'.join(unique_concepts).strip()
    
    return before_concepts + "## Key Concepts Explored\n" + cleaned_concepts_section + "\n" + rest_of_description

def limit_description_length(description: str, max_length: int = 4000) -> str:
    """
    Limit description length to specified character count while preserving References and Hashtags sections.
    CRITICAL: References and Hashtags sections are ALWAYS preserved completely - never truncated.
    """
    if not description:
        return description

    description = sanitize_reference_placeholders(description)
    
    if len(description) <= max_length:
        return description
    
    # Split description into main content and preserved sections
    main_content = description
    references_section = ""
    hashtags_section = ""
    episode_details_section = ""
    
    # Extract References section (MUST be preserved completely)
    if '## References' in description:
        parts = description.split('## References', 1)
        main_content = parts[0].rstrip()
        ref_content = '## References' + parts[1]
        
        # Extract until next major section
        for marker in ['## Hashtags', '## Episode Details']:
            if marker in ref_content:
                split_parts = ref_content.split(marker, 1)
                references_section = split_parts[0].rstrip()
                ref_content = marker + split_parts[1]
                break
        else:
            references_section = ref_content.rstrip()
    
    # Extract Hashtags section from remaining content
    remaining_after_refs = description.split('## References', 1)[1] if '## References' in description else description
    if '## Hashtags' in remaining_after_refs:
        hashtags_parts = remaining_after_refs.split('## Hashtags', 1)
        hashtags_content = '## Hashtags' + hashtags_parts[1]
        if '## Episode Details' in hashtags_content:
            split_parts = hashtags_content.split('## Episode Details', 1)
            hashtags_section = split_parts[0].rstrip()
            episode_details_section = '## Episode Details' + split_parts[1].rstrip()
        else:
            hashtags_section = hashtags_content.rstrip()
    
    # Calculate space needed for preserved sections
    preserved_text = ""
    if references_section:
        preserved_text += '\n\n' + references_section if preserved_text else references_section
    if hashtags_section:
        preserved_text += '\n\n' + hashtags_section
    if episode_details_section:
        preserved_text += '\n\n' + episode_details_section
    
    preserved_length = len(preserved_text)
    available_space = max_length - preserved_length - 20  # 20 char buffer
    
    # If main content fits, return original
    if len(main_content) + preserved_length <= max_length:
        return description
    
    # Truncate main content to fit
    if len(main_content) > available_space:
        # Truncate at word boundary
        truncated = main_content[:available_space]
        # Find last space to avoid cutting words
        last_space = truncated.rfind(' ')
        if last_space > available_space * 0.9:  # Only use last_space if it's reasonably close
            truncated = truncated[:last_space]
        main_content = truncated.rstrip() + '...'
    
    # Reconstruct with preserved sections — always a blank line before ## headers.
    result = join_description_sections(
        main_content, references_section, hashtags_section, episode_details_section
    )
    
    # Final safety check
    if len(result) > max_length:
        # Last resort: truncate main content more aggressively, but STILL preserve references
        max_main_space = max_length - preserved_length - 10
        if max_main_space > 100:
            result = join_description_sections(
                main_content[:max_main_space].rstrip() + '...',
                references_section, hashtags_section, episode_details_section
            )
        else:
            result = join_description_sections(
                main_content[:100] + '...',
                references_section, hashtags_section, episode_details_section
            )
    
    return result

def extract_itunes_summary(description: str) -> str:
    """
    Extract the first paragraph as iTunes summary
    This should be engaging and under 255 characters
    Clean of HTML entities and unwanted symbols for Spotify compatibility
    """
    if not description:
        return ""
    
    # Get the first paragraph
    first_paragraph = description.split('\n\n')[0]
    
    # Clean up any markdown formatting
    first_paragraph = re.sub(r'#+\s*', '', first_paragraph)  # Remove headers
    first_paragraph = re.sub(r'\*\*(.*?)\*\*', r'\1', first_paragraph)  # Remove bold
    first_paragraph = re.sub(r'\*(.*?)\*', r'\1', first_paragraph)  # Remove italic
    
    # Remove HTML tags
    first_paragraph = re.sub(r'<[^>]+>', '', first_paragraph)
    
    # Remove HTML entities and unwanted symbols (similar to RSS cleaning)
    import html
    first_paragraph = html.unescape(first_paragraph)
    first_paragraph = first_paragraph.replace('&nbsp;', ' ')
    first_paragraph = first_paragraph.replace('\u201c', '"').replace('\u201d', '"')
    first_paragraph = first_paragraph.replace('\u2018', "'").replace('\u2019', "'")
    
    # Remove control characters
    first_paragraph = ''.join(char for char in first_paragraph if ord(char) >= 32 or char in '\n\t')
    
    # Limit to 255 characters for iTunes
    if len(first_paragraph) > 255:
        first_paragraph = first_paragraph[:252] + '...'
    
    return first_paragraph.strip()
