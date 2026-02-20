#!/usr/bin/env python3
"""
Analyze existing description files to identify issues:
- Files exceeding 4000 character limit
- Missing References section
- Missing Hashtags section
- Estimate time to fix
"""

import os
from google.cloud import storage
from typing import List, Dict
import re

BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
DESC_PREFIX = "descriptions/"

def analyze_description(content: str, filename: str) -> Dict:
    """Analyze a single description file for issues"""
    issues = []
    
    # Check length
    length = len(content)
    if length > 4000:
        issues.append(f"Exceeds 4000 chars ({length} chars)")
    
    # Check for References section
    has_references = '## References' in content or 'References' in content
    if not has_references:
        issues.append("Missing References section")
    
    # Check for Hashtags section
    has_hashtags = '## Hashtags' in content or '#CopernicusAI' in content
    if not has_hashtags:
        issues.append("Missing Hashtags section")
    
    # Check if References section is complete (has actual citations)
    if has_references:
        ref_section = ""
        if '## References' in content:
            ref_parts = content.split('## References', 1)
            if len(ref_parts) > 1:
                ref_section = ref_parts[1].split('##')[0]  # Get until next section
        # Check if it has actual citations (lines starting with - or numbers)
        has_citations = bool(re.search(r'^[-*]\s+|^\d+\.\s+', ref_section, re.MULTILINE))
        if not has_citations:
            issues.append("References section exists but appears empty/incomplete")
    
    return {
        "filename": filename,
        "length": length,
        "has_references": has_references,
        "has_hashtags": has_hashtags,
        "issues": issues,
        "needs_fix": len(issues) > 0
    }

def main():
    print("🔍 Analyzing description files in GCS...")
    print()
    
    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    
    # List all description files
    blobs = list(bucket.list_blobs(prefix=DESC_PREFIX))
    description_files = [blob for blob in blobs if blob.name.endswith('.md')]
    
    print(f"Found {len(description_files)} description files")
    print()
    
    # Analyze each file
    results = []
    for blob in description_files:
        try:
            content = blob.download_as_text()
            filename = blob.name.replace(DESC_PREFIX, '')
            analysis = analyze_description(content, filename)
            results.append(analysis)
        except Exception as e:
            print(f"❌ Error analyzing {blob.name}: {e}")
            results.append({
                "filename": blob.name.replace(DESC_PREFIX, ''),
                "error": str(e),
                "needs_fix": True
            })
    
    # Summary statistics
    total = len(results)
    needs_fix = sum(1 for r in results if r.get('needs_fix', False))
    too_long = sum(1 for r in results if any('Exceeds 4000' in issue for issue in r.get('issues', [])))
    missing_refs = sum(1 for r in results if any('Missing References' in issue for issue in r.get('issues', [])))
    missing_hashtags = sum(1 for r in results if any('Missing Hashtags' in issue for issue in r.get('issues', [])))
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total description files: {total}")
    print(f"Files needing fixes: {needs_fix} ({needs_fix/total*100:.1f}%)")
    print(f"  - Exceeding 4000 chars: {too_long}")
    print(f"  - Missing References: {missing_refs}")
    print(f"  - Missing Hashtags: {missing_hashtags}")
    print()
    
    # Time estimate
    # Assuming:
    # - 2-3 minutes per file to review and regenerate description
    # - Can batch process similar issues
    # - Some files may need manual review
    
    if needs_fix > 0:
        estimated_minutes = needs_fix * 2.5  # 2.5 minutes per file average
        estimated_hours = estimated_minutes / 60
        
        print("⏱️  TIME ESTIMATE")
        print("=" * 60)
        print(f"Estimated time to fix all: {estimated_hours:.1f} hours ({estimated_minutes:.0f} minutes)")
        print(f"  - Assumes 2-3 minutes per file (download, analyze, regenerate, upload)")
        print(f"  - Could be faster with batch processing")
        print(f"  - Some files may need manual review if content is complex")
        print()
    
    # Show files with issues
    if needs_fix > 0:
        print("=" * 60)
        print("FILES NEEDING FIXES (showing first 20)")
        print("=" * 60)
        for i, result in enumerate([r for r in results if r.get('needs_fix', False)][:20]):
            print(f"\n{i+1}. {result['filename']}")
            if 'error' in result:
                print(f"   ❌ Error: {result['error']}")
            else:
                print(f"   Length: {result['length']} chars")
                print(f"   Issues: {', '.join(result['issues'])}")
        
        if needs_fix > 20:
            print(f"\n... and {needs_fix - 20} more files")
    
    print()
    print("=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    if needs_fix == 0:
        print("✅ All description files meet requirements!")
    elif needs_fix < 10:
        print(f"✅ Worth fixing - only {needs_fix} files need updates")
        print("   Estimated time: ~30 minutes")
    elif needs_fix < 50:
        print(f"⚠️  Moderate effort - {needs_fix} files need updates")
        print(f"   Estimated time: {estimated_hours:.1f} hours")
        print("   Consider fixing in batches or prioritizing recent/popular episodes")
    else:
        print(f"⚠️  Significant effort - {needs_fix} files need updates")
        print(f"   Estimated time: {estimated_hours:.1f} hours")
        print("   Recommendation:")
        print("   - Fix new episodes going forward (already done)")
        print("   - Optionally fix only recent/popular episodes")
        print("   - Or fix in batches over time")
    print()

if __name__ == "__main__":
    main()


