#!/bin/bash
# Cleanup script for papers folder
# Removes files no longer needed after successful submissions

cd /home/gdubs/copernicus-web-public/papers

echo "=== Papers Folder Cleanup ==="
echo "This script will delete files that are no longer needed."
echo ""
echo "Files to be deleted:"
echo ""

# Unused submission checklists and guides
echo "1. Unused submission checklists and guides:"
echo "   - PLOS_ONE_SUBMISSION_CHECKLIST.md"
echo "   - SCIENTIFIC_REPORTS_SUBMISSION_CHECKLIST.md"
echo "   - SCIENTIFIC_REPORTS_ACCESS_GUIDE.md"
echo "   - Cover_Letter_PLOS_ONE.md"
echo "   - Cover_Letter_Scientific_Reports.md"

# Temporary submission guides
echo ""
echo "2. Temporary submission guides:"
echo "   - QUICK_START_SUBMISSION.md"
echo "   - TASK_BY_TASK_GUIDE.md"
echo "   - TASK2_QUICK_REFERENCE.md"
echo "   - SUBMISSION_ACTION_PLAN.md"
echo "   - SUBMISSION_INSTRUCTIONS.md"
echo "   - SUBMISSION_PREPARATION.md"

# Planning and evaluation docs (completed)
echo ""
echo "3. Completed planning/evaluation docs:"
echo "   - PROGRAMMING_FRAMEWORK_SUBMISSION_PLAN.md"
echo "   - NATURE_METHODS_FORMATTING_CHECK.md"
echo "   - NATURE_METHODS_EVALUATION.md"
echo "   - PROGRAMMING_FRAMEWORK_JOURNAL_RECOMMENDATIONS.md"
echo "   - JOURNAL_SUBMISSION_RECOMMENDATIONS.md"
echo "   - PREPRINT_READINESS_ASSESSMENT.md"
echo "   - ARXIV_SUBMISSION_METADATA.md"
echo "   - SCREENSHOT_INSTRUCTIONS.md"

# Completed submission checklists (optional - can keep for reference)
echo ""
echo "4. Completed submission checklists (optional to delete):"
echo "   - NATURE_MACHINE_INTELLIGENCE_SUBMISSION_CHECKLIST.md"
echo "   - NATURE_METHODS_SUBMISSION_CHECKLIST.md"

# Old draft paper (if it's a duplicate)
echo ""
echo "5. Old draft paper (if duplicate):"
echo "   - Paper4_Knowledge_Engine_Concept_Draft.md"
echo "   - Paper4_Knowledge_Engine_Concept_Draft.pdf"

# Tracking CSV (optional)
echo ""
echo "6. Optional tracking file:"
echo "   - SUBMISSION_TRACKING.csv"

echo ""
echo "Press Ctrl+C to cancel, or press Enter to continue..."
read

# Delete files
echo ""
echo "Deleting files..."

# Unused checklists
rm -f PLOS_ONE_SUBMISSION_CHECKLIST.md
rm -f SCIENTIFIC_REPORTS_SUBMISSION_CHECKLIST.md
rm -f SCIENTIFIC_REPORTS_ACCESS_GUIDE.md
rm -f Cover_Letter_PLOS_ONE.md
rm -f Cover_Letter_Scientific_Reports.md

# Temporary guides
rm -f QUICK_START_SUBMISSION.md
rm -f TASK_BY_TASK_GUIDE.md
rm -f TASK2_QUICK_REFERENCE.md
rm -f SUBMISSION_ACTION_PLAN.md
rm -f SUBMISSION_INSTRUCTIONS.md
rm -f SUBMISSION_PREPARATION.md

# Planning docs
rm -f PROGRAMMING_FRAMEWORK_SUBMISSION_PLAN.md
rm -f NATURE_METHODS_FORMATTING_CHECK.md
rm -f NATURE_METHODS_EVALUATION.md
rm -f PROGRAMMING_FRAMEWORK_JOURNAL_RECOMMENDATIONS.md
rm -f JOURNAL_SUBMISSION_RECOMMENDATIONS.md
rm -f PREPRINT_READINESS_ASSESSMENT.md
rm -f ARXIV_SUBMISSION_METADATA.md
rm -f SCREENSHOT_INSTRUCTIONS.md

# Optional: Completed checklists (uncomment if you want to delete)
# rm -f NATURE_MACHINE_INTELLIGENCE_SUBMISSION_CHECKLIST.md
# rm -f NATURE_METHODS_SUBMISSION_CHECKLIST.md

# Optional: Old draft (uncomment if Paper4 is confirmed duplicate)
# rm -f Paper4_Knowledge_Engine_Concept_Draft.md
# rm -f Paper4_Knowledge_Engine_Concept_Draft.pdf

# Optional: Tracking CSV
# rm -f SUBMISSION_TRACKING.csv

echo "Cleanup complete!"
echo ""
echo "Files remaining:"
ls -1 *.md *.pdf *.docx 2>/dev/null | head -20
