# Quick Start Guide for LLMs

## What You Need to Know

You're being asked to fix a Mermaid syntax cleaning function. The current implementation fails to clean certain patterns.

## Files to Review

1. **`MERMAID_SYNTAX_FIX_HANDOFF.md`** - Full problem description and context
2. **`test_mermaid_clean.py`** - Standalone test script (run this to test your solution)
3. **`create_individual_pages.py`** - The file you need to modify (function `clean_mermaid_syntax()`)

## Quick Test

Run this to see the current failures:
```bash
cd /home/gdubs/copernicus-web-public/math-processes
python3 test_mermaid_clean.py
```

**Current Status**: 2/6 tests pass. The parentheses patterns `(/"text"/)` are not being cleaned.

## Your Task

Fix the `clean_mermaid_syntax()` function in `create_individual_pages.py` so that:
- All 6 unit tests pass
- All actual JSON files are cleaned correctly
- The function handles patterns like `(/"text"/)`, `[/"text"/]`, and `{/"text"/}`

## Success Criteria

After your fix:
1. Run `python3 test_mermaid_clean.py` - all tests should pass ✅
2. Run `python3 create_individual_pages.py` - regenerate HTML pages
3. Check that no HTML files contain `(/"`, `[/"`, or `{/"` patterns

## Key Insight

The regex `r'\(/"([^"]+)"\)'` should match `(/"text"/)` but it's not working. The pattern appears directly adjacent to other text (e.g., `(/"text"/)B1` or `(/"text"/)style`), so the regex might need adjustment.

Good luck! 🚀

