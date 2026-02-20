# Proposal Validation Checklist

**Purpose:** Systematic validation before declaring any document "ready for submission"

**When to use:** Before declaring any proposal, grant application, or critical document ready

---

## Automated Checks (Run validation script)

- [ ] Run `./validate_proposal.sh` (or `bash validate_proposal.sh`)
- [ ] Script reports 0 issues found
- [ ] All files pass placeholder checks

---

## Manual Content Review

### 1. Placeholder and Incomplete Section Check

- [ ] No `[Additional... should be added here]` placeholders
- [ ] No `[Current Date]` or `[Date]` placeholders
- [ ] No `TODO`, `FIXME`, or `TBD` markers
- [ ] No "will be added", "should be added", "need to add" notes
- [ ] No "you should", "you will", "you need" instructions to user
- [ ] All sections have actual content (not just headers)

### 2. Citation and Reference Check

- [ ] All citations are complete (author, year, title, venue)
- [ ] No placeholder citations like `[Citations on...]`
- [ ] All URLs/links are valid and accessible
- [ ] Prior work properly cited with working links
- [ ] References section is complete (if required)

### 3. Document Completeness

- [ ] All required sections present
- [ ] No empty sections (header with no content)
- [ ] All "See:" references point to existing documents
- [ ] All cross-references are valid
- [ ] Page limits respected (if applicable)

### 4. Formatting and Technical Issues

- [ ] No Unicode characters that break LaTeX (≥, ≤, etc.) - use >=, <=
- [ ] Font size and margins correct (if specified)
- [ ] Page numbers present (if required)
- [ ] Tables/figures properly formatted
- [ ] PDFs generate without errors

### 5. Administrative Information

- [ ] PI name and contact information complete
- [ ] Organization information correct
- [ ] No placeholder passwords or sensitive info
- [ ] Budget totals correct
- [ ] All dates are actual dates (not placeholders)

### 6. Content Quality

- [ ] No grammatical errors
- [ ] Consistent terminology throughout
- [ ] All technical terms defined (if needed)
- [ ] Claims are supported by evidence
- [ ] Objectives are clear and measurable

---

## Multi-Document Validation

For proposals with multiple files:

- [ ] Main proposal document validated
- [ ] All supporting documents validated
- [ ] Budget document complete
- [ ] Biographical sketch complete
- [ ] Data management plan complete
- [ ] Facilities/equipment section complete
- [ ] Current/pending support complete
- [ ] All cross-references between documents work

---

## Pre-Submission Final Check

- [ ] All automated checks pass
- [ ] All manual checks pass
- [ ] Content reviewed by human (you)
- [ ] Ready for PDF generation
- [ ] PDFs generated successfully
- [ ] PDFs reviewed for formatting issues

---

## Declaration of Readiness

**DO NOT declare ready until:**

1. ✅ Validation script reports 0 issues
2. ✅ All manual checks completed
3. ✅ All documents reviewed
4. ✅ PDFs generated and reviewed
5. ✅ Final human review completed

**When declaring ready, state:**

- "I have completed [specific tasks] and run validation checks. Please review [specific sections] before final submission."

**NOT:**

- "The proposal is ready for submission" (unless all checks are explicitly confirmed)

---

## Notes

- This checklist should be used for every critical document
- When in doubt, flag for review rather than declaring ready
- Always verify with user before declaring submission-ready
- Keep a record of validation runs (date, issues found, fixes applied)

---

**Last Updated:** 2024-12-22  
**Version:** 1.0



