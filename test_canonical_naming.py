#!/usr/bin/env python3
"""
Test script for canonical naming system
"""

import asyncio
import sys
import os

# Add the cloud-run-backend directory to the path
sys.path.append('/home/gdubs/copernicus-web-public/cloud-run-backend')

from canonical_naming import canonical_service

async def test_canonical_naming():
    """Test the canonical naming system"""
    print("🧪 Testing Canonical Naming System")
    print("=" * 50)
    
    # Test categories
    test_categories = ["biology", "chemistry", "computer-science", "mathematics", "physics"]
    
    for category in test_categories:
        print(f"\n📂 Testing category: {category}")
        
        try:
            # Test filename generation
            canonical_filename, episode_number = await canonical_service.generate_canonical_filename(
                category, f"Test {category.title()} Episode"
            )
            
            print(f"✅ Generated filename: {canonical_filename}")
            print(f"✅ Episode number: {episode_number}")
            
            # Test asset URL generation
            asset_urls = canonical_service.get_asset_urls(canonical_filename)
            print(f"🎵 Audio URL: {asset_urls['audio_url']}")
            print(f"🖼️ Thumbnail URL: {asset_urls['thumbnail_url']}")
            print(f"📝 Description URL: {asset_urls['description_url']}")
            
            # Test description formatting
            test_description = f"This is a test episode about {category}. It covers important concepts and recent research."
            test_citations = [
                "Smith et al. (2024). Recent Advances in Research.",
                "Jones & Brown (2023). Methodology and Applications."
            ]
            
            formatted_desc = canonical_service.format_description_with_citations(
                test_description, test_citations, f"Test {category} Topic", category
            )
            
            print(f"📄 Formatted description preview:")
            print(formatted_desc[:200] + "..." if len(formatted_desc) > 200 else formatted_desc)
            
        except Exception as e:
            print(f"❌ Error testing {category}: {e}")
    
    print("\n🎉 Canonical naming system test completed!")

if __name__ == "__main__":
    asyncio.run(test_canonical_naming())
