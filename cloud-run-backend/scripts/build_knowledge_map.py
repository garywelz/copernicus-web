#!/usr/bin/env python3
"""
Build Mathematics Knowledge Map

Extracts relationships from papers and builds a knowledge graph.
"""

import sys
import json
import argparse
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.knowledge_map_service import get_knowledge_map_service
from utils.logging import structured_logger


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build mathematics knowledge map")
    parser.add_argument(
        "--max-papers",
        type=int,
        default=None,
        help="Maximum number of papers to include (default: all)"
    )
    parser.add_argument(
        "--no-concepts",
        action="store_true",
        help="Don't extract concept nodes"
    )
    parser.add_argument(
        "--no-similarity",
        action="store_true",
        help="Don't include similarity-based relationships"
    )
    parser.add_argument(
        "--no-categories",
        action="store_true",
        help="Don't include category-based relationships"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="knowledge_map.json",
        help="Output file path (default: knowledge_map.json)"
    )
    parser.add_argument(
        "--format",
        choices=["cytoscape", "d3", "raw"],
        default="cytoscape",
        help="Output format (default: cytoscape)"
    )
    parser.add_argument(
        "--use-semantic-scholar",
        action="store_true",
        help="Use Semantic Scholar API for citation data"
    )
    parser.add_argument(
        "--use-llm-concepts",
        action="store_true",
        help="Use LLM for concept extraction (more detailed)"
    )
    parser.add_argument(
        "--max-citations",
        type=int,
        default=None,
        help="Maximum papers to fetch citations for (to limit API calls)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("MATHEMATICS KNOWLEDGE MAP BUILDER")
    print("=" * 80)
    print(f"Max papers: {args.max_papers or 'All'}")
    print(f"Include concepts: {not args.no_concepts}")
    print(f"Include similarity: {not args.no_similarity}")
    print(f"Include categories: {not args.no_categories}")
    print(f"Output format: {args.format}")
    print("=" * 80)
    print()
    
    # Build knowledge map
    service = get_knowledge_map_service()
    
    print("🔨 Building knowledge graph...")
    graph = asyncio.run(service.build_graph(
        max_papers=args.max_papers,
        include_concepts=not args.no_concepts,
        include_similarity=not args.no_similarity,
        include_categories=not args.no_categories,
        use_semantic_scholar=args.use_semantic_scholar,
        use_llm_concepts=args.use_llm_concepts,
        max_papers_for_citations=args.max_citations
    ))
    
    print(f"\n✅ Graph built successfully!")
    print(f"   Nodes: {len(graph['nodes'])}")
    print(f"   Edges: {len(graph['edges'])}")
    print(f"   Papers: {graph['metadata']['papers']}")
    print(f"   Concepts: {graph['metadata']['concepts']}")
    print(f"   Relationships: {graph['metadata']['relationships']}")
    
    # Export for visualization
    if args.format == "raw":
        output_data = graph
    else:
        output_data = service.export_for_visualization(format=args.format)
        output_data['metadata'] = graph['metadata']
    
    # Save to file
    output_path = Path(args.output)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved to: {output_path}")
    print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    # Show sample
    print(f"\n📋 Sample nodes (first 5):")
    for node in graph['nodes'][:5]:
        print(f"   - {node['type']}: {node['label'][:60]}")
    
    print(f"\n📋 Sample edges (first 5):")
    for edge in graph['edges'][:5]:
        print(f"   - {edge['type']}: {edge['source'][:30]} → {edge['target'][:30]}")


if __name__ == "__main__":
    main()

