#!/usr/bin/env python3
"""
Quick check script to diagnose Mermaid syntax problems in JSON files.
Scans all JSON files and reports which ones have problematic patterns.
"""

import json
import re
from pathlib import Path

def check_file(json_file: Path) -> dict:
    """Check a single JSON file for problematic patterns."""
    try:
        with open(json_file) as f:
            data = json.load(f)
        
        mermaid = data.get('mermaid', '')
        problems = []
        
        # Check for problematic patterns
        if '(/"' in mermaid or '(/\\"' in mermaid:
            problems.append('(/" pattern')
        if '[/"' in mermaid or '[/\\"' in mermaid:
            problems.append('[/" pattern')
        if '{/"' in mermaid or '{/\\"' in mermaid:
            problems.append('{/" pattern')
        
        # Check for nested parentheses in parentheses nodes
        paren_nodes = re.findall(r'([A-Z0-9]+)\([^)]*\([^)]+\)[^)]*\)', mermaid)
        if paren_nodes:
            problems.append(f'nested parentheses in {len(paren_nodes)} node(s)')
        
        return {
            'file': json_file,
            'has_problems': len(problems) > 0,
            'problems': problems,
            'mermaid_length': len(mermaid)
        }
    except Exception as e:
        return {
            'file': json_file,
            'has_problems': True,
            'problems': [f'Error reading file: {e}'],
            'mermaid_length': 0
        }

def main():
    """Main function to check all JSON files."""
    base_dir = Path(__file__).parent
    
    print("=" * 80)
    print("MERMAID SYNTAX QUICK CHECK")
    print("=" * 80)
    print()
    
    # Find all JSON files
    json_files = list(base_dir.rglob('*.json'))
    json_files = [f for f in json_files if f.parent.name != 'processes']
    
    print(f"Scanning {len(json_files)} JSON files...")
    print()
    
    results = []
    for json_file in json_files:
        result = check_file(json_file)
        results.append(result)
    
    # Report results
    problematic = [r for r in results if r['has_problems']]
    clean = [r for r in results if not r['has_problems']]
    
    print(f"✅ Clean files: {len(clean)}")
    print(f"❌ Files with problems: {len(problematic)}")
    print()
    
    if problematic:
        print("PROBLEMATIC FILES:")
        print("-" * 80)
        for result in problematic:
            print(f"\n📄 {result['file'].relative_to(base_dir)}")
            for problem in result['problems']:
                print(f"   ⚠️  {problem}")
    
    print()
    print("=" * 80)
    if problematic:
        print("💡 Run fix_all_mermaid_syntax.py --fix to automatically fix these files")
    else:
        print("🎉 All files are clean!")
    print("=" * 80)

if __name__ == '__main__':
    main()

