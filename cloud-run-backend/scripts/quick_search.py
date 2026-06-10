#!/usr/bin/env python3
"""
Quick Vector Search - Simple one-liner search

Usage:
    python3 quick_search.py "your query here"
    python3 quick_search.py "DNA replication" --type papers
    python3 quick_search.py "metabolic pathways" --type glmp --limit 10
"""

import sys
import asyncio
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools.vector_search import search_semantic, find_similar_content
from services.rag_service import get_rag_service


async def quick_search(query: str, content_types: list = None, limit: int = 5):
    """Quick semantic search."""
    results = await search_semantic(query, content_types=content_types, limit=limit)
    data = json.loads(results)
    
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        return
    
    counts = data.get("counts", {})
    print(f"\n🔍 Query: '{query}'")
    print(f"📊 Found: {counts.get('papers', 0)} papers, "
          f"{counts.get('glmp_processes', 0)} GLMP, "
          f"{counts.get('math_processes', 0)} math, "
          f"{counts.get('chemistry_processes', 0)} chemistry, "
          f"{counts.get('physics_processes', 0)} physics, "
          f"{counts.get('computer_science_processes', 0)} CS, "
          f"{counts.get('podcasts', 0)} podcasts")
    
    # Show top results
    papers = data.get("papers", [])[:3]
    if papers:
        print(f"\n📄 Papers:")
        for p in papers:
            print(f"   • {p.get('title', 'Untitled')[:70]} (score: {p.get('similarity_score', 0):.3f})")
    
    glmp = data.get("glmp_processes", [])[:3]
    if glmp:
        print(f"\n🔬 GLMP Processes:")
        for g in glmp:
            print(f"   • {g.get('title', 'Untitled')[:70]} (score: {g.get('similarity_score', 0):.3f})")
    
    math = data.get("math_processes", [])[:3]
    if math:
        print(f"\n📐 Math Processes:")
        for m in math:
            print(f"   • {m.get('title', 'Untitled')[:70]} (score: {m.get('similarity_score', 0):.3f})")
    
    chemistry = data.get("chemistry_processes", [])[:3]
    if chemistry:
        print(f"\n🧪 Chemistry Processes:")
        for c in chemistry:
            print(f"   • {c.get('title', 'Untitled')[:70]} (score: {c.get('similarity_score', 0):.3f})")
    
    physics = data.get("physics_processes", [])[:3]
    if physics:
        print(f"\n⚛️  Physics Processes:")
        for p in physics:
            print(f"   • {p.get('title', 'Untitled')[:70]} (score: {p.get('similarity_score', 0):.3f})")
    
    cs = data.get("computer_science_processes", [])[:3]
    if cs:
        print(f"\n💻 Computer Science Processes:")
        for c in cs:
            print(f"   • {c.get('title', 'Untitled')[:70]} (score: {c.get('similarity_score', 0):.3f})")
    
    podcasts = data.get("podcasts", [])[:3]
    if podcasts:
        print(f"\n🎙️  Podcasts:")
        for p in podcasts:
            result = p.get("result", {})
            title = result.get("title") or p.get("title", "Untitled")
            print(f"   • {title[:70]} (score: {p.get('similarity_score', 0):.3f})")


async def quick_rag(question: str):
    """Quick RAG question answering."""
    rag_service = get_rag_service()
    
    if not rag_service.llm_available:
        print("❌ RAG service not available")
        return
    
    result = await rag_service.answer_question(question, max_context_items=5)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n❓ Question: {question}")
    print(f"\n💬 Answer:\n{result.get('answer', 'No answer')}")
    
    citations = result.get("citations", [])
    if citations:
        print(f"\n📚 Sources ({len(citations)}):")
        for c in citations[:5]:
            print(f"   [{c.get('number')}] {c.get('type')}: {c.get('title', 'Untitled')[:60]}")


def main():
    parser = argparse.ArgumentParser(description="Quick vector search and RAG")
    parser.add_argument("query", help="Search query or question")
    parser.add_argument("--type", choices=["papers", "glmp", "podcasts", "math", "chemistry", "physics", "computer_science"], 
                       action="append", help="Filter by content type (can use multiple)")
    parser.add_argument("--limit", type=int, default=5, help="Max results per type (default: 5)")
    parser.add_argument("--rag", action="store_true", help="Use RAG to answer the query")
    parser.add_argument("--similar", type=str, help="Find similar content (provide content ID)")
    parser.add_argument("--similar-type", choices=["paper", "podcast", "glmp", "math", "chemistry", "physics", "computer_science"], 
                       default="glmp", help="Type of content for similarity search")
    
    args = parser.parse_args()
    
    if args.similar:
        # Similarity search
        asyncio.run(find_similar_content(args.similar, args.similar_type, args.limit))
    elif args.rag:
        # RAG question answering
        asyncio.run(quick_rag(args.query))
    else:
        # Semantic search
        asyncio.run(quick_search(args.query, args.type, args.limit))


if __name__ == "__main__":
    main()

