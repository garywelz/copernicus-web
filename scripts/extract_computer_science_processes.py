#!/usr/bin/env python3
"""
Extract Computer Science Processes from Programming Framework

Wrapper script for extracting computer science processes from all 7 batches.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extract_programming_framework_processes import extract_all_batches
import argparse

BASE_URL = "https://garywelz-programming-framework.static.hf.space"

# Computer Science has 7 batches
COMPUTER_SCIENCE_BATCH_URLS = [
    f"{BASE_URL}/computer_science_batch_{i:02d}.html" for i in range(1, 8)
]


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Extract computer science processes from Programming Framework")
    parser.add_argument("--output", type=Path, default=Path("computer_science-processes"),
                       help="Output directory (default: computer_science-processes)")
    
    args = parser.parse_args()
    
    print("="*70)
    print("  EXTRACT COMPUTER SCIENCE PROCESSES FROM PROGRAMMING FRAMEWORK")
    print("="*70)
    print(f"\n📋 Processing 7 computer science batches...")
    print(f"   Output directory: {args.output}\n")
    
    try:
        stats = extract_all_batches("computer_science", COMPUTER_SCIENCE_BATCH_URLS, args.output)
        
        print("\n" + "="*70)
        print("  EXTRACTION COMPLETE")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Total processes: {stats['total_processes']}")
        print(f"   Subcategories: {len(stats['subcategories'])}")
        print(f"   Output directory: {args.output}")
        print(f"\n📋 Subcategories:")
        for subcat, count in sorted(stats['subcategories'].items()):
            print(f"   - {subcat}: {count} processes")
        
        print(f"\n📋 Next steps:")
        print(f"   1. Review extracted processes in {args.output}")
        print(f"   2. Upload to GCS: gsutil -m cp -r {args.output}/* gs://regal-scholar-453620-r7-podcast-storage/computer_science-processes-database/")
        print(f"   3. Sync to Firestore: python3 scripts/sync_computer_science_processes.py")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

