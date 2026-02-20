#!/usr/bin/env python3
"""
Fix all Mermaid syntax problems in JSON files directly at the source.
This script applies the same fixes that create_individual_pages.py uses.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any

def clean_mermaid_syntax(mermaid_code: str) -> str:
    """
    Clean Mermaid syntax by removing problematic quote patterns.
    This is the same function used in create_individual_pages.py
    """
    if not mermaid_code:
        return ""
    
    # Fix unescaped quote patterns (after JSON parsing): /"text"/
    # Handle parentheses nodes: (/"text"/) -> (text)
    mermaid_code = re.sub(r'\(/"([^"]+)"/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/"text" /] or [/"text"/] or [/"text"\] -> [text]
    # Handle cases with optional text/characters between quote and closing bracket
    # Also handle patterns without / before ]: [/"text"\]
    mermaid_code = re.sub(r'\[/"([^"]+)"[^\]]*?/?\\?\]', r'[\1]', mermaid_code)
    # Also handle patterns that might have escaped quotes in JSON: [/\"text\"...]
    mermaid_code = re.sub(r'\[/\\"([^"]+)\\"[^\]]*?/?\\?\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/"text"/} or {/"text" /} -> {text}
    # Handle cases with optional text/characters between quote and closing brace
    mermaid_code = re.sub(r'\{/"([^"]+)"[^\}]*?/?\\?\}', r'{\1}', mermaid_code)
    
    # Also handle escaped quote patterns (in case they appear): /\"text\"/
    # Handle parentheses nodes: (/\"text\"/) -> (text)
    mermaid_code = re.sub(r'\(/\\"([^"]+)\\"/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/\"text\" /] or [/\"text\"/] -> [text]
    mermaid_code = re.sub(r'\[/\\"([^"]+)\\"\s*/\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/\"text\"/} -> {text}
    mermaid_code = re.sub(r'\{/\\"([^"]+)\\"/\}', r'{\1}', mermaid_code)
    
    # Remove invalid class assignments
    mermaid_code = re.sub(r'\]:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\):::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    mermaid_code = re.sub(r'\]::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\)::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    mermaid_code = re.sub(r'([\]\}\)]);::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'\1', mermaid_code)
    
    # Add spaces after node definitions
    mermaid_code = re.sub(r'([\)\]\}])([A-Z0-9])', r'\1 \2', mermaid_code)
    mermaid_code = re.sub(r'([\)\]\}])(style)', r'\1 \2', mermaid_code)
    
    # Convert parentheses nodes with nested parentheses to bracket nodes
    def convert_nested_parens(text):
        """Convert parentheses nodes with nested parens to bracket nodes."""
        result = []
        i = 0
        while i < len(text):
            match = re.match(r'([A-Z0-9]+)\(', text[i:])
            if match:
                node_id = match.group(1)
                start = i + len(node_id) + 1
                paren_count = 1
                j = start
                while j < len(text) and paren_count > 0:
                    if text[j] == '(':
                        paren_count += 1
                    elif text[j] == ')':
                        paren_count -= 1
                    j += 1
                
                if paren_count == 0:
                    node_text = text[start:j-1]
                    if '(' in node_text or ')' in node_text:
                        node_text = node_text.replace('"', '\\"')
                        result.append(f'{node_id}["{node_text}"]')
                    else:
                        result.append(text[i:j])
                    i = j
                else:
                    result.append(text[i])
                    i += 1
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)
    
    mermaid_code = convert_nested_parens(mermaid_code)
    
    return mermaid_code.strip()

def fix_json_file(json_file: Path, dry_run: bool = False) -> bool:
    """Fix a single JSON file."""
    try:
        with open(json_file) as f:
            data = json.load(f)
        
        original_mermaid = data.get('mermaid', '')
        cleaned_mermaid = clean_mermaid_syntax(original_mermaid)
        
        if original_mermaid != cleaned_mermaid:
            if not dry_run:
                data['mermaid'] = cleaned_mermaid
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        return False
    except Exception as e:
        print(f"❌ Error processing {json_file}: {e}")
        return False

def main():
    """Main function."""
    dry_run = '--fix' not in sys.argv
    
    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("Add --fix flag to actually apply changes")
        print("=" * 80)
        print()
    else:
        print("=" * 80)
        print("FIXING MERMAID SYNTAX IN JSON FILES")
        print("=" * 80)
        print()
    
    base_dir = Path(__file__).parent
    json_files = list(base_dir.rglob('*.json'))
    json_files = [f for f in json_files if f.parent.name != 'processes']
    
    print(f"Scanning {len(json_files)} JSON files...")
    print()
    
    fixed_count = 0
    for json_file in json_files:
        was_fixed = fix_json_file(json_file, dry_run=dry_run)
        if was_fixed:
            fixed_count += 1
            status = "Would fix" if dry_run else "Fixed"
            print(f"{status}: {json_file.relative_to(base_dir)}")
    
    print()
    print("=" * 80)
    if dry_run:
        print(f"Found {fixed_count} files that need fixing")
        print("Run with --fix flag to apply changes")
    else:
        print(f"✅ Fixed {fixed_count} files")
        print("Now run: python3 create_individual_pages.py")
    print("=" * 80)

if __name__ == '__main__':
    main()

