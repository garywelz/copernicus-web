# NSF Proposal - Formatting Instructions for PDF Generation

## Formatting Requirements

### General Formatting (All Documents)
- **Font:** 11pt or larger (Times New Roman, Arial, or Helvetica recommended)
- **Margins:** 1 inch minimum on all sides
- **Line Spacing:** Single or double spacing (consistent throughout)
- **Page Numbers:** Include on all pages (bottom center or bottom right)
- **Headers/Footers:** Optional, but if used, keep minimal

### Document-Specific Requirements

#### 1. Project Summary (1 page)
- **File:** `NSF_Project_Summary.md`
- **Page Limit:** Exactly 1 page
- **Sections:** Overview, Intellectual Merit, Broader Impacts
- **Format:** Single column, standard margins
- **Note:** May need to condense slightly to fit on one page

#### 2. Project Description (≤15 pages)
- **File:** `NSF_Project_Description.md`
- **Page Limit:** 15 pages maximum (strictly enforced)
- **Sections:** All numbered sections 1-11
- **Format:** Single column, standard margins
- **Note:** Current version should fit within 15 pages when formatted

#### 3. Biographical Sketch (2 pages max)
- **File:** `NSF_Biographical_Sketch_Welz.md`
- **Page Limit:** 2 pages maximum
- **Format:** NSF format (Professional Preparation, Appointments, Products, etc.)
- **Note:** Already formatted for NSF

#### 4. Current and Pending Support
- **File:** `NSF_Current_Pending_Support.md`
- **Page Limit:** No specific limit, but keep concise
- **Format:** Standard formatting

#### 5. Budget Justification
- **File:** Extract from `NSF_BUDGET_3Year.md`
- **Page Limit:** No specific limit, but keep reasonable
- **Format:** Standard formatting with tables if needed

#### 6. Facilities, Equipment, and Other Resources
- **File:** `NSF_Facilities_Equipment_Resources.md`
- **Page Limit:** No specific limit, but keep concise
- **Format:** Standard formatting

#### 7. Data Management and Sharing Plan (2 pages max)
- **File:** `NSF_DataManagement_Plan.md`
- **Page Limit:** 2 pages maximum
- **Format:** Standard formatting
- **Note:** Current version should fit within 2 pages

---

## PDF Generation Steps

### Option 1: Using Pandoc (Recommended)

```bash
# Install pandoc if not already installed
# Then convert each markdown file to PDF:

pandoc NSF_Project_Summary.md -o NSF_Project_Summary.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V fontfamily=times

pandoc NSF_Project_Description.md -o NSF_Project_Description.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V fontfamily=times

# Repeat for other documents...
```

### Option 2: Using Markdown to PDF Tools

1. **Markdown PDF (VS Code Extension):**
   - Install "Markdown PDF" extension
   - Open markdown file
   - Right-click → "Markdown PDF: Export (pdf)"
   - Adjust settings for 11pt font, 1" margins

2. **Online Converters:**
   - Use services like Dillinger, Markdown to PDF
   - Upload markdown file
   - Download PDF
   - Verify formatting

3. **Word/Google Docs:**
   - Copy markdown content to Word/Google Docs
   - Apply formatting (11pt font, 1" margins)
   - Export to PDF

### Option 3: Manual Formatting

1. Open markdown file in text editor
2. Copy content
3. Paste into Word/Google Docs
4. Apply formatting:
   - Font: 11pt Times New Roman (or Arial/Helvetica)
   - Margins: 1 inch all sides
   - Line spacing: Single or double
   - Page numbers: Insert → Page Number → Bottom
5. Export to PDF
6. Review PDF for formatting issues

---

## Pre-PDF Checklist

For each document:
- [ ] Content complete and reviewed
- [ ] Spelling and grammar checked
- [ ] URLs verified (if applicable)
- [ ] Page count verified (for documents with limits)
- [ ] Formatting applied (11pt font, 1" margins)
- [ ] Page numbers added
- [ ] PDF generated
- [ ] PDF reviewed for formatting issues
- [ ] File named appropriately (e.g., `NSF_Project_Summary.pdf`)

---

## File Naming Convention

Use clear, descriptive names:
- `NSF_Project_Summary.pdf`
- `NSF_Project_Description.pdf`
- `NSF_Biographical_Sketch_Welz.pdf`
- `NSF_Current_Pending_Support.pdf`
- `NSF_Budget_Justification.pdf`
- `NSF_Facilities_Equipment_Resources.pdf`
- `NSF_DataManagement_Plan.pdf`

---

## Quality Checks After PDF Generation

1. **Page Count Verification:**
   - Project Summary: Exactly 1 page
   - Project Description: ≤15 pages
   - Biographical Sketch: ≤2 pages
   - Data Management Plan: ≤2 pages

2. **Formatting Verification:**
   - Font size readable (11pt or larger)
   - Margins adequate (1" minimum)
   - Page numbers present
   - Consistent formatting throughout

3. **Content Verification:**
   - All sections present
   - No content cut off
   - Tables/figures (if any) properly formatted
   - URLs clickable (if applicable)

4. **File Verification:**
   - PDFs not corrupted
   - Files open correctly
   - File sizes reasonable

---

## Upload to FastLane/Research.gov

After generating PDFs:
1. Log into FastLane or Research.gov
2. Create new proposal
3. Select program: CISE Core Programs - IIS
4. Upload each PDF in the appropriate section
5. Review proposal in system
6. Generate preview PDF and review
7. Submit proposal

---

**Note:** These instructions assume you have access to PDF generation tools. If you need help with specific tools or encounter issues, let me know.

