#!/usr/bin/env python3
"""
Fix existing description files to meet production standards:
- Ensure under 4000 characters
- Add missing Hashtags sections
- Preserve/improve References sections
- Apply same trimming logic as deployed code
"""

import os
import sys
import re
from google.cloud import storage
from typing import List, Dict, Optional
import argparse

# Add parent directory to path to import content_fixes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_fixes import generate_relevant_hashtags

BUCKET_NAME = "regal-scholar-453620-r7-podcast-storage"
DESC_PREFIX = "descriptions/"
MAX_DESCRIPTION_LENGTH = 4000

def extract_category_from_filename(filename: str) -> str:
    """Extract category from canonical filename"""
    filename_parts = filename.replace('.md', '').split('-')
    if len(filename_parts) >= 2:
        category = filename_parts[1].upper()
        if category == 'BIO':
            return 'Biology'
        elif category == 'COMPSCI':
            return 'Computer Science'
        elif category == 'PHYS':
            return 'Physics'
        elif category == 'MATH':
            return 'Mathematics'
        elif category == 'CHEM':
            return 'Chemistry'
    return 'Science'

def extract_topic_from_description(description: str) -> str:
    """Extract topic from description content"""
    # Try to find title in first line or heading
    topic_match = re.search(r'^#\s*(.+)$', description, re.MULTILINE)
    if topic_match:
        return topic_match.group(1).strip()
    
    # Try to find in first paragraph
    first_para = description.split('\n\n')[0] if '\n\n' in description else description[:200]
    # Extract first sentence or key phrase
    return first_para[:100].strip()

def fix_description(description: str, filename: str, title: str = "", topic: str = "") -> str:
    """
    Fix a description to meet standards:
    - Ensure under 4000 chars
    - Add hashtags if missing
    - Preserve references
    - Apply trimming logic
    """
    # Extract category and topic
    category = extract_category_from_filename(filename)
    if not topic:
        topic = extract_topic_from_description(description)
    
    # Extract existing References and Hashtags
    references_text = ""
    hashtags_text = ""
    main_content = description
    
    # Extract References section
    if '## References' in description:
        ref_parts = description.split('## References', 1)
        main_content = ref_parts[0].rstrip()
        ref_remainder = ref_parts[1]
        # Get everything until next ## header or end
        if '##' in ref_remainder:
            ref_section = ref_remainder.split('##')[0]
            references_text = '## References' + ref_section.rstrip()
            # Check if there's a Hashtags section after References
            if 'Hashtags' in ref_remainder:
                hashtag_parts = ref_remainder.split('## Hashtags', 1)
                hashtags_text = '## Hashtags' + hashtag_parts[1].strip() if len(hashtag_parts) > 1 else ""
        else:
            # References section goes to end
            references_text = '## References' + ref_remainder.rstrip()
    elif '## Hashtags' in description:
        # No References but Hashtags exist
        hashtag_parts = description.split('## Hashtags', 1)
        main_content = hashtag_parts[0].rstrip()
        hashtags_text = '## Hashtags' + hashtag_parts[1].strip() if len(hashtag_parts) > 1 else ""
    
    # Generate hashtags if missing
    if not hashtags_text and not ("## Hashtags" in description or "#CopernicusAI" in description):
        hashtags = generate_relevant_hashtags(topic, category, title or "", description)
        hashtags_text = f"## Hashtags\n{hashtags}"
    
    # Rebuild description
    enhanced_description = main_content
    if references_text:
        enhanced_description += '\n\n' + references_text
    if hashtags_text:
        enhanced_description += '\n\n' + hashtags_text
    
    # Trim if too long
    if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
        # Re-extract sections after adding hashtags
        references_text = ""
        hashtags_text = ""
        main_content = enhanced_description
        
        if '## References' in enhanced_description:
            ref_parts = enhanced_description.split('## References', 1)
            main_content = ref_parts[0].rstrip()
            ref_remainder = ref_parts[1]
            if '##' in ref_remainder:
                ref_section = ref_remainder.split('##')[0]
                references_text = '## References' + ref_section.rstrip()
                if 'Hashtags' in ref_remainder:
                    hashtag_parts = ref_remainder.split('## Hashtags', 1)
                    hashtags_text = '## Hashtags' + hashtag_parts[1].strip() if len(hashtag_parts) > 1 else ""
            else:
                references_text = '## References' + ref_remainder.rstrip()
        elif '## Hashtags' in enhanced_description:
            hashtag_parts = enhanced_description.split('## Hashtags', 1)
            main_content = hashtag_parts[0].rstrip()
            hashtags_text = '## Hashtags' + hashtag_parts[1].strip() if len(hashtag_parts) > 1 else ""
        
        # Trim main content
        sections = main_content.split('\n\n')
        other_sections = [s for s in sections if s.strip()]
        
        reserved_space = len(references_text) + len(hashtags_text) + 100
        available_space = MAX_DESCRIPTION_LENGTH - reserved_space
        trimmed_other = []
        current_length = 0
        
        for section in other_sections:
            if current_length + len(section) + 2 < available_space:
                trimmed_other.append(section)
                current_length += len(section) + 2
            elif current_length < available_space:
                remaining = available_space - current_length - 20
                if remaining > 50:
                    trimmed_other.append(section[:remaining] + "...")
                break
        
        # Rebuild
        main_content_trimmed = '\n\n'.join(trimmed_other)
        if references_text:
            enhanced_description = main_content_trimmed + '\n\n' + references_text
        else:
            enhanced_description = main_content_trimmed
        
        if hashtags_text:
            enhanced_description += '\n\n' + hashtags_text
        elif not hashtags_text:
            hashtags = generate_relevant_hashtags(topic, category, title or "", description)
            enhanced_description += f"\n\n## Hashtags\n{hashtags}"
        
        # Final trim if still too long
        if len(enhanced_description) > MAX_DESCRIPTION_LENGTH:
            desc_with_refs = main_content_trimmed
            if references_text:
                desc_with_refs += '\n\n' + references_text
            
            hashtags_available_space = MAX_DESCRIPTION_LENGTH - len(desc_with_refs) - len("\n\n## Hashtags\n")
            if hashtags_available_space > 50:
                if hashtags_text:
                    hashtag_content = hashtags_text.replace('## Hashtags', '').strip()
                    if len(hashtag_content) > hashtags_available_space:
                        hashtag_lines = hashtag_content.split('\n')
                        trimmed_hashtags = []
                        current_len = 0
                        for line in hashtag_lines:
                            if current_len + len(line) + 1 <= hashtags_available_space:
                                trimmed_hashtags.append(line)
                                current_len += len(line) + 1
                            else:
                                break
                        hashtag_content = '\n'.join(trimmed_hashtags)
                    enhanced_description = desc_with_refs + f"\n\n## Hashtags\n{hashtag_content}"
                else:
                    hashtags = generate_relevant_hashtags(topic, category, title or "", description)
                    hashtag_content = hashtags[:hashtags_available_space] if len(hashtags) > hashtags_available_space else hashtags
                    enhanced_description = desc_with_refs + f"\n\n## Hashtags\n{hashtag_content}"
            else:
                enhanced_description = desc_with_refs
    
    return enhanced_description

def analyze_description(content: str, filename: str) -> Dict:
    """Analyze a description for issues"""
    issues = []
    
    length = len(content)
    if length > 4000:
        issues.append(f"Exceeds 4000 chars ({length} chars)")
    
    has_references = '## References' in content
    if not has_references:
        issues.append("Missing References section")
    
    has_hashtags = '## Hashtags' in content or '#CopernicusAI' in content
    if not has_hashtags:
        issues.append("Missing Hashtags section")
    
    return {
        "filename": filename,
        "length": length,
        "has_references": has_references,
        "has_hashtags": has_hashtags,
        "issues": issues,
        "needs_fix": len(issues) > 0
    }

def main():
    parser = argparse.ArgumentParser(description='Fix description files to meet production standards')
    parser.add_argument('--dry-run', action='store_true', help='Analyze files without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of files to fix (for testing)')
    parser.add_argument('--fix-only', choices=['length', 'hashtags', 'references', 'all'], 
                       default='all', help='Only fix specific issues')
    args = parser.parse_args()
    
    print("🔧 Fixing description files...")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    print()
    
    # Initialize GCS client
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    
    # List all description files
    blobs = list(bucket.list_blobs(prefix=DESC_PREFIX))
    description_files = [blob for blob in blobs if blob.name.endswith('.md')]
    
    print(f"Found {len(description_files)} description files")
    print()
    
    # Analyze and fix
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    files_to_process = description_files
    if args.limit:
        files_to_process = files_to_process[:args.limit]
        print(f"Processing first {args.limit} files...")
        print()
    
    for blob in files_to_process:
        try:
            filename = blob.name.replace(DESC_PREFIX, '')
            content = blob.download_as_text()
            
            # Analyze
            analysis = analyze_description(content, filename)
            
            # Check if we should fix this file
            should_fix = False
            if args.fix_only == 'all':
                should_fix = analysis['needs_fix']
            elif args.fix_only == 'length':
                should_fix = any('Exceeds 4000' in issue for issue in analysis['issues'])
            elif args.fix_only == 'hashtags':
                should_fix = any('Missing Hashtags' in issue for issue in analysis['issues'])
            elif args.fix_only == 'references':
                should_fix = any('Missing References' in issue for issue in analysis['issues'])
            
            if not should_fix:
                skipped_count += 1
                continue
            
            print(f"📝 Processing: {filename}")
            print(f"   Original: {analysis['length']} chars, Issues: {', '.join(analysis['issues'])}")
            
            # Fix the description
            fixed_content = fix_description(content, filename)
            fixed_length = len(fixed_content)
            
            # Verify fix worked
            fixed_analysis = analyze_description(fixed_content, filename)
            if fixed_analysis['needs_fix']:
                print(f"   ⚠️  Warning: Still has issues after fix: {', '.join(fixed_analysis['issues'])}")
            else:
                print(f"   ✅ Fixed: {fixed_length} chars, all issues resolved")
            
            # Upload if not dry-run
            if not args.dry_run:
                blob.upload_from_string(fixed_content, content_type="text/markdown")
                blob.make_public()
                print(f"   ✅ Uploaded to GCS")
            
            fixed_count += 1
            print()
            
        except Exception as e:
            print(f"   ❌ Error processing {blob.name}: {e}")
            error_count += 1
            print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(files_to_process)}")
    print(f"Files fixed: {fixed_count}")
    print(f"Files skipped (no issues or filtered): {skipped_count}")
    print(f"Errors: {error_count}")
    if args.dry_run:
        print()
        print("🔍 This was a DRY RUN - no files were actually modified")
        print("   Run without --dry-run to apply fixes")

if __name__ == "__main__":
    main()


