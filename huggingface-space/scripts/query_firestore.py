#!/usr/bin/env python3
"""
Query Firestore Database

Lists collections and documents in Firestore database.
"""

import sys
from google.cloud import firestore
from google.cloud.exceptions import NotFound

def query_firestore():
    """Query Firestore database."""
    print("=" * 70)
    print("Firestore Database Query")
    print("=" * 70)
    print(f"Project: regal-scholar-453620-r7")
    print()
    
    try:
        # Initialize Firestore client
        db = firestore.Client(project='regal-scholar-453620-r7')
        
        print("✅ Connected to Firestore")
        print()
        
        # Get all collections
        print("📁 Collections:")
        collections = db.collections()
        collection_list = list(collections)
        
        if not collection_list:
            print("  (No collections found)")
        else:
            for collection in collection_list:
                collection_id = collection.id
                print(f"  - {collection_id}")
                
                # Try to count documents (limit to avoid timeout)
                try:
                    docs = collection.limit(100).stream()
                    doc_count = sum(1 for _ in docs)
                    if doc_count >= 100:
                        print(f"    (at least {doc_count} documents, may be more)")
                    else:
                        print(f"    ({doc_count} documents)")
                except Exception as e:
                    print(f"    (could not count documents: {e})")
        
        print()
        
        # If collections exist, show sample documents from first collection
        if collection_list:
            first_collection = collection_list[0]
            print(f"📄 Sample Documents from '{first_collection.id}':")
            try:
                docs = first_collection.limit(5).stream()
                doc_list = list(docs)
                if doc_list:
                    for i, doc in enumerate(doc_list, 1):
                        doc_data = doc.to_dict()
                        print(f"  [{i}] Document ID: {doc.id}")
                        # Show first few fields
                        fields_shown = 0
                        for key, value in list(doc_data.items())[:3]:
                            if fields_shown < 3:
                                value_str = str(value)[:50] if len(str(value)) > 50 else str(value)
                                print(f"      {key}: {value_str}")
                                fields_shown += 1
                        if len(doc_data) > 3:
                            print(f"      ... ({len(doc_data) - 3} more fields)")
                else:
                    print("  (No documents found)")
            except Exception as e:
                print(f"  (Error reading documents: {e})")
        
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total Collections: {len(collection_list)}")
        
    except Exception as e:
        print(f"❌ Error connecting to Firestore: {e}")
        print()
        print("Troubleshooting:")
        print("1. Ensure you're authenticated: gcloud auth application-default login")
        print("2. Check project access: gcloud config get-value project")
        print("3. Ensure Firestore API is enabled")
        sys.exit(1)

if __name__ == "__main__":
    query_firestore()
