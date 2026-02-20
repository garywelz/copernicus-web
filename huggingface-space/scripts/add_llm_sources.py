#!/usr/bin/env python3
"""
Add LLM-Generated Research Paper Citations to Process JSON Files

Uses LLM to generate appropriate research paper citations for each process
based on the process name, description, and keywords.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

# Try to import Google Generative AI (Gemini) and Secrets Manager
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: google.generativeai not available. Will generate template sources.")

try:
    from google.cloud import secretmanager
    SECRETS_MANAGER_AVAILABLE = True
except ImportError:
    SECRETS_MANAGER_AVAILABLE = False
    print("Warning: google.cloud.secretmanager not available. Will try environment variable or manual setup.")

def get_gemini_api_key():
    """
    Get Gemini API key from Google Secrets Manager or environment variable.
    Returns API key string or None if not found.
    """
    # First try Secrets Manager
    if SECRETS_MANAGER_AVAILABLE:
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = "regal-scholar-453620-r7"
            secret_id = "GEMINI_API_KEY"  # Adjust if your secret has a different name
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            api_key = response.payload.data.decode("UTF-8")
            return api_key.strip()
        except Exception as e:
            print(f"⚠️  Could not access secret from Secrets Manager: {e}")
            print("   Falling back to environment variable...")
    
    # Fallback to environment variable
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        return api_key
    
    return None

def generate_citations_with_llm(process_name: str, description: str, keywords: List[str], 
                                  category: str, organism: Optional[str] = None) -> List[Dict]:
    """
    Use LLM to generate appropriate research paper citations for a process.
    Returns list of citation dictionaries matching GLMP format.
    """
    
    # Build prompt for LLM - matching GLMP style
    keywords_text = ", ".join(keywords[:5])
    organism_text = f"\nOrganism/Species: {organism}" if organism else ""
    
    prompt = f"""Generate 2-3 real, authoritative research paper citations for this scientific process:

Process: {process_name}
Category: {category}
Description: {description}
Keywords: {keywords_text}{organism_text}

Requirements:
1. Provide REAL, well-known papers from top-tier journals:
   - Biology: Nature, Science, Cell, PNAS, Annual Reviews, Journal of Biological Chemistry
   - Chemistry: JACS, Angewandte Chemie, Nature Chemistry, Chemical Reviews, ACS journals
   - Physics: Physical Review Letters, Nature Physics, Science, Reviews of Modern Physics
   - Computer Science: ACM/IEEE conferences, Nature, Science, Communications of the ACM
   - Mathematics: Annals of Mathematics, Inventiones Mathematicae, PNAS, Nature

2. Format citations EXACTLY like this GLMP example:
   "Umbarger HE. Biosynthesis of amino acids. Annu Rev Biochem. 1978. PubMed: 354503 DOI: 10.1146/annurev.bi.47.070178.002203"

3. Prioritize:
   - Classic foundational papers
   - Recent reviews when available
   - Papers with PubMed IDs (preferred for biology/biochemistry)
   - Papers with DOIs (all disciplines)

4. Be specific to the exact process described, not general topics

Output ONLY valid JSON array (no markdown, no code blocks):
[
  {{
    "title": "Paper title",
    "authors": "LastName, FI.",
    "journal": "Journal Name (abbreviated if standard)",
    "year": "YYYY",
    "pubmed": "XXXXXX or null",
    "doi": "10.xxxx/xxxxx or null",
    "url": "https://pubmed.ncbi.nlm.nih.gov/XXXXXX or https://doi.org/10.xxxx/xxxxx"
  }}
]"""

    if not GENAI_AVAILABLE:
        # Fallback: Generate template citations
        return generate_template_citations(process_name, category, organism)
    
    try:
        # Get API key from Secrets Manager or environment variable
        api_key = get_gemini_api_key()
        if not api_key:
            print(f"  ⚠️  No Gemini API key found. Skipping LLM generation for {process_name}.")
            return generate_template_citations(process_name, category, organism)
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        # Use latest available model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON from response (handle markdown code blocks or plain JSON)
        # Remove markdown code fences if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = response_text.strip()
        
        # Try to find JSON array
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                citations_json = json.loads(json_match.group(0))
                # Validate structure
                if isinstance(citations_json, list) and len(citations_json) > 0:
                    return citations_json
            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parse error for {process_name}: {e}")
        
        print(f"  ⚠️  Could not parse LLM response for {process_name}")
        print(f"      Response preview: {response_text[:200]}...")
        return generate_template_citations(process_name, category, organism)
            
    except Exception as e:
        print(f"  ⚠️  LLM error for {process_name}: {e}")
        return generate_template_citations(process_name, category, organism)

def generate_template_citations(process_name: str, category: str, organism: Optional[str] = None) -> List[Dict]:
    """
    Generate template citations when LLM is not available.
    These are placeholders that need to be filled in manually.
    """
    return [{
        "title": f"Research on {process_name}",
        "authors": "Author, A., et al.",
        "journal": "Journal Name (to be filled)",
        "year": "YYYY",
        "pubmed": None,
        "doi": None,
        "url": None,
        "relevance": f"Primary reference for {process_name}",
        "needs_review": True
    }]

def add_sources_to_json(json_file_path: Path, keep_methodology: bool = True):
    """
    Add LLM-generated research paper citations to a process JSON file.
    Keeps the methodology reference unless keep_methodology is False.
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if already has real paper citations (not just methodology)
    sources = data.get('sources', [])
    has_real_papers = False
    methodology_ref = None
    
    for source in sources:
        if source.get('journal') == 'CopernicusAI Knowledge Engine':
            methodology_ref = source
        elif source.get('doi') or source.get('pubmed') or (source.get('journal') and 'Knowledge Engine' not in source.get('journal', '')):
            has_real_papers = True
            break
    
    # If already has real papers, skip
    if has_real_papers and len(sources) > 1:
        return False
    
    # Generate citations
    process_name = data.get('name', '')
    description = data.get('description', '')
    keywords = data.get('keywords', [])
    category = data.get('category', '')
    organism = data.get('organism')
    
    print(f"  Generating citations for: {process_name}")
    
    llm_citations = generate_citations_with_llm(
        process_name, description, keywords, category, organism
    )
    
    # Build new sources list
    new_sources = []
    if keep_methodology and methodology_ref:
        new_sources.append(methodology_ref)
    new_sources.extend(llm_citations)
    
    data['sources'] = new_sources
    data['lastUpdated'] = "2026-01-08"
    
    # Write updated JSON
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return True

def main():
    import sys
    
    base_dir = Path("/home/gdubs/copernicus-web-public/huggingface-space")
    
    # Check for test mode
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    disciplines = ["biology", "chemistry", "physics", "computer-science", "mathematics"]
    
    print("=" * 60)
    print("Adding LLM-Generated Research Paper Citations")
    if test_mode:
        print("🧪 TEST MODE: Processing one example process")
    if dry_run:
        print("🔍 DRY RUN: Will not modify files")
    print("=" * 60)
    print()
    print("Note: This script uses Google Gemini API to generate citations.")
    print("API key will be retrieved from Google Secrets Manager (or environment variable).")
    print()
    
    # Test API key access
    if GENAI_AVAILABLE:
        api_key = get_gemini_api_key()
        if api_key:
            print(f"✅ Gemini API key found (length: {len(api_key)})")
        else:
            print("⚠️  No Gemini API key found. Will generate template citations.")
        print()
    if test_mode:
        print("Usage: python3 add_llm_sources.py [--test] [--dry-run]")
        print("  --test / -t: Process only one example process")
        print("  --dry-run / -d: Show what would be updated without making changes")
        print()
    
    if not GENAI_AVAILABLE:
        print("⚠️  Warning: google.generativeai not installed.")
        print("   Install with: pip install google-generativeai")
        print("   Will generate template citations instead.")
        print()
    
    total_updated = 0
    
    # Process standard discipline databases
    for discipline in disciplines:
        db_dir = base_dir / f"{discipline}-processes-database"
        if not db_dir.exists():
            print(f"⚠️  Skipping {discipline}: directory not found")
            continue
        
        print(f"\nProcessing {discipline}...")
        json_files = list((db_dir / "processes").rglob("*.json"))
        
        if test_mode:
            # Process only first file in first discipline
            if json_files:
                json_files = [json_files[0]]
                print(f"  Test mode: Processing only {json_files[0].name}")
        
        updated = 0
        for json_file in json_files:
            try:
                if dry_run:
                    # Just check what would be updated
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    sources = data.get('sources', [])
                    has_real = any(s.get('doi') or s.get('pubmed') or 
                                 (s.get('journal') and 'Knowledge Engine' not in s.get('journal', '')) 
                                 for s in sources if s.get('journal') != 'CopernicusAI Knowledge Engine')
                    if not has_real:
                        print(f"    Would update: {json_file.name}")
                        updated += 1
                    else:
                        print(f"    Would skip (has citations): {json_file.name}")
                elif add_sources_to_json(json_file):
                    updated += 1
                    print(f"    ✓ Updated: {json_file.name}")
                else:
                    print(f"    - Skipped (already has citations): {json_file.name}")
            except Exception as e:
                print(f"    ✗ Error updating {json_file.name}: {e}")
        
        total_updated += updated
        if not dry_run:
            print(f"  Updated {updated}/{len(json_files)} files")
        else:
            print(f"  Would update {updated}/{len(json_files)} files")
        
        if test_mode:
            break  # Only process first discipline in test mode
    
    # Process Programming Framework biology database
    pf_bio_dir = base_dir / "programming-framework" / "biology-processes-database"
    if pf_bio_dir.exists():
        print(f"\nProcessing programming-framework/biology...")
        json_files = list((pf_bio_dir / "processes").rglob("*.json"))
        
        if test_mode and total_updated == 0:
            # If test mode and nothing processed yet, process first file
            if json_files:
                json_files = [json_files[0]]
                print(f"  Test mode: Processing only {json_files[0].name}")
        elif test_mode:
            json_files = []  # Skip if already processed one in test mode
        
        updated = 0
        for json_file in json_files:
            try:
                if dry_run:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    sources = data.get('sources', [])
                    has_real = any(s.get('doi') or s.get('pubmed') or 
                                 (s.get('journal') and 'Knowledge Engine' not in s.get('journal', '')) 
                                 for s in sources if s.get('journal') != 'CopernicusAI Knowledge Engine')
                    if not has_real:
                        print(f"    Would update: {json_file.name}")
                        updated += 1
                    else:
                        print(f"    Would skip (has citations): {json_file.name}")
                elif add_sources_to_json(json_file):
                    updated += 1
                    print(f"    ✓ Updated: {json_file.name}")
                else:
                    print(f"    - Skipped (already has citations): {json_file.name}")
            except Exception as e:
                print(f"    ✗ Error updating {json_file.name}: {e}")
        
        total_updated += updated
        if not dry_run:
            print(f"  Updated {updated}/{len(json_files)} files")
        else:
            print(f"  Would update {updated}/{len(json_files)} files")
    
    # Process GLMP database
    glmp_dir = base_dir / "glmp-processes-database"
    if glmp_dir.exists():
        print(f"\nProcessing GLMP...")
        json_files = [f for f in (glmp_dir / "processes").rglob("*.json") if f.name != "metadata.json"]
        
        if test_mode and total_updated == 0:
            # If test mode and nothing processed yet, process first file
            if json_files:
                json_files = [json_files[0]]
                print(f"  Test mode: Processing only {json_files[0].name}")
        elif test_mode:
            json_files = []  # Skip if already processed one in test mode
        
        updated = 0
        for json_file in json_files:
            try:
                if dry_run:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    sources = data.get('sources', [])
                    has_real = any(s.get('doi') or s.get('pubmed') or 
                                 (s.get('journal') and 'Knowledge Engine' not in s.get('journal', '')) 
                                 for s in sources if s.get('journal') != 'CopernicusAI Knowledge Engine')
                    if not has_real:
                        print(f"    Would update: {json_file.name}")
                        updated += 1
                    else:
                        print(f"    Would skip (has citations): {json_file.name}")
                elif add_sources_to_json(json_file):
                    updated += 1
                    print(f"    ✓ Updated: {json_file.name}")
                else:
                    print(f"    - Skipped (already has citations): {json_file.name}")
            except Exception as e:
                print(f"    ✗ Error updating {json_file.name}: {e}")
        
        total_updated += updated
        if not dry_run:
            print(f"  Updated {updated}/{len(json_files)} files")
        else:
            print(f"  Would update {updated}/{len(json_files)} files")
    
    print()
    print("=" * 60)
    print(f"Total files updated: {total_updated}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review generated citations for accuracy")
    print("2. Verify PubMed IDs and DOIs are correct")
    print("3. Update any placeholder citations with real papers")
    print("4. Regenerate HTML viewers with updated sources")

if __name__ == "__main__":
    main()
