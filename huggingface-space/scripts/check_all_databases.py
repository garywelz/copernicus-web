#!/usr/bin/env python3
"""
Check All Databases Script

Queries all data sources:
1. Google Cloud Storage (process databases)
2. Local files (processes, podcasts)
3. Firestore (if accessible)
4. PostgreSQL (video database - requires connection)
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def check_gcs_bucket():
    """Check GCS bucket structure."""
    print("=" * 70)
    print("Google Cloud Storage Bucket")
    print("=" * 70)
    print("Bucket: gs://regal-scholar-453620-r7-podcast-storage")
    print()
    
    # Note: Would need gsutil or gcloud SDK to query directly
    print("Available via gsutil:")
    print("  - biology-processes-database/")
    print("  - chemistry-processes-database/")
    print("  - physics-processes-database/")
    print("  - mathematics-processes-database/")
    print("  - computer-science-processes-database/")
    print("  - glmp/")
    print()

def check_local_processes():
    """Check local process databases."""
    print("=" * 70)
    print("Local Process Databases")
    print("=" * 70)
    
    base_path = Path(__file__).parent.parent
    disciplines = ["biology", "chemistry", "physics", "mathematics", "computer_science"]
    
    total_processes = 0
    
    for discipline in disciplines:
        db_path = base_path / f"{discipline}-processes-database"
        metadata_file = db_path / "metadata.json"
        processes_dir = db_path / "processes"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    count = metadata.get("totalProcesses", 0)
                    total_processes += count
                    print(f"{discipline.capitalize()}: {count} processes")
            except Exception as e:
                print(f"{discipline.capitalize()}: Error reading metadata - {e}")
        elif processes_dir.exists():
            # Count JSON files
            json_files = list(processes_dir.rglob("*.json"))
            count = len(json_files)
            total_processes += count
            print(f"{discipline.capitalize()}: {count} process files")
        else:
            print(f"{discipline.capitalize()}: Not found")
    
    print(f"\nTotal Processes (Local): {total_processes}")
    print()

def check_local_podcasts():
    """Check local podcast database."""
    print("=" * 70)
    print("Local Podcast Database")
    print("=" * 70)
    
    podcasts_file = Path(__file__).parent.parent.parent / "copernicus-web-public" / "public" / "podcasts.json"
    
    if podcasts_file.exists():
        try:
            with open(podcasts_file, 'r') as f:
                podcasts = json.load(f)
                count = len(podcasts) if isinstance(podcasts, list) else 0
                print(f"Total Podcasts: {count}")
                
                # Count by category
                if count > 0:
                    categories = defaultdict(int)
                    for podcast in podcasts:
                        cat = podcast.get("category", "unknown")
                        categories[cat] += 1
                    
                    print("\nBy Category:")
                    for cat, cnt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                        print(f"  {cat}: {cnt}")
        except Exception as e:
            print(f"Error reading podcasts.json: {e}")
    else:
        print("podcasts.json not found")
    
    print()

def check_papers():
    """Check paper database."""
    print("=" * 70)
    print("Paper Database")
    print("=" * 70)
    
    papers_dir = Path(__file__).parent.parent / "metadata-database" / "papers"
    
    if papers_dir.exists():
        # Count JSON files
        json_files = list(papers_dir.rglob("*.json"))
        total = len(json_files)
        
        # Count by discipline
        disciplines = defaultdict(int)
        sources = defaultdict(int)
        
        for json_file in json_files[:100]:  # Sample first 100
            try:
                with open(json_file, 'r') as f:
                    paper = json.load(f)
                    cat = paper.get("category", "unknown")
                    src = paper.get("source", "unknown")
                    disciplines[cat] += 1
                    sources[src] += 1
            except:
                pass
        
        print(f"Total Papers: {total} (from file count)")
        print("\nSample Distribution (first 100):")
        print("By Discipline:")
        for disc, cnt in sorted(disciplines.items(), key=lambda x: x[1], reverse=True):
            print(f"  {disc}: {cnt}")
        print("By Source:")
        for src, cnt in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"  {src}: {cnt}")
    else:
        print("Paper database directory not found")
    
    print()

def check_gcs_metadata():
    """Try to read GCS metadata files."""
    print("=" * 70)
    print("GCS Metadata Files")
    print("=" * 70)
    
    # Would need gsutil or gcloud SDK
    print("To check GCS metadata, run:")
    print("  gsutil cat gs://regal-scholar-453620-r7-podcast-storage/biology-processes-database/metadata.json")
    print()

def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("CopernicusAI Knowledge Engine - Database Status")
    print("=" * 70)
    print()
    
    check_local_processes()
    check_local_podcasts()
    check_papers()
    check_gcs_bucket()
    
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("\nTo get complete status:")
    print("1. Run this script for local files")
    print("2. Use gsutil for GCS bucket:")
    print("   gsutil ls -r gs://regal-scholar-453620-r7-podcast-storage/")
    print("3. Query PostgreSQL for videos (requires cloud connection)")
    print("4. Query Firestore via gcloud or admin SDK")
    print()

if __name__ == "__main__":
    main()
