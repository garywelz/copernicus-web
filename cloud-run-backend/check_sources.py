#!/usr/bin/env python3
"""
Quick script to check what sources and categories exist in the research_papers collection.
"""

import os
from google.cloud import firestore
from collections import defaultdict

# Initialize Firestore
project_id = "regal-scholar-453620-r7"
db = firestore.Client(project=project_id, database="copernicusai")

# Query papers collection
papers_ref = db.collection('research_papers')

# Get a sample of papers (limit to first 100 for quick check)
print("Fetching papers from Firestore...")
papers = list(papers_ref.limit(100).stream())

print(f"\nTotal papers fetched: {len(papers)}")

if len(papers) == 0:
    print("⚠️  No papers found in the database!")
    exit(1)

# Check what fields exist in the papers
all_fields = set()
field_samples = defaultdict(list)

for doc in papers[:10]:  # Check first 10 papers
    paper_data = doc.to_dict()
    all_fields.update(paper_data.keys())
    
    # Collect sample values for key fields
    for field in ['source', 'sources', 'category', 'categories', 'published_date', 'year', 'title']:
        value = paper_data.get(field)
        if value is not None and len(field_samples[field]) < 3:
            field_samples[field].append(str(value)[:100])

print("\n" + "="*80)
print("ALL FIELDS FOUND IN PAPERS:")
print("="*80)
for field in sorted(all_fields):
    print(f"  - {field}")

print("\n" + "="*80)
print("SAMPLE VALUES FOR KEY FIELDS:")
print("="*80)
for field in ['source', 'sources', 'category', 'categories', 'published_date', 'year', 'title']:
    samples = field_samples[field]
    if samples:
        print(f"\n{field}:")
        for sample in samples:
            print(f"  - {sample}")
    else:
        print(f"\n{field}: ⚠️  NOT FOUND")

# Now check all papers for source/category patterns
sources = set()
categories = set()
source_counts = {}
category_counts = {}

for doc in papers:
    paper_data = doc.to_dict()
    
    # Try different field names for source
    source = (paper_data.get('source') or 
              paper_data.get('sources') or 
              (paper_data.get('sources', [{}])[0] if isinstance(paper_data.get('sources'), list) else None))
    
    if isinstance(source, list) and source:
        source = source[0]
    if source:
        source_str = str(source).lower()
        sources.add(source_str)
        source_counts[source_str] = source_counts.get(source_str, 0) + 1
    
    # Try different field names for category
    category = (paper_data.get('category') or 
                paper_data.get('categories') or
                (paper_data.get('categories', [None])[0] if isinstance(paper_data.get('categories'), list) else None))
    
    if isinstance(category, list) and category:
        category = category[0]
    if category:
        cat_str = str(category).lower()
        categories.add(cat_str)
        category_counts[cat_str] = category_counts.get(cat_str, 0) + 1

print("\n" + "="*80)
print("DISTINCT SOURCES (after checking all field variations):")
print("="*80)
if sources:
    for source in sorted(sources):
        count = source_counts.get(source, 0)
        print(f"  {source}: {count} papers")
else:
    print("  ⚠️  No source data found in any format!")

print("\n" + "="*80)
print("DISTINCT CATEGORIES (after checking all field variations):")
print("="*80)
if categories:
    for category in sorted(categories):
        count = category_counts.get(category, 0)
        print(f"  {category}: {count} papers")
else:
    print("  ⚠️  No category data found in any format!")

print("\n" + "="*80)
