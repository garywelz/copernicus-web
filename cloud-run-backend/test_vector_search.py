#!/usr/bin/env python3
"""
Test script for vector search functionality
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.tools.vector_search import search_semantic, find_similar_content
from mcp_server.utils.firestore_client import get_firestore_client
from mcp_server.config import COLLECTION_PAPERS, COLLECTION_PODCASTS
from services.embedding_service import get_embedding_service


async def test_semantic_search():
    """Test semantic search functionality"""
    print("=" * 60)
    print("Testing Semantic Search")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "ATP synthesis in mitochondria",
        "DNA replication",
        "protein folding",
        "gene expression"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            result = await search_semantic(
                query=query,
                content_types=["papers", "podcasts"],
                limit=3,
                distance_threshold=0.8  # More lenient for testing
            )
            
            import json
            data = json.loads(result)
            
            print(f"  Papers found: {data.get('counts', {}).get('papers', 0)}")
            print(f"  Podcasts found: {data.get('counts', {}).get('podcasts', 0)}")
            
            # Show first result if available
            papers = data.get('papers', [])
            if papers:
                paper = papers[0]
                print(f"  Top paper: {paper.get('title', 'N/A')[:60]}")
                print(f"    Similarity: {paper.get('similarity_score', 0):.3f}")
            
            podcasts = data.get('podcasts', [])
            if podcasts:
                podcast = podcasts[0]
                print(f"  Top podcast: {podcast.get('title', 'N/A')[:60]}")
                print(f"    Similarity: {podcast.get('similarity_score', 0):.3f}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")


async def test_find_similar():
    """Test find similar content functionality"""
    print("\n" + "=" * 60)
    print("Testing Find Similar Content")
    print("=" * 60)
    
    db = get_firestore_client()
    
    # Find a paper with an embedding
    papers_ref = db.collection(COLLECTION_PAPERS)
    papers = papers_ref.stream()
    
    test_paper_id = None
    for paper_doc in papers:
        paper_data = paper_doc.to_dict()
        if paper_data.get('embedding'):
            test_paper_id = paper_doc.id
            print(f"\n📄 Testing with paper: {paper_data.get('title', 'N/A')[:60]}")
            break
    
    if not test_paper_id:
        print("\n⚠️  No papers with embeddings found. Skipping similarity test.")
        return
    
    try:
        result = await find_similar_content(
            content_id=test_paper_id,
            content_type="paper",
            limit=3
        )
        
        import json
        data = json.loads(result)
        
        print(f"  Similar papers: {data.get('counts', {}).get('papers', 0)}")
        print(f"  Similar podcasts: {data.get('counts', {}).get('podcasts', 0)}")
        
        similar_papers = data.get('similar_papers', [])
        if similar_papers:
            print("\n  Top similar papers:")
            for i, paper in enumerate(similar_papers[:3], 1):
                print(f"    {i}. {paper.get('title', 'N/A')[:60]}")
                print(f"       Similarity: {paper.get('similarity_score', 0):.3f}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")


async def check_embeddings():
    """Check embedding status"""
    print("=" * 60)
    print("Checking Embedding Status")
    print("=" * 60)
    
    db = get_firestore_client()
    embedding_service = get_embedding_service()
    
    # Check papers
    papers_ref = db.collection(COLLECTION_PAPERS)
    papers = list(papers_ref.limit(10).stream())
    
    papers_with_embeddings = 0
    papers_without_embeddings = 0
    
    for paper_doc in papers:
        paper_data = paper_doc.to_dict()
        if paper_data.get('embedding'):
            papers_with_embeddings += 1
        else:
            papers_without_embeddings += 1
    
    print(f"\n📄 Papers:")
    print(f"  With embeddings: {papers_with_embeddings}")
    print(f"  Without embeddings: {papers_without_embeddings}")
    
    # Check podcasts
    podcasts_ref = db.collection(COLLECTION_PODCASTS)
    podcasts = list(podcasts_ref.limit(10).stream())
    
    podcasts_with_embeddings = 0
    podcasts_without_embeddings = 0
    
    for podcast_doc in podcasts:
        podcast_data = podcast_doc.to_dict()
        if podcast_data.get('embedding'):
            podcasts_with_embeddings += 1
        else:
            podcasts_without_embeddings += 1
    
    print(f"\n🎙️  Podcasts:")
    print(f"  With embeddings: {podcasts_with_embeddings}")
    print(f"  Without embeddings: {podcasts_without_embeddings}")
    
    # Test embedding generation
    print(f"\n🔧 Embedding Service:")
    info = embedding_service.get_embedding_info()
    print(f"  Model: {info['model']}")
    print(f"  Dimension: {info['dimension']}")
    print(f"  Available: {info['available']}")
    
    # Generate a test embedding
    test_text = "Test embedding generation"
    test_embedding = embedding_service.embed_text(test_text)
    print(f"  Test embedding generated: {len(test_embedding)} dimensions ✅")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Vector Search Test Suite")
    print("=" * 60)
    
    # First check embedding status
    await check_embeddings()
    
    # Then test semantic search
    await test_semantic_search()
    
    # Finally test find similar
    await test_find_similar()
    
    print("\n" + "=" * 60)
    print("Tests Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


