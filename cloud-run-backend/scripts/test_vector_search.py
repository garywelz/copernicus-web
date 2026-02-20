#!/usr/bin/env python3
"""
Test Vector Search and RAG Capabilities

Tests semantic search, similarity search, and RAG across all content types.
"""

import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.vector_search import search_semantic, find_similar_content
from services.rag_service import get_rag_service
from utils.logging import structured_logger


async def test_semantic_search():
    """Test semantic search across all content types."""
    print("\n" + "="*70)
    print("TEST 1: Semantic Search")
    print("="*70)
    
    test_queries = [
        "DNA replication",
        "metabolic pathways",
        "quantum mechanics",
        "protein synthesis",
        "cell division"
    ]
    
    results = []
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        try:
            result_str = await search_semantic(query=query, limit=5)
            result = json.loads(result_str)
            
            papers_count = len(result.get("papers", []))
            glmp_count = len(result.get("glmp_processes", []))
            podcasts_count = len(result.get("podcasts", []))
            total = papers_count + glmp_count + podcasts_count
            
            print(f"   ✅ Found: {papers_count} papers, {glmp_count} GLMP, {podcasts_count} podcasts (total: {total})")
            
            # Show top result from each type
            if result.get("papers"):
                top_paper = result["papers"][0]
                print(f"   📄 Top paper: {top_paper.get('title', 'N/A')[:60]}... (score: {top_paper.get('similarity_score', 0):.3f})")
            
            if result.get("glmp_processes"):
                top_glmp = result["glmp_processes"][0]
                print(f"   🔬 Top GLMP: {top_glmp.get('title', top_glmp.get('name', 'N/A'))[:60]}... (score: {top_glmp.get('similarity_score', 0):.3f})")
            
            if result.get("podcasts"):
                top_podcast = result["podcasts"][0]
                title = top_podcast.get('result', {}).get('title') or top_podcast.get('title', 'N/A')
                print(f"   🎙️  Top podcast: {title[:60]}... (score: {top_podcast.get('similarity_score', 0):.3f})")
            
            results.append({
                "query": query,
                "success": True,
                "papers": papers_count,
                "glmp": glmp_count,
                "podcasts": podcasts_count,
                "total": total
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "query": query,
                "success": False,
                "error": str(e)
            })
    
    return results


async def test_content_type_search():
    """Test search with specific content types."""
    print("\n" + "="*70)
    print("TEST 2: Content Type Filtering")
    print("="*70)
    
    test_cases = [
        ("DNA replication", ["glmp"]),
        ("quantum mechanics", ["papers"]),
        ("biology", ["glmp", "papers"]),
    ]
    
    results = []
    for query, content_types in test_cases:
        print(f"\n🔍 Testing: '{query}' in {content_types}")
        try:
            result_str = await search_semantic(query=query, content_types=content_types, limit=5)
            result = json.loads(result_str)
            
            total = sum(len(result.get(ct, [])) for ct in ["papers", "glmp_processes", "podcasts"])
            print(f"   ✅ Found {total} results")
            
            results.append({"query": query, "content_types": content_types, "success": True, "count": total})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({"query": query, "success": False, "error": str(e)})
    
    return results


async def test_similarity_search():
    """Test finding similar content."""
    print("\n" + "="*70)
    print("TEST 3: Similarity Search")
    print("="*70)
    
    # Get a sample GLMP process ID
    from google.cloud import firestore
    import os
    db = firestore.Client(project=os.getenv("GCP_PROJECT_ID", "regal-scholar-453620-r7"), database="copernicusai")
    
    glmp_docs = list(db.collection("glmp_processes").limit(1).stream())
    if not glmp_docs:
        print("   ⚠️  No GLMP processes found for testing")
        return []
    
    test_process_id = glmp_docs[0].id
    process_data = glmp_docs[0].to_dict()
    process_name = process_data.get("title") or process_data.get("name", test_process_id)
    
    print(f"\n🔍 Testing similarity for: '{process_name}' (ID: {test_process_id})")
    
    try:
        result_str = await find_similar_content(content_id=test_process_id, content_type="glmp", limit=5)
        result = json.loads(result_str)
        
        similar_glmp = len(result.get("similar_glmp_processes", []))
        similar_papers = len(result.get("similar_papers", []))
        similar_podcasts = len(result.get("similar_podcasts", []))
        
        print(f"   ✅ Found: {similar_glmp} similar GLMP, {similar_papers} similar papers, {similar_podcasts} similar podcasts")
        
        if result.get("similar_glmp_processes"):
            top_similar = result["similar_glmp_processes"][0]
            print(f"   🔬 Most similar: {top_similar.get('title', top_similar.get('name', 'N/A'))[:60]}... (score: {top_similar.get('similarity_score', 0):.3f})")
        
        return [{"success": True, "similar_glmp": similar_glmp, "similar_papers": similar_papers, "similar_podcasts": similar_podcasts}]
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return [{"success": False, "error": str(e)}]


async def test_rag():
    """Test RAG question answering."""
    print("\n" + "="*70)
    print("TEST 4: RAG Question Answering")
    print("="*70)
    
    test_questions = [
        "What is DNA replication?",
        "How does transcription work?",
        "Explain metabolic pathways",
    ]
    
    rag_service = get_rag_service()
    if not rag_service.model:
        print("   ⚠️  RAG service LLM client not available")
        return []
    
    results = []
    for question in test_questions:
        print(f"\n❓ Question: '{question}'")
        try:
            answer_data = await rag_service.answer_question(question, max_context_items=5)
            
            answer = answer_data.get("answer", "")
            citations = answer_data.get("citations", [])
            sources = answer_data.get("sources", [])
            
            print(f"   ✅ Answer generated ({len(answer)} chars)")
            print(f"   📚 Citations: {len(citations)}")
            print(f"   📄 Sources: {len(sources)}")
            
            # Show answer preview
            if answer:
                preview = answer[:200] + "..." if len(answer) > 200 else answer
                print(f"   💬 Answer preview: {preview}")
            
            # Show citation types
            if citations:
                citation_types = {}
                for cit in citations:
                    cit_type = cit.get("type", "unknown")
                    citation_types[cit_type] = citation_types.get(cit_type, 0) + 1
                print(f"   📊 Citation types: {dict(citation_types)}")
            
            results.append({
                "question": question,
                "success": True,
                "answer_length": len(answer),
                "citations": len(citations),
                "sources": len(sources)
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                "question": question,
                "success": False,
                "error": str(e)
            })
    
    return results


async def main():
    """Run all tests."""
    print("="*70)
    print("VECTOR SEARCH & RAG TESTING")
    print("="*70)
    print("\nThis will test:")
    print("  1. Semantic search across all content types")
    print("  2. Content type filtering")
    print("  3. Similarity search")
    print("  4. RAG question answering")
    print()
    
    all_results = {}
    
    # Test 1: Semantic search
    all_results["semantic_search"] = await test_semantic_search()
    
    # Test 2: Content type filtering
    all_results["content_type_filtering"] = await test_content_type_search()
    
    # Test 3: Similarity search
    all_results["similarity_search"] = await test_similarity_search()
    
    # Test 4: RAG
    all_results["rag"] = await test_rag()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total_tests = sum(len(results) for results in all_results.values())
    passed = sum(sum(1 for r in results if r.get("success", False)) for results in all_results.values())
    failed = total_tests - passed
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {total_tests}")
    print(f"📈 Success rate: {passed/total_tests*100:.1f}%")
    
    # Detailed results
    print("\n📋 Detailed Results:")
    for test_name, results in all_results.items():
        test_passed = sum(1 for r in results if r.get("success", False))
        print(f"   {test_name}: {test_passed}/{len(results)} passed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

