# Adding Research Paper Citations to Process Databases

This script uses Google Gemini LLM to generate appropriate research paper citations for all processes in the discipline databases.

## Purpose

Currently, all processes only have methodology references (Programming Framework). This script adds real research paper citations similar to GLMP format:

```
Umbarger HE. Biosynthesis of amino acids. Annu Rev Biochem. 1978. PubMed: 354503 DOI: 10.1146/annurev.bi.47.070178.002203
```

## Setup

### 1. Install Google Generative AI Package

```bash
pip install google-generativeai
```

### 2. Set API Key

Get your Gemini API key from: https://makersuite.google.com/app/apikey

Then set it as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or add to your `.bashrc`/`.zshrc`:

```bash
echo 'export GEMINI_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Run the Script

```bash
cd /home/gdubs/copernicus-web-public/huggingface-space
python3 scripts/add_llm_sources.py
```

## What It Does

1. **Scans all databases**: biology, chemistry, physics, computer-science, mathematics
2. **For each process**: 
   - Checks if it already has real paper citations (skips if yes)
   - Uses LLM to generate 2-3 relevant paper citations
   - Preserves the methodology reference
   - Adds new citations to the JSON file
3. **Citation format**: Matches GLMP style with PubMed/DOI when available

## Output

The script will:
- Update JSON files in place
- Preserve existing methodology references
- Add LLM-generated paper citations
- Print progress for each file

## After Running

1. **Review citations**: Check that generated papers are actually relevant
2. **Verify PubMed/DOIs**: Ensure links work and point to correct papers
3. **Manual curation**: Replace any inaccurate citations with real, verified papers
4. **Regenerate HTML viewers**: Run `create_process_viewers.py` to update HTML files with new sources

## Limitations

- LLM may generate plausible-sounding but incorrect citations
- Some processes may have better papers not found by LLM
- Manual review and curation is still required for publication-quality databases

## Example Citation Format

```json
{
  "title": "Biosynthesis of amino acids",
  "authors": "Umbarger, HE.",
  "journal": "Annu Rev Biochem",
  "year": "1978",
  "pubmed": "354503",
  "doi": "10.1146/annurev.bi.47.070178.002203",
  "url": "https://pubmed.ncbi.nlm.nih.gov/354503"
}
```
