#!/usr/bin/env python3
"""
Standalone test script for Mermaid syntax cleaning function.

This script can be used to test any proposed fix for the clean_mermaid_syntax function.
Simply replace the clean_mermaid_syntax function with your implementation and run this script.
"""

import re
from pathlib import Path
import json

def clean_mermaid_syntax_current(mermaid_code: str) -> str:
    """
    CURRENT IMPLEMENTATION (has bugs - this is what needs to be fixed)
    
    Replace this function with your improved version to test.
    """
    if not mermaid_code:
        return ""
    
    # First, fix unescaped quote patterns (after JSON parsing): /"text"/
    # Handle parentheses nodes: (/"text"/) -> (text) - FIXED: added / before )
    mermaid_code = re.sub(r'\(/"([^"]+)"/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/"text" /] or [/"text"/] -> [text] - FIXED: removed ? and added / before ]
    mermaid_code = re.sub(r'\[/"([^"]+)"\s*/\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/"text"/} -> {text} - FIXED: added / before }
    mermaid_code = re.sub(r'\{/"([^"]+)"/\}', r'{\1}', mermaid_code)
    
    # Also handle escaped quote patterns (in case they appear): /\"text\"/
    # Handle parentheses nodes: (/\"text\"/) -> (text) - FIXED: added / before )
    mermaid_code = re.sub(r'\(/\\"([^"]+)\\"/\)', r'(\1)', mermaid_code)
    
    # Handle bracket nodes: [/\"text\" /] or [/\"text\"/] -> [text] - FIXED: removed ? and added / before ]
    mermaid_code = re.sub(r'\[/\\"([^"]+)\\"\s*/\]', r'[\1]', mermaid_code)
    
    # Handle curly brace nodes: {/\"text\"/} -> {text} - FIXED: added / before }
    mermaid_code = re.sub(r'\{/\\"([^"]+)\\"/\}', r'{\1}', mermaid_code)
    
    # Remove invalid class assignments like ]:::red, ]::yellow, }::yellow, etc.
    # Also remove ;::color patterns that come after nodes
    mermaid_code = re.sub(r'\]:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}:::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\):::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    mermaid_code = re.sub(r'\]::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r']', mermaid_code)
    mermaid_code = re.sub(r'\}::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'}', mermaid_code)
    mermaid_code = re.sub(r'\)::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r')', mermaid_code)
    # Remove ;::color patterns that come after closing brackets/braces
    mermaid_code = re.sub(r'([\]\}\)]);::(red|yellow|green|blue|purple|orange|pink|gray|grey)', r'\1', mermaid_code)
    
    # Fix [/"text"/] patterns to [text] (handles all variations with spaces)
    mermaid_code = re.sub(r'\[/"([^"]+)"[^\]]*\]', r'[\1]', mermaid_code)
    
    # Fix {/"text"/} patterns to {text} (handles all variations with spaces)
    mermaid_code = re.sub(r'\{/"([^"]+)"[^\}]*\}', r'{\1}', mermaid_code)
    
    # Fix /"text"\\] patterns (escaped backslashes)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+]', r'[\1]', mermaid_code)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+\s*/\}\)', r'[\1])', mermaid_code)
    mermaid_code = re.sub(r'/\\"([^"]+)\\"[\\]+\s*/\}', r'[\1]}', mermaid_code)
    
    return mermaid_code.strip()


# ============================================================================
# TEST CASES - These are actual problematic patterns from the JSON files
# ============================================================================

TEST_CASES = [
    # (test_input, expected_output, description)
    (
        'B1(/"Input: Divisor Polynomial (D(x))"/)B1 --> C1',
        'B1(Input: Divisor Polynomial (D(x)))B1 --> C1',
        'Basic parentheses node pattern'
    ),
    (
        'P1(/"Output: Quotient Polynomial"/)style P1 fill:#b197fc,color:#fff',
        'P1(Output: Quotient Polynomial)style P1 fill:#b197fc,color:#fff',
        'Pattern followed by style directive'
    ),
    (
        'B1(/"Initialize: L = I (n x n), U = A (n x n)"/)style B1 fill:#ffd43b',
        'B1(Initialize: L = I (n x n), U = A (n x n))style B1 fill:#ffd43b',
        'Pattern with nested parentheses in text'
    ),
    (
        'A1[Input: Square Matrix A (n x n)] --> B1(/"Initialize: L = I (n x n), U = A (n x n)"/)B1 --> C1',
        'A1[Input: Square Matrix A (n x n)] --> B1(Initialize: L = I (n x n), U = A (n x n))B1 --> C1',
        'Pattern in middle of Mermaid graph'
    ),
    (
        'D1{/"i < n - 1?"/};::yellow style D1 fill:#ffd43b',
        'D1{i < n - 1?} style D1 fill:#ffd43b',
        'Curly brace pattern with class assignment'
    ),
    (
        'G1[/"factor = U[j][i] / U[i][i]" /];::green style G1 fill:#51cf66',
        'G1[factor = U[j][i] / U[i][i]] style G1 fill:#51cf66',
        'Bracket pattern with space and class assignment'
    ),
]


def run_tests(clean_func):
    """Run all test cases against the provided cleaning function."""
    print("=" * 80)
    print("Testing Mermaid Syntax Cleaning Function")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, (test_input, expected, description) in enumerate(TEST_CASES, 1):
        result = clean_func(test_input)
        if result == expected:
            print(f"✅ Test {i}: PASS - {description}")
            passed += 1
        else:
            print(f"❌ Test {i}: FAIL - {description}")
            print(f"   Input:    {test_input[:70]}")
            print(f"   Got:      {result[:70]}")
            print(f"   Expected: {expected[:70]}")
            print()
            failed += 1
    
    print()
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 80)
    
    return failed == 0


def test_on_actual_files(clean_func):
    """Test the function on actual problematic JSON files."""
    print("\n" + "=" * 80)
    print("Testing on Actual JSON Files")
    print("=" * 80)
    print()
    
    base_dir = Path(__file__).parent
    problematic_files = [
        'polynomial_algebra/polynomial-long-division.json',
        'numerical_linear_algebra/lu-decomposition.json',
    ]
    
    all_clean = True
    
    for file_path in problematic_files:
        json_file = base_dir / file_path
        if not json_file.exists():
            print(f"⚠️  File not found: {json_file}")
            continue
        
        with open(json_file) as f:
            data = json.load(f)
        
        mermaid = data['mermaid']
        cleaned = clean_func(mermaid)
        
        # Check if any problematic patterns remain
        has_errors = False
        file_name = Path(file_path).name
        if '(/"' in cleaned:
            print(f"❌ {file_name}: Still contains (/\") pattern")
            has_errors = True
        if '[/"' in cleaned:
            print(f"❌ {file_name}: Still contains [/\") pattern")
            has_errors = True
        if '{/"' in cleaned:
            print(f"❌ {file_name}: Still contains {{/\") pattern")
            has_errors = True
        
        if not has_errors:
            print(f"✅ {file_name}: All problematic patterns removed")
        else:
            all_clean = False
    
    return all_clean


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("MERMAID SYNTAX CLEANING TEST SUITE")
    print("=" * 80)
    print("\nThis script tests the clean_mermaid_syntax function.")
    print("Replace clean_mermaid_syntax_current() with your implementation to test.\n")
    
    # Run unit tests
    unit_tests_passed = run_tests(clean_mermaid_syntax_current)
    
    # Test on actual files
    files_clean = test_on_actual_files(clean_mermaid_syntax_current)
    
    print("\n" + "=" * 80)
    if unit_tests_passed and files_clean:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Please fix the clean_mermaid_syntax function.")
    print("=" * 80)

