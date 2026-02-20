# Mermaid Syntax Error Fix - Handoff Document

## How to Use This Document

1. **Read the Problem Summary** below to understand the issue
2. **Review the Root Cause Analysis** to see why current fixes aren't working
3. **Use the Test Script**: Run `test_mermaid_clean.py` to test your solution
   ```bash
   cd /home/gdubs/copernicus-web-public/math-processes
   python3 test_mermaid_clean.py
   ```
4. **Implement your fix** in the `clean_mermaid_syntax()` function in `create_individual_pages.py`
5. **Validate** using the commands in the "Validation Command" section

## Problem Summary

The mathematics process flowcharts are displaying "Syntax error in text" when rendered in HTML pages. The issue stems from invalid Mermaid syntax patterns in the JSON source files that are not being properly cleaned before embedding into HTML.

## Current Status

- **Total Process Pages**: 41 mathematics processes
- **Files with Syntax Errors**: 8 files still have invalid patterns
- **Error Pattern**: Unescaped quote patterns `(/"text"/)`, `[/"text"/]`, `{/"text"/}`

### Affected Files
1. `lu-decomposition.html`
2. `polynomial-long-division.html`
3. `group-operation-verification.html`
4. `curvature-calculation.html`
5. `proof-by-contradiction.html`
6. `gradient-descent-algorithm.html`
7. `monte-carlo-simulation.html`
8. `rsa-encryption-process.html`

## Root Cause Analysis

### The Problem Pattern

In the JSON source files, the Mermaid code contains patterns like:
```json
"mermaid": "... B1(/\"Input: Divisor Polynomial (D(x))\"/)B1 --> ..."
```

When Python's `json.load()` parses this:
- `\"` in JSON becomes `"` in Python
- So `(/\"text\"/)` becomes `(/"text"/)` in the Python string

### Why Current Fix Isn't Working

The `clean_mermaid_syntax()` function in `create_individual_pages.py` has regex patterns to handle this:
```python
mermaid_code = re.sub(r'\(/"([^"]+)"\)', r'(\1)', mermaid_code)
```

**Actual patterns found in the code:**
- `(/"Input: Divisor Polynomial (D(x))"/)`
- `(/"Output: Quotient Polynomial"/)`
- `(/"Output: Remainder Polynomial"/)`

The regex `r'\(/"([^"]+)"\)'` should theoretically match these, but it's not working. Possible reasons:
1. The pattern might be immediately followed by other text without space (e.g., `(/"text"/)B1` or `(/"text"/)style`)
2. The `[^"]+` pattern might be too greedy or not matching correctly when text contains parentheses
3. The regex might need to be more specific about what follows the closing `)`

**Key Insight**: The pattern `(/"text"/)` appears directly adjacent to other Mermaid syntax like `)B1 -->` or `)style`, so the regex needs to ensure it only matches the node definition, not consume following text.

## Technical Details

### File Structure
- **Source Files**: `/math-processes/[subcategory]/[process-id].json`
- **Generated HTML**: `/math-processes/processes/[process-id].html`
- **Script**: `/math-processes/create_individual_pages.py`
- **Function**: `clean_mermaid_syntax()` (lines 18-67)

### Current Cleaning Function

The function attempts to clean:
1. Unescaped quote patterns: `(/"text"/)`, `[/"text"/]`, `{/"text"/}`
2. Escaped quote patterns: `(/\"text\"/)`, `[/\"text\"/]`, `{/\"text\"/}`
3. Invalid class assignments: `]:::color`, `}:::color`, `;::color`
4. Various edge cases with spaces and backslashes

### Example Problematic Code

From `polynomial-long-division.json`:
```json
"mermaid": "... B1(/\"Input: Divisor Polynomial (D(x))\"/)B1 --> C1[\"Is D(x) = 0?\"] ..."
```

After JSON parsing, this becomes:
```
... B1(/"Input: Divisor Polynomial (D(x))"/)B1 --> C1["Is D(x) = 0?"] ...
```

The pattern `(/"Input: Divisor Polynomial (D(x))"/)` should be converted to:
```
(Input: Divisor Polynomial (D(x)))
```

## What Has Been Tried

1. ✅ Added regex patterns for `(/"text"/)` → `(text)`
2. ✅ Added regex patterns for `[/"text"/]` → `[text]`
3. ✅ Added regex patterns for `{/"text"/}` → `{text}`
4. ✅ Added handling for escaped quote variants
5. ✅ Added removal of invalid class assignments (`:::` and `::`)
6. ✅ Added handling for patterns with spaces: `[/"text" /]`
7. ❌ **Still failing** - 8 files still have errors

## Recommended Approach

### Option 1: More Robust Regex Pattern (RECOMMENDED)

The current regex `r'\(/"([^"]+)"\)'` should work, but might need word boundaries or lookahead to prevent over-matching.

**Try these patterns:**
```python
# Option 1a: Use word boundary or lookahead to ensure we only match the node
mermaid_code = re.sub(r'\(/"([^"]+)"\)(?=[A-Z0-9\s]|style|$)', r'(\1)', mermaid_code)

# Option 1b: More explicit - match the full pattern including the closing quote and paren
mermaid_code = re.sub(r'\(/"([^"]+)"\s*/\s*\)', r'(\1)', mermaid_code)

# Option 1c: Handle the case where there's no space before the closing paren
mermaid_code = re.sub(r'\(/"([^"]+)"\s*/?\s*\)', r'(\1)', mermaid_code)
```

**Test with actual problematic string:**
```python
test = 'B1(/"Input: Divisor Polynomial (D(x))"/)B1 --> C1'
# Should become: 'B1(Input: Divisor Polynomial (D(x)))B1 --> C1'
```

### Option 2: Multi-Pass Cleaning

Instead of trying to match all variations in one pass, do multiple passes:
1. First pass: Handle the most common pattern `(/"text"/)`
2. Second pass: Handle edge cases with whitespace `(/"text" /)`
3. Third pass: Handle patterns followed by other text `(/"text"/)style`

### Option 3: Parse and Reconstruct

Instead of regex, parse the Mermaid syntax more carefully:
1. Identify all node definitions
2. For each node, check if it has the invalid pattern
3. Reconstruct the node with proper syntax

### Option 4: Fix at Source (JSON Files)

Instead of cleaning during HTML generation, fix the JSON files directly:
1. Create a script to fix all JSON files
2. Update the LLM generation script to not produce these patterns
3. Re-generate affected processes

## Testing Strategy

1. **Extract problematic patterns**: Create a test script that extracts all `(/"`, `[/"`, `{/"` patterns from the 8 problematic files
2. **Test regex patterns**: Test each proposed regex against the actual problematic strings
3. **Validate output**: After fixing, validate that:
   - No `(/"` patterns remain
   - Mermaid renders without syntax errors
   - The flowchart still displays correctly

## Files to Examine

1. **Source JSON files** (to see raw patterns):
   - `/math-processes/numerical_linear_algebra/lu-decomposition.json`
   - `/math-processes/polynomial_algebra/polynomial-long-division.json`
   - `/math-processes/abstract_algebra/group-operation-verification.json`
   - `/math-processes/differential_geometry/curvature-calculation.json`
   - `/math-processes/logic_foundations/proof-by-contradiction.json`
   - `/math-processes/optimization/gradient-descent-algorithm.json`
   - `/math-processes/probability_statistics/monte-carlo-simulation.json`
   - `/math-processes/applied_mathematics/rsa-encryption-process.json`

2. **Generated HTML files** (to see what's being rendered):
   - `/math-processes/processes/[process-id].html` (check the `<div class="mermaid">` section)

3. **Script to modify**:
   - `/math-processes/create_individual_pages.py` (function `clean_mermaid_syntax()`)

## Test Cases

**⚠️ IMPORTANT: Use the standalone test script `test_mermaid_clean.py` to test your solution!**

The test script includes:
- Unit tests with actual problematic patterns
- Tests on real JSON files from the codebase
- Clear pass/fail reporting

To use it:
1. Copy your improved `clean_mermaid_syntax()` function into `test_mermaid_clean.py`
2. Replace the `clean_mermaid_syntax_current()` function
3. Run: `python3 test_mermaid_clean.py`

Here are the actual problematic strings from the JSON files that need to be fixed:

```python
# Test case 1: Basic pattern
test1 = 'B1(/"Input: Divisor Polynomial (D(x))"/)B1 --> C1'
# Expected: 'B1(Input: Divisor Polynomial (D(x)))B1 --> C1'

# Test case 2: Pattern followed by style
test2 = 'P1(/"Output: Quotient Polynomial"/)style P1 fill:#b197fc,color:#fff'
# Expected: 'P1(Output: Quotient Polynomial)style P1 fill:#b197fc,color:#fff'

# Test case 3: Pattern with nested parentheses
test3 = 'B1(/"Initialize: L = I (n x n), U = A (n x n)"/)style B1 fill:#ffd43b'
# Expected: 'B1(Initialize: L = I (n x n), U = A (n x n))style B1 fill:#ffd43b'
```

**Quick test script:**
```python
import re

def test_clean_function(clean_func):
    tests = [
        ('B1(/"Input: Divisor Polynomial (D(x))"/)B1 --> C1', 
         'B1(Input: Divisor Polynomial (D(x)))B1 --> C1'),
        ('P1(/"Output: Quotient Polynomial"/)style P1 fill:#b197fc', 
         'P1(Output: Quotient Polynomial)style P1 fill:#b197fc'),
    ]
    
    for input_str, expected in tests:
        result = clean_func(input_str)
        if result == expected:
            print(f"✅ PASS: {input_str[:50]}...")
        else:
            print(f"❌ FAIL: {input_str[:50]}...")
            print(f"   Got:      {result[:80]}")
            print(f"   Expected: {expected[:80]}")
```

## Validation Command

After making changes, run:
```bash
cd /home/gdubs/copernicus-web-public/math-processes
python3 create_individual_pages.py
python3 << 'PYEOF'
import re
from pathlib import Path

processes_dir = Path('processes')
invalid_patterns = []

for html_file in processes_dir.glob('*.html'):
    with open(html_file) as f:
        content = f.read()
    
    mermaid_match = re.search(r'<div class="mermaid">\s*(.*?)\s*</div>', content, re.DOTALL)
    if mermaid_match:
        mermaid_code = mermaid_match.group(1)
        if '{/"' in mermaid_code or '[/"' in mermaid_code or '(/"' in mermaid_code:
            invalid_patterns.append(html_file.name)

if invalid_patterns:
    print(f"❌ Found {len(invalid_patterns)} files with invalid patterns")
    for p in invalid_patterns:
        print(f"  - {p}")
else:
    print("✅ All HTML files are clean")
PYEOF
```

## Success Criteria

- ✅ Zero files with `(/"`, `[/"`, or `{/"` patterns in generated HTML
- ✅ All 41 process pages render without "Syntax error in text"
- ✅ Flowcharts display correctly in browser
- ✅ No regression in previously working files

## Additional Context

- The Mermaid library version being used: 11.12.2 (from HTML template)
- The processes were generated by an LLM (Vertex AI Gemini) which produced these invalid patterns
- The goal is to have clean, valid Mermaid syntax that renders correctly
- Once fixed, the HTML pages need to be deployed to GCS bucket: `regal-scholar-453620-r7-podcast-storage/math-processes-database/processes/`

## Next Steps

1. Examine one of the problematic JSON files to see the exact pattern
2. Test regex patterns against the actual problematic strings
3. Update `clean_mermaid_syntax()` function
4. Regenerate all HTML pages
5. Validate no errors remain
6. Deploy to GCS

---

**Created**: January 2, 2026  
**Status**: In Progress - 8 files still have syntax errors  
**Priority**: High - Blocks proper display of mathematics process flowcharts

