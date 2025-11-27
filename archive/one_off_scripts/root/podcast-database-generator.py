#!/usr/bin/env python3
"""
Copernicus AI Podcast Database Generator
Creates a metadata JSON file for all podcasts, similar to GLMP database
"""
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Cloud Run API endpoint
API_BASE = "https://copernicus-podcast-api-204731194849.us-central1.run.app"

def fetch_all_podcasts() -> List[Dict]:
    """Fetch all published podcasts from the API"""
    podcasts = []
    
    # Since we don't have a public API endpoint yet, we'll need to query Firestore
    # For now, we'll generate metadata for podcasts in GCS
    
    print("📊 Fetching podcasts from GCS storage...")
    
    # For now, return empty list - will be implemented after RSS endpoint
    return podcasts

def analyze_podcast(podcast_data: Dict) -> Dict:
    """Analyze a podcast and extract metadata"""
    metadata = {
        'title': podcast_data.get('title', 'Untitled'),
        'category': podcast_data.get('category', 'Unknown'),
        'expertise_level': podcast_data.get('expertise_level', 'intermediate'),
        'duration': podcast_data.get('duration', '5-10 minutes'),
        'created_at': podcast_data.get('created_at', ''),
        'submitted_to_rss': podcast_data.get('submitted_to_rss', False),
        'creator_attribution': podcast_data.get('creator_attribution'),
        'audio_url': podcast_data.get('result', {}).get('audio_url', ''),
        'description_url': podcast_data.get('result', {}).get('description_url', ''),
        'transcript_url': podcast_data.get('result', {}).get('transcript_url', ''),
    }
    
    return metadata

def generate_podcast_metadata() -> Dict:
    """Generate metadata for all podcasts"""
    podcasts = fetch_all_podcasts()
    
    metadata = {
        'generated_at': datetime.utcnow().isoformat(),
        'total_podcasts': len(podcasts),
        'categories': {},
        'expertise_levels': {},
        'podcasts': []
    }
    
    for podcast in podcasts:
        podcast_meta = analyze_podcast(podcast)
        metadata['podcasts'].append(podcast_meta)
        
        # Count by category
        category = podcast_meta['category']
        metadata['categories'][category] = metadata['categories'].get(category, 0) + 1
        
        # Count by expertise level
        level = podcast_meta['expertise_level']
        metadata['expertise_levels'][level] = metadata['expertise_levels'].get(level, 0) + 1
    
    return metadata

def main():
    """Main function to generate and save podcast database metadata"""
    print("🚀 Generating Copernicus AI Podcast Database...")
    
    metadata = generate_podcast_metadata()
    
    # Save to JSON file
    output_file = 'podcast-database-metadata.json'
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Generated metadata for {metadata['total_podcasts']} podcasts")
    print(f"📁 Saved to: {output_file}")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"   Total podcasts: {metadata['total_podcasts']}")
    print(f"   Categories: {json.dumps(metadata['categories'], indent=6)}")
    print(f"   Expertise levels: {json.dumps(metadata['expertise_levels'], indent=6)}")

if __name__ == "__main__":
    main()

