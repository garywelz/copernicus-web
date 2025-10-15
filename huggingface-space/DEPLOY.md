# 📤 Deploying to Hugging Face Spaces

## Quick Deployment Instructions

### Option 1: Direct Upload via Web Interface

1. Go to your Hugging Face space: https://huggingface.co/spaces/garywelz/copernicusai
2. Click on "Files" tab
3. Upload the following files:
   - `index.html`
   - `README.md`
   - `.gitattributes`

### Option 2: Git Push (Recommended)

1. **Clone your Hugging Face space repository:**
```bash
git clone https://huggingface.co/spaces/garywelz/copernicusai
cd copernicusai
```

2. **Copy the new files:**
```bash
cp /home/gdubs/copernicus-web-public/huggingface-space/index.html .
cp /home/gdubs/copernicus-web-public/huggingface-space/README.md .
cp /home/gdubs/copernicus-web-public/huggingface-space/.gitattributes .
```

3. **Commit and push:**
```bash
git add .
git commit -m "Update Copernicus AI space with comprehensive project overview"
git push
```

### Option 3: Direct Copy from This Directory

If you're in the `/home/gdubs/copernicus-web-public` directory:

```bash
# Navigate to your Hugging Face space clone
cd /path/to/your/copernicusai-space

# Copy files
cp /home/gdubs/copernicus-web-public/huggingface-space/index.html .
cp /home/gdubs/copernicus-web-public/huggingface-space/README.md .
cp /home/gdubs/copernicus-web-public/huggingface-space/.gitattributes .

# Commit and push
git add .
git commit -m "Update Copernicus AI space with Phase 1 features"
git push
```

## What's Included

### `index.html`
A beautiful, comprehensive overview page featuring:
- Project mission and vision
- Core components (AI Podcasts, Programming Framework, GLMP)
- Database architecture
- Technology stack
- Live links to platform and APIs
- Visual statistics and discipline breakdown

### `README.md`
Detailed documentation for the Hugging Face space including:
- Project description
- All features and components
- Database schema
- API endpoints
- Links to live platform
- Technology stack details

### `.gitattributes`
Standard Hugging Face configuration for Git LFS

## Verify Deployment

After pushing, visit:
- **Main Space**: https://huggingface.co/spaces/garywelz/copernicusai
- **Files View**: https://huggingface.co/spaces/garywelz/copernicusai/tree/main

The space should display your new `index.html` as the main page with all the project information beautifully formatted.

## Troubleshooting

If the page doesn't display:
1. Make sure `index.html` is in the root directory
2. Check that the space SDK is set to "static" in the README.md frontmatter
3. Refresh the browser cache (Ctrl+F5)
4. Check the space settings to ensure it's public

## Next Steps

Consider adding:
- Interactive demos of GLMP visualizations
- Embedded audio player for sample podcasts
- Search functionality for papers/podcasts
- Live API testing interface

