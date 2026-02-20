#!/bin/bash
# Proposal Validation Script
# Checks for placeholders, incomplete sections, and common issues before declaring documents ready

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track issues
ISSUES_FOUND=0
FILES_CHECKED=0

echo "=========================================="
echo "Proposal Validation Script"
echo "=========================================="
echo ""

# Function to check a file for issues
check_file() {
    local file="$1"
    local file_issues=0
    
    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠️  File not found: $file${NC}"
        return 1
    fi
    
    echo "Checking: $file"
    FILES_CHECKED=$((FILES_CHECKED + 1))
    
    # Check for placeholder patterns
    local patterns=(
        "\[.*to be added"
        "\[.*should be added"
        "\[.*will be added"
        "\[.*need to add"
        "\[.*must add"
        "\[.*please add"
        "\[.*Additional.*should be added"
        "\[.*Citations.*should be added"
        "\[Current Date\]"
        "\[.*Date\]"
        "TODO"
        "FIXME"
        "TBD"
        "to be determined"
        "placeholder"
        "will add"
        "should add"
        "need to add"
        "must add"
        "please add"
        "you should"
        "you will"
        "you need"
    )
    
    for pattern in "${patterns[@]}"; do
        # Use case-insensitive grep
        matches=$(grep -i -n "$pattern" "$file" 2>/dev/null || true)
        if [ -n "$matches" ]; then
            echo -e "${RED}❌ Found placeholder pattern: $pattern${NC}"
            echo "$matches" | while IFS= read -r line; do
                echo -e "   ${RED}Line: $line${NC}"
            done
            file_issues=$((file_issues + 1))
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
        fi
    done
    
    # Check for empty sections (sections with only headers)
    empty_sections=$(grep -n "^##.*" "$file" | while read -r header_line; do
        line_num=$(echo "$header_line" | cut -d: -f1)
        next_header=$(awk -v start="$line_num" 'NR > start && /^##/ {print NR; exit}' "$file" || echo "EOF")
        if [ "$next_header" != "EOF" ]; then
            section_lines=$(sed -n "${line_num},$((next_header-1))p" "$file" | grep -v "^#" | grep -v "^$" | wc -l)
            if [ "$section_lines" -lt 2 ]; then
                echo "$header_line"
            fi
        fi
    done || true)
    
    if [ -n "$empty_sections" ]; then
        echo -e "${YELLOW}⚠️  Potentially empty sections found:${NC}"
        echo "$empty_sections" | while IFS= read -r line; do
            echo -e "   ${YELLOW}$line${NC}"
        done
    fi
    
    if [ $file_issues -eq 0 ]; then
        echo -e "${GREEN}✅ No issues found in $file${NC}"
    fi
    
    echo ""
    return $file_issues
}

# Main validation
echo "Starting validation..."
echo ""

# Check main proposal document
if [ -f "NSF_CISE_CORE_Proposal_Draft.md" ]; then
    check_file "NSF_CISE_CORE_Proposal_Draft.md"
fi

# Check all NSF-related markdown files
for file in NSF_*.md; do
    if [ -f "$file" ]; then
        # Skip status/checklist/guide files (these are documentation, not submission documents)
        # Only check actual proposal submission documents (case-insensitive check)
        skip_file=false
        file_upper=$(echo "$file" | tr '[:lower:]' '[:upper:]')
        for skip_pattern in STATUS CHECKLIST GUIDE INSTRUCTIONS GAP SUMMARY COMPLETE GUIDANCE VALIDATION ADDITIONS UPDATES FORMATTING FINAL; do
            if [[ "$file_upper" == *"$skip_pattern"* ]]; then
                skip_file=true
                break
            fi
        done
        
        if [ "$skip_file" = false ]; then
            check_file "$file"
        else
            echo "Skipping documentation file: $file"
        fi
    fi
done

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo "Files checked: $FILES_CHECKED"
echo "Issues found: $ISSUES_FOUND"
echo ""

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ VALIDATION PASSED - No placeholders or incomplete sections found${NC}"
    echo ""
    echo "Note: This script checks for common placeholders. Please also:"
    echo "  - Review content for completeness"
    echo "  - Verify all citations are properly formatted"
    echo "  - Check that all required sections are present"
    echo "  - Verify page limits are respected"
    exit 0
else
    echo -e "${RED}❌ VALIDATION FAILED - Found $ISSUES_FOUND issue(s)${NC}"
    echo ""
    echo "Please fix all issues before declaring documents ready for submission."
    exit 1
fi

