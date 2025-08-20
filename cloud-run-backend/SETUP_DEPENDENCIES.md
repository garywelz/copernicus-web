# 🚀 Copernicus Podcast Backend - Dependency Setup Guide

## 📋 Overview

This guide will help you set up all required dependencies for the Copernicus AI podcast generation backend following the established workflow patterns.

## 🔧 Prerequisites

- Python 3.8+ installed
- Google Cloud SDK (for GCS and TTS services)
- Git access to the repository

## 🌟 Option 1: Virtual Environment Setup (Recommended)

### Step 1: Create Virtual Environment
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
python3 -m venv backend_venv
source backend_venv/bin/activate
```

### Step 2: Upgrade pip
```bash
pip install --upgrade pip
```

### Step 3: Install Core Dependencies
```bash
# Core FastAPI and web framework
pip install fastapi uvicorn[standard]

# Google Cloud services
pip install google-cloud-texttospeech google-cloud-storage google-generativeai

# HTTP and async support
pip install aiohttp requests

# Image processing for thumbnails
pip install Pillow

# Data processing
pip install pydantic pandas

# Additional utilities
pip install python-multipart
```

## 🌟 Option 2: Requirements File Installation

### Step 1: Create requirements.txt
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
cat > requirements.txt << 'EOF'
# Core web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Google Cloud services
google-cloud-texttospeech==2.16.3
google-cloud-storage==2.10.0
google-generativeai==0.3.2

# HTTP and async
aiohttp==3.9.1
requests==2.31.0

# Image processing
Pillow==10.1.0

# Data processing
pydantic==2.5.0
pandas==2.1.3

# Utilities
python-multipart==0.0.6
python-dotenv==1.0.0
EOF
```

### Step 2: Install from requirements
```bash
# Create virtual environment
python3 -m venv backend_venv
source backend_venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 🌟 Option 3: System-wide Installation (Not Recommended)

If you must install system-wide (not recommended due to package conflicts):

```bash
# Use --break-system-packages flag (risky)
pip install --break-system-packages fastapi uvicorn google-cloud-texttospeech google-cloud-storage google-generativeai aiohttp Pillow pydantic

# Or use system package manager
sudo apt update
sudo apt install python3-fastapi python3-uvicorn python3-aiohttp python3-pil python3-pydantic python3-requests
```

## 🔑 Environment Variables Setup

### Step 1: Create .env file
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
cat > .env << 'EOF'
# Google AI API Key (for Gemini content generation)
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
GEMINI_API_KEY=your_google_ai_api_key_here

# Google Cloud Project (for TTS and Storage)
GOOGLE_CLOUD_PROJECT=regal-scholar-453620-r7

# Backend configuration
PORT=8002
ENV=development
EOF
```

### Step 2: Set environment variables
```bash
# Load environment variables
source .env

# Or export manually
export GOOGLE_AI_API_KEY="your_actual_api_key"
export GOOGLE_CLOUD_PROJECT="regal-scholar-453620-r7"
export PORT=8002
```

## 🔐 Google Cloud Authentication

### Option 1: Service Account Key (Production)
```bash
# Set service account key path
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Option 2: gcloud CLI (Development)
```bash
# Install Google Cloud SDK if not installed
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login
gcloud config set project regal-scholar-453620-r7
gcloud auth application-default login
```

## 🧪 Verify Installation

### Step 1: Test Python imports
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source backend_venv/bin/activate  # if using venv

python3 -c "
import fastapi
import google.cloud.texttospeech
import google.cloud.storage
import google.generativeai
import aiohttp
from PIL import Image
import pydantic
print('✅ All core dependencies imported successfully!')
"
```

### Step 2: Test Google Cloud connectivity
```bash
python3 -c "
from google.cloud import storage
try:
    client = storage.Client()
    bucket = client.bucket('regal-scholar-453620-r7-podcast-storage')
    print('✅ Google Cloud Storage connection successful!')
except Exception as e:
    print(f'❌ GCS connection failed: {e}')
"
```

### Step 3: Test API key
```bash
python3 -c "
import os
import google.generativeai as genai

api_key = os.environ.get('GOOGLE_AI_API_KEY')
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content('Hello, test!')
        print('✅ Google AI API key working!')
    except Exception as e:
        print(f'❌ API key test failed: {e}')
else:
    print('❌ No Google AI API key found in environment')
"
```

## 🚀 Start the Backend

### Development Mode
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source backend_venv/bin/activate  # if using venv
python3 main_google.py
```

### Production Mode
```bash
cd /home/gdubs/copernicus-web-public/cloud-run-backend
source backend_venv/bin/activate  # if using venv
uvicorn main_google:app --host 0.0.0.0 --port 8002
```

## 🔍 Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'aiohttp'**
   - Solution: Activate virtual environment and reinstall dependencies

2. **Google Cloud authentication errors**
   - Solution: Run `gcloud auth application-default login`

3. **Permission denied errors**
   - Solution: Check file permissions and virtual environment activation

4. **Port already in use**
   - Solution: Kill existing processes: `pkill -f "python.*main_google.py"`

### Debug Commands
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Check installed packages
pip list | grep -E "(fastapi|google|aiohttp|pydantic)"

# Check environment variables
env | grep -E "(GOOGLE|PORT)"

# Check running processes
ps aux | grep python
```

## 📚 Next Steps

After successful installation:

1. ✅ **Dependencies installed**
2. ✅ **Environment configured**
3. ✅ **Authentication working**
4. 🔄 **Run comprehensive end-to-end test**
5. 🔄 **Validate all critical fixes**

## 🎯 Critical Fixes Implemented

This backend includes the following fixes following established workflow patterns:

- ✅ **TTS Text Preprocessing**: Removes speaker labels and symbols
- ✅ **Speaker Naming Policy**: First names only, no titles
- ✅ **AI Thumbnail Generation**: 1792x1792, no text overlays
- ✅ **Comprehensive Descriptions**: References, hashtags, structured format
- ✅ **Content Quality Standards**: Technical depth with accessibility

Ready for comprehensive testing! 🚀
