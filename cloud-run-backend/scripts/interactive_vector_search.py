#!/usr/bin/env python3
"""
Interactive Vector Search & RAG Demo

A simple command-line interface to test vector search and RAG capabilities.
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.vector_search import search_semantic, find_similar_content
from services.rag_service import get_rag_service


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_results(results_json: str, max_items: int = 3):
    """Pretty print search results."""
    try:
        results = json.loads(results_json)
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
            return
        
        # Print summary
        counts = results.get("counts", {})
        print(f"📊 Found: {counts.get('papers', 0)} papers, "
              f"{counts.get('glmp_processes', 0)} GLMP processes, "
              f"{counts.get('podcasts', 0)} podcasts "
              f"(total: {counts.get('total', 0)})")
        
        # Print top papers
        papers = results.get("papers", [])[:max_items]
        if papers:
            print(f"\n📄 Top Papers:")
            for i, paper in enumerate(papers, 1):
                title = paper.get("title", "Untitled")[:60]
                score = paper.get("similarity_score", 0)
                print(f"   {i}. {title}... (similarity: {score:.3f})")
        
        # Print top GLMP processes
        glmp = results.get("glmp_processes", [])[:max_items]
        if glmp:
            print(f"\n🔬 Top GLMP Processes:")
            for i, process in enumerate(glmp, 1):
                title = process.get("title", "Untitled")[:60]
                score = process.get("similarity_score", 0)
                print(f"   {i}. {title}... (similarity: {score:.3f})")
        
        # Print top podcasts
        podcasts = results.get("podcasts", [])[:max_items]
        if podcasts:
            print(f"\n🎙️  Top Podcasts:")
            for i, podcast in enumerate(podcasts, 1):
                result = podcast.get("result", {})
                title = result.get("title") or podcast.get("title", "Untitled")
                title = title[:60] if title else "Untitled"
                score = podcast.get("similarity_score", 0)
                print(f"   {i}. {title}... (similarity: {score:.3f})")
                
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing results: {e}")
        print(f"Raw output: {results_json[:500]}")


def print_rag_result(result: dict):
    """Pretty print RAG answer."""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n💬 Answer:")
    print("-" * 70)
    answer = result.get("answer", "No answer generated")
    print(answer)
    print("-" * 70)
    
    citations = result.get("citations", [])
    if citations:
        print(f"\n📚 Sources ({len(citations)}):")
        for citation in citations[:5]:  # Show first 5
            num = citation.get("number", "?")
            ctype = citation.get("type", "unknown")
            title = citation.get("title", "Untitled")[:50]
            print(f"   [{num}] {ctype}: {title}...")
        if len(citations) > 5:
            print(f"   ... and {len(citations) - 5} more")


async def demo_semantic_search():
    """Demo semantic search."""
    print_section("SEMANTIC SEARCH DEMO")
    
    queries = [
        "DNA replication",
        "metabolic pathways",
        "cell division",
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 70)
        results = await search_semantic(query, limit=5)
        print_results(results, max_items=2)
    
    # Interactive query
    print("\n" + "="*70)
    print("Try your own query! (or press Enter to continue)")
    user_query = input("> ").strip()
    
    if user_query:
        print(f"\n🔍 Query: '{user_query}'")
        print("-" * 70)
        results = await search_semantic(user_query, limit=5)
        print_results(results, max_items=3)


async def demo_content_filtering():
    """Demo content type filtering."""
    print_section("CONTENT TYPE FILTERING DEMO")
    
    query = "biology"
    
    print(f"Query: '{query}'")
    print("\n1. All content types:")
    results = await search_semantic(query, content_types=["papers", "glmp", "podcasts"], limit=3)
    print_results(results, max_items=2)
    
    print("\n2. Papers only:")
    results = await search_semantic(query, content_types=["papers"], limit=3)
    print_results(results, max_items=3)
    
    print("\n3. GLMP processes only:")
    results = await search_semantic(query, content_types=["glmp"], limit=3)
    print_results(results, max_items=3)


async def demo_similarity_search():
    """Demo similarity search."""
    print_section("SIMILARITY SEARCH DEMO")
    
    # Find a GLMP process ID
    print("Finding a sample GLMP process...")
    results = await search_semantic("DNA", content_types=["glmp"], limit=1)
    results_data = json.loads(results)
    
    glmp_processes = results_data.get("glmp_processes", [])
    if glmp_processes:
        process = glmp_processes[0]
        process_id = process.get("process_id") or process.get("id")
        process_title = process.get("title", "Unknown")
        
        print(f"\n🔬 Finding content similar to: '{process_title}'")
        print(f"   Process ID: {process_id}")
        print("-" * 70)
        
        similar = await find_similar_content(process_id, "glmp", limit=5)
        similar_data = json.loads(similar)
        
        if "error" not in similar_data:
            print(f"\n📊 Found:")
            print(f"   - {len(similar_data.get('similar_papers', []))} similar papers")
            print(f"   - {len(similar_data.get('similar_glmp_processes', []))} similar GLMP processes")
            print(f"   - {len(similar_data.get('similar_podcasts', []))} similar podcasts")
            
            # Show top similar GLMP
            similar_glmp = similar_data.get("similar_glmp_processes", [])[:3]
            if similar_glmp:
                print(f"\n🔬 Most Similar GLMP Processes:")
                for i, p in enumerate(similar_glmp, 1):
                    title = p.get("title", "Untitled")[:60]
                    score = p.get("similarity_score", 0)
                    print(f"   {i}. {title}... (similarity: {score:.3f})")
        else:
            print(f"❌ Error: {similar_data['error']}")
    else:
        print("❌ No GLMP processes found to use as example")


async def demo_rag():
    """Demo RAG question answering."""
    print_section("RAG (RETRIEVAL-AUGMENTED GENERATION) DEMO")
    
    rag_service = get_rag_service()
    
    if not rag_service.llm_available:
        print("❌ RAG service not available (LLM model not initialized)")
        return
    
    questions = [
        "What is DNA replication?",
        "Explain metabolic pathways",
    ]
    
    for question in questions:
        print(f"\n❓ Question: {question}")
        print("-" * 70)
        
        result = await rag_service.answer_question(question, max_context_items=5)
        print_rag_result(result)
    
    # Interactive question
    print("\n" + "="*70)
    print("Ask your own question! (or press Enter to finish)")
    user_question = input("> ").strip()
    
    if user_question:
        print(f"\n❓ Question: {user_question}")
        print("-" * 70)
        result = await rag_service.answer_question(user_question, max_context_items=5)
        print_rag_result(result)


async def main():
    """Main interactive demo."""
    print("\n" + "="*70)
    print("  VECTOR SEARCH & RAG INTERACTIVE DEMO")
    print("="*70)
    print("\nThis demo will show you:")
    print("  1. Semantic search across all content")
    print("  2. Content type filtering")
    print("  3. Similarity search")
    print("  4. RAG question answering")
    print("\nPress Enter to start...")
    input()
    
    try:
        # Run demos
        await demo_semantic_search()
        print("\n\n")
        await demo_content_filtering()
        print("\n\n")
        await demo_similarity_search()
        print("\n\n")
        await demo_rag()
        
        print("\n" + "="*70)
        print("  DEMO COMPLETE")
        print("="*70)
        print("\n✅ All demos completed successfully!")
        print("\nTo use these features in your code:")
        print("  - Import: from mcp_server.tools.vector_search import search_semantic, find_similar_content")
        print("  - Import: from services.rag_service import get_rag_service")
        print("  - Use the async functions as shown in this demo")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

