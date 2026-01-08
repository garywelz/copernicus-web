# Quick Deployment to Hugging Face Space

## ✅ README.md Updated and Committed

The updated README.md has been committed to your local repository. 

## 🚀 Deploy to Hugging Face Space

**Option 1: Git Push (if you have the HF space cloned)**

```bash
# If you have the HF space repo cloned locally:
cd /path/to/copernicusai-space
cp /home/gdubs/copernicus-web-public/huggingface-space/README.md .
git add README.md
git commit -m "Update README: grant-application-ready with video features, multi-API research, Phase 2 metadata database"
git push
```

**Option 2: Web Interface Upload (Fastest)**

1. Go to: https://huggingface.co/spaces/garywelz/copernicusai
2. Click "Files" tab
3. Click "Add file" → "Upload files"
4. Upload: `/home/gdubs/copernicus-web-public/huggingface-space/README.md`
5. Commit with message: "Update README: grant-application-ready content"

**Option 3: Clone and Push (First Time)**

```bash
# Clone the HF space repo
cd /tmp
git clone https://huggingface.co/spaces/garywelz/copernicusai
cd copernicusai

# Copy the updated README
cp /home/gdubs/copernicus-web-public/huggingface-space/README.md .

# Commit and push
git add README.md
git commit -m "Update README: grant-application-ready with video features, multi-API research, Phase 2 metadata database"
git push
```

The README will automatically update on the Hugging Face Space page!


