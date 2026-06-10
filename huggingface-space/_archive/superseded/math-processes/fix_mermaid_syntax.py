#!/usr/bin/env python3
"""
Fix Mermaid Syntax Errors in All Mathematics Processes

Fixes common issues:
1. Invalid node syntax like /\"...\"/ or (/\"...\"/)
2. Invalid class assignments like :::red, :::yellow
3. Corrupted entities arrays
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

def fix_mermaid_syntax(mermaid_code: str) -> str:
    """Fix common Mermaid syntax errors."""
    if not mermaid_code:
        return ""
    
    # Fix invalid node syntax patterns:
    # When JSON is loaded, /\" becomes /"/ (backslash is consumed)
    # The LLM generated patterns like: [/"text"/ more text] which is invalid
    # We need to convert these to proper [text more text] format
    
    # Pattern 1: [/"text"/ more text] - convert to [text more text]
    # This handles cases where the node label has [/"text"/ followed by more text before ]
    mermaid_code = re.sub(r'\[/"([^"]+)"/\s+([^\]]+)\]', r'[\1 \2]', mermaid_code)
    
    # Pattern 2: [/"text"/] - convert to [text]
    mermaid_code = re.sub(r'\[/"([^"]+)"/\]', r'[\1]', mermaid_code)
    
    # Pattern 3: [/"text"/ at start of node (not closed yet)
    mermaid_code = re.sub(r'\[/"([^"]+)"/', r'[\1', mermaid_code)
    
    # Remove invalid class assignments like :::red, :::yellow, etc.
    mermaid_code = re.sub(r':::(red|yellow|green|blue|purple|orange|pink|gray|grey)\s*', '', mermaid_code)
    
    # Fix any remaining escaped quotes and newlines in node labels
    mermaid_code = re.sub(r'\\"', '', mermaid_code)
    mermaid_code = re.sub(r'\\n', ' ', mermaid_code)
    
    # Fix missing spaces before style statements
    mermaid_code = re.sub(r'\]style', ']\n    style', mermaid_code)
    mermaid_code = re.sub(r'\]-->', '] -->', mermaid_code)
    
    # Clean up extra whitespace
    mermaid_code = re.sub(r'\s+', ' ', mermaid_code)
    mermaid_code = re.sub(r'\n\s*\n+', '\n', mermaid_code)
    
    return mermaid_code.strip()

def extract_clean_entities(mermaid_code: str) -> list:
    """Extract clean entity names from Mermaid code."""
    if not mermaid_code:
        return []
    
    # Extract node labels from patterns like A1[Label], A1(Label), A1{Label}
    node_pattern = r'[A-Za-z0-9_]+\s*[\[\(\{]([^\]]+)[\]\)\}]'
    entities = re.findall(node_pattern, mermaid_code)
    
    # Clean up entities - remove quotes, escape sequences, etc.
    clean_entities = []
    for entity in entities:
        # Remove quotes and escape sequences
        entity = entity.replace('\\"', '').replace('"', '').strip()
        # Skip if it's just style or syntax
        if entity and not entity.startswith('style') and len(entity) > 2:
            clean_entities.append(entity)
    
    # Remove duplicates and limit to 30
    unique_entities = list(dict.fromkeys(clean_entities))[:30]
    return unique_entities

def fix_process_file(json_file: Path) -> bool:
    """Fix a single process JSON file."""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            process_data = json.load(f)
        
        original_mermaid = process_data.get('mermaid', '')
        
        # Check if file has syntax errors (has [/"/ pattern - JSON loads /\" as /"/)
        has_errors = '[/"/' in original_mermaid or ':::' in original_mermaid
        
        if has_errors:
            fixed_mermaid = fix_mermaid_syntax(original_mermaid)
            
            # Only update if there were changes
            if fixed_mermaid != original_mermaid:
                process_data['mermaid'] = fixed_mermaid
                
                # Fix entities array
                process_data['entities'] = extract_clean_entities(fixed_mermaid)
                
                # Save back
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(process_data, f, indent=2, ensure_ascii=False)
                
                return True
        return False
    except Exception as e:
        print(f"   ❌ Error fixing {json_file.name}: {e}")
        return False

def main():
    """Fix all process JSON files."""
    base_dir = Path(__file__).parent
    
    print("=" * 70)
    print("Fixing Mermaid Syntax Errors in All Processes")
    print("=" * 70)
    
    # Find all process JSON files
    json_files = []
    for subdir in base_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('.') and subdir.name != 'processes':
            json_files.extend(subdir.glob('*.json'))
    
    print(f"\nFound {len(json_files)} process files to check\n")
    
    fixed_count = 0
    error_count = 0
    
    for i, json_file in enumerate(json_files, 1):
        print(f"[{i}/{len(json_files)}] Checking: {json_file.name}")
        if fix_process_file(json_file):
            print(f"   ✅ Fixed syntax errors")
            fixed_count += 1
        else:
            print(f"   ✓ No errors found")
    
    print("\n" + "=" * 70)
    print("Fix Complete")
    print("=" * 70)
    print(f"✅ Fixed: {fixed_count} files")
    print(f"✓ Clean: {len(json_files) - fixed_count} files")
    print(f"❌ Errors: {error_count} files")
    
    if fixed_count > 0:
        print(f"\n🔄 Regenerating metadata and HTML pages...")
        from generate_metadata import main as generate_metadata_main
        generate_metadata_main()
        
        from create_individual_pages import main as create_pages_main
        create_pages_main()

if __name__ == '__main__':
    main()

