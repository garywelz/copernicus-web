# Upload Instructions: TDA Preprint and Slides to Hugging Face GLMP Space

## Files Ready for Upload

1. **TDA_PREPRINT_DRAFT.pdf** (86KB) - Preprint PDF
2. **TDA_Seminar_Slides.html** (23KB) - Presentation slides

Both files are located in: `/home/gdubs/copernicus-web-public/nsf-proposal/`

## Upload Steps

### Option 1: Using Hugging Face Web Interface

1. Go to: https://huggingface.co/spaces/garywelz/glmp
2. Click on the "Files and versions" tab
3. Click "Add file" → "Upload file"
4. Upload both files:
   - `TDA_PREPRINT_DRAFT.pdf`
   - `TDA_Seminar_Slides.html`
5. Commit the changes

### Option 2: Using Git/Hugging Face CLI

If you have the GLMP repository cloned locally:

```bash
cd /path/to/glmp-repo
cp /home/gdubs/copernicus-web-public/nsf-proposal/TDA_PREPRINT_DRAFT.pdf .
cp /home/gdubs/copernicus-web-public/nsf-proposal/TDA_Seminar_Slides.html .
git add TDA_PREPRINT_DRAFT.pdf TDA_Seminar_Slides.html
git commit -m "Add TDA preprint PDF and seminar slides"
git push
```

### Option 3: Using Hugging Face Hub Python Library

```python
from huggingface_hub import HfApi

api = HfApi()
api.upload_file(
    path_or_fileobj="/home/gdubs/copernicus-web-public/nsf-proposal/TDA_PREPRINT_DRAFT.pdf",
    path_in_repo="TDA_PREPRINT_DRAFT.pdf",
    repo_id="garywelz/glmp",
    repo_type="space"
)
api.upload_file(
    path_or_fileobj="/home/gdubs/copernicus-web-public/nsf-proposal/TDA_Seminar_Slides.html",
    path_in_repo="TDA_Seminar_Slides.html",
    repo_id="garywelz/glmp",
    repo_type="space"
)
```

## README Already Updated

The GLMP README (`/home/gdubs/copernicus-web-public/huggingface-space/glmp/README.md`) has been updated with:
- A new "Publications & Presentations" section
- Links to both files using Hugging Face's `resolve/main/` URLs
- Abstract and key findings from the preprint

The links in the README point to:
- PDF: `https://huggingface.co/spaces/garywelz/glmp/resolve/main/TDA_PREPRINT_DRAFT.pdf`
- HTML Slides: `https://huggingface.co/spaces/garywelz/glmp/resolve/main/TDA_Seminar_Slides.html`

## After Upload

Once the files are uploaded, the links in the README will automatically work. You may want to:
1. Verify the links work by clicking them in the README
2. Test that the PDF downloads correctly
3. Test that the HTML slides display correctly in a browser

## Notes

- The README update is already saved locally at: `/home/gdubs/copernicus-web-public/huggingface-space/glmp/README.md`
- You'll need to commit and push the README changes along with the files
- The files should be in the root of the GLMP space repository
