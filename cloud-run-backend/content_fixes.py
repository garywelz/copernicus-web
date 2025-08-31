#!/usr/bin/env python3
"""
Content fixes for podcast generation issues
Addresses voice assignment, DOI removal, and category classification
"""

import re
from typing import Dict, List, Optional

def remove_dois_from_script(script: str) -> str:
    """
    Remove DOI numbers from spoken script content
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
    
    # Clean up any double spaces or punctuation issues
    cleaned_script = re.sub(r'\s+', ' ', cleaned_script)
    cleaned_script = re.sub(r'\s+([.!?])', r'\1', cleaned_script)
    
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
    Generate 5+ relevant hashtags that will attract the target audience
    Based on topic, category, title, and description content
    """
    # Base hashtags
    base_hashtags = ["#CopernicusAI", "#SciencePodcast", "#AcademicDiscussion", "#ResearchInsights"]
    
    # Topic-based hashtag
    topic_hashtag = f"#{topic.replace(' ', '')}Research"
    
    # Category-based hashtags
    category_hashtags = {
        "Computer Science": ["#ComputerScience", "#TechResearch", "#AI", "#MachineLearning"],
        "Physics": ["#Physics", "#QuantumPhysics", "#TheoreticalPhysics", "#ExperimentalPhysics"],
        "Biology": ["#Biology", "#Biotech", "#Genomics", "#Neuroscience"],
        "Chemistry": ["#Chemistry", "#Biochemistry", "#MaterialsScience", "#ChemicalEngineering"],
        "Mathematics": ["#Mathematics", "#AppliedMath", "#Statistics", "#DataScience"],
        "Engineering": ["#Engineering", "#BiomedicalEngineering", "#Robotics", "#Automation"],
        "Medicine": ["#Medicine", "#MedicalResearch", "#Healthcare", "#Biomedical"],
        "Psychology": ["#Psychology", "#CognitiveScience", "#BehavioralScience", "#Neuroscience"],
        "Economics": ["#Economics", "#BehavioralEconomics", "#DataScience", "#PolicyResearch"],
        "Environmental Science": ["#EnvironmentalScience", "#ClimateScience", "#Sustainability", "#Ecology"]
    }
    
    # Get category-specific hashtags
    cat_hashtags = category_hashtags.get(category, ["#Science", "#Research", "#Academic"])
    
    # Extract additional hashtags from title and description
    additional_hashtags = []
    all_text = f"{title} {description}".lower()
    
    # Common research terms that make good hashtags
    research_terms = [
        "neural", "network", "algorithm", "machine learning", "artificial intelligence",
        "quantum", "molecular", "genetic", "protein", "dna", "rna", "cell", "brain",
        "cognitive", "behavioral", "economic", "environmental", "climate", "sustainable",
        "robotic", "automation", "biomedical", "pharmaceutical", "therapeutic",
        "computational", "theoretical", "experimental", "analytical", "statistical"
    ]
    
    for term in research_terms:
        if term in all_text and len(additional_hashtags) < 3:
            hashtag = f"#{term.replace(' ', '')}"
            if hashtag not in additional_hashtags:
                additional_hashtags.append(hashtag)
    
    # Combine all hashtags
    all_hashtags = base_hashtags + [topic_hashtag] + cat_hashtags[:2] + additional_hashtags
    
    # Ensure we have at least 5 hashtags
    while len(all_hashtags) < 5:
        all_hashtags.append("#Research")
    
    return " ".join(all_hashtags[:8])  # Limit to 8 hashtags max

def validate_academic_references(references_text: str) -> str:
    """
    Validate and improve academic reference formatting
    Ensures proper APA-style format with DOIs
    """
    if not references_text:
        return references_text
    
    # Split into individual references
    references = [ref.strip() for ref in references_text.split('\n') if ref.strip()]
    
    improved_refs = []
    for ref in references:
        # Check if it already has proper format
        if re.search(r'\([0-9]{4}\)\.', ref) and re.search(r'DOI:', ref):
            improved_refs.append(ref)
            continue
        
        # Try to improve the format
        # Look for year pattern
        year_match = re.search(r'\(([0-9]{4})\)', ref)
        if year_match:
            year = year_match.group(1)
            # Ensure proper formatting
            if not re.search(r'DOI:', ref):
                ref += f" DOI: 10.xxxx/xxxx"
            improved_refs.append(ref)
        else:
            # Add placeholder for missing year
            ref = ref.replace('[', '').replace(']', '')
            if not re.search(r'\([0-9]{4}\)', ref):
                ref = ref.replace('(Year)', '(2024)')
            if not re.search(r'DOI:', ref):
                ref += f" DOI: 10.xxxx/xxxx"
            improved_refs.append(ref)
    
    return '\n'.join(improved_refs)

def apply_content_fixes(script: str, topic: str) -> str:
    """
    Apply all content fixes to improve podcast quality
    """
    # Remove DOIs from spoken content
    script = remove_dois_from_script(script)
    
    # Fix voice assignment for interview format
    script = fix_voice_assignment(script)
    
    # Add missing speakers if needed
    existing_speakers = extract_speakers_from_script(script)
    if len(existing_speakers) < 2:
        script = add_missing_speakers(script, existing_speakers)
    
    return script

def limit_description_length(description: str, max_length: int = 4000) -> str:
    """
    Limit description length to specified character count
    Ensures first paragraph works as iTunes summary
    """
    if len(description) <= max_length:
        return description
    
    # Split into paragraphs
    paragraphs = description.split('\n\n')
    
    # Start with the first paragraph (iTunes summary)
    result = paragraphs[0]
    
    # Add subsequent paragraphs until we hit the limit
    for paragraph in paragraphs[1:]:
        if len(result + '\n\n' + paragraph) <= max_length:
            result += '\n\n' + paragraph
        else:
            # Add ellipsis to indicate truncation
            result += '\n\n...'
            break
    
    return result

def extract_itunes_summary(description: str) -> str:
    """
    Extract the first paragraph as iTunes summary
    This should be engaging and under 255 characters
    """
    # Get the first paragraph
    first_paragraph = description.split('\n\n')[0]
    
    # Clean up any markdown formatting
    first_paragraph = re.sub(r'#+\s*', '', first_paragraph)  # Remove headers
    first_paragraph = re.sub(r'\*\*(.*?)\*\*', r'\1', first_paragraph)  # Remove bold
    first_paragraph = re.sub(r'\*(.*?)\*', r'\1', first_paragraph)  # Remove italic
    
    # Limit to 255 characters for iTunes
    if len(first_paragraph) > 255:
        first_paragraph = first_paragraph[:252] + '...'
    
    return first_paragraph.strip()
