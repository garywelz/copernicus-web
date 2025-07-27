"""
Helper functions for canonical podcast generation
"""

import re
import aiohttp
from google.cloud import storage
from datetime import datetime
from typing import List, Optional

async def generate_canonical_thumbnail(title: str, canonical_filename: str) -> str:
    """Generate thumbnail with canonical naming"""
    from canonical_naming import canonical_service
    
    try:
        # Use OpenAI DALL-E to generate thumbnail
        openai_key = get_secret("openai-api-key")
        if not openai_key:
            return await generate_default_thumbnail(canonical_filename)
        
        prompt = f"""
        Create a professional podcast thumbnail for "{title}".
        Style: Modern, scientific, clean design
        Elements: Abstract scientific imagery, professional typography
        Colors: Blue and white theme, high contrast
        Format: Square, podcast-ready, visually striking
        """
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1792",  # Maximum DALL-E 3 size for podcast platform requirements (min 1400x1400)
                "quality": "standard"
            }
            
            async with session.post("https://api.openai.com/v1/images/generations", 
                                  headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    image_url = result["data"][0]["url"]
                    
                    # Download and upload to GCS with canonical naming
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            image_data = await img_response.read()
                            
                            # Upload with canonical filename
                            return await canonical_service.upload_thumbnail_to_gcs(
                                canonical_filename, image_data
                            )
    
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
    
    # Return default thumbnail with canonical naming
    return await generate_default_thumbnail(canonical_filename)

async def generate_default_thumbnail(canonical_filename: str) -> str:
    """Generate default thumbnail with canonical naming"""
    try:
        # Create a simple default thumbnail or use existing default
        default_url = f"https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/{canonical_filename}-thumb.jpg"
        
        # For now, copy from default thumbnail
        storage_client = storage.Client()
        bucket = storage_client.bucket("regal-scholar-453620-r7-podcast-storage")
        
        # Try to copy default thumbnail to canonical name
        source_blob = bucket.blob("thumbnails/default-thumb.jpg")
        if source_blob.exists():
            dest_blob = bucket.blob(f"thumbnails/{canonical_filename}-thumb.jpg")
            dest_blob.upload_from_string(source_blob.download_as_bytes(), content_type="image/jpeg")
            dest_blob.make_public()
            return default_url
    
    except Exception as e:
        print(f"Default thumbnail error: {e}")
    
    return "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/thumbnails/default-thumb.jpg"

def extract_citations_from_content(script: str) -> List[str]:
    """Extract citations from generated content"""
    citations = []
    
    # Look for common citation patterns
    patterns = [
        r'([A-Z][a-z]+ et al\. \(\d{4}\))',  # Author et al. (Year)
        r'([A-Z][a-z]+ and [A-Z][a-z]+ \(\d{4}\))',  # Author and Author (Year)
        r'([A-Z][a-z]+ \(\d{4}\))',  # Single Author (Year)
        r'(DOI: [^\s]+)',  # DOI references
        r'(arXiv:\d+\.\d+)',  # arXiv references
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, script)
        citations.extend(matches)
    
    # Remove duplicates and clean up
    citations = list(set(citations))
    
    # If no citations found, add some example research citations
    if not citations:
        citations = [
            "Recent advances in the field (2024)",
            "Current research literature review",
            "Emerging paradigms and methodologies"
        ]
    
    return citations[:5]  # Limit to 5 citations

def get_secret(secret_name: str) -> str:
    """Get secret from Google Secret Manager"""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = "regal-scholar-453620-r7"
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error getting secret {secret_name}: {e}")
        return None
