# Use Python 3.11 slim image for optimal performance
# Pinned to the digest revision copernicus-podcast-api-00244-lj6 (2026-07-24)
# actually pulled -- confirmed via that build's Cloud Build log ("Digest:
# sha256:db3ff2e1..."), not a fresh/different resolution of the floating tag.
# The 2026-07-24 deploy silently carried a Python patch bump alongside an
# unrelated code change; pinning stops that from happening unnoticed again.
# Bump deliberately (new digest + note here) when a base-image update is
# actually intended.
FROM python:3.11-slim@sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/podcast_generation

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port
EXPOSE $PORT

# Run the enhanced character-driven application
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
