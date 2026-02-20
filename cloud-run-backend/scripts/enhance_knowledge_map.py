#!/usr/bin/env python3
"""
Enhance Knowledge Map with Advanced Features

Adds Semantic Scholar citations and LLM-extracted concepts to existing knowledge map.
"""

import sys
import json
import argparse
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.knowledge_map_service import get_knowledge_map_service
from utils.logging import structured_logger


async def enhance_existing_map(
    input_file: str,
    output_file: str,
    use_semantic_scholar: bool = False,
    use_llm_concepts: bool = False,
    max_papers: Optional[int] = None
):
    """Enhance an existing knowledge map with additional relationships."""
    
    # Load existing map
    with open(input_file, 'r') as f:
        existing_map = json.load(f)
    
    print(f"📊 Loaded existing map: {len(existing_map.get('nodes', []))} nodes, {len(existing_map.get('edges', []))} edges")
    
    # Get papers from Firestore
    service = get_knowledge_map_service()
    papers_ref = service.db.collection('research_papers')
    papers_query = papers_ref.limit(max_papers) if max_papers else papers_ref
    
    papers = []
    for doc in papers_query.stream():
        paper_data = doc.to_dict()
        paper_data['paper_id'] = doc.id
        papers.append(paper_data)
    
    print(f"📚 Fetched {len(papers)} papers from Firestore")
    
    # Extract additional relationships
    new_edges = []
    
    if use_semantic_scholar:
        print("🔗 Fetching citations from Semantic Scholar...")
        citation_rels = await service.extract_citation_relationships(
            papers,
            use_semantic_scholar=True,
            max_papers_for_citations=max_papers
        )
        new_edges.extend(citation_rels)
        print(f"   Added {len(citation_rels)} citation relationships")
    
    if use_llm_concepts:
        print("🧠 Extracting concepts with LLM...")
        concepts = await service.extract_concepts_from_papers(
            papers,
            use_llm=True,
            max_papers_for_llm=max_papers
        )
        
        # Add concept nodes and edges
        existing_node_ids = {n.get('id') or n.get('data', {}).get('id') for n in existing_map.get('nodes', [])}
        
        for concept_name, paper_ids in concepts.items():
            concept_id = f'concept:{concept_name}'
            
            # Add concept node if not exists
            if concept_id not in existing_node_ids:
                existing_map['nodes'].append({
                    'data': {
                        'id': concept_id,
                        'label': concept_name,
                        'type': 'concept'
                    }
                })
                existing_node_ids.add(concept_id)
            
            # Add concept-paper edges
            for paper_id in paper_ids[:20]:
                new_edges.append({
                    'data': {
                        'id': f"{paper_id}-{concept_id}",
                        'source': paper_id,
                        'target': concept_id,
                        'type': 'mentions',
                        'weight': 1.0
                    }
                })
        
        print(f"   Added {len(concepts)} concepts and {len(new_edges)} concept relationships")
    
    # Merge edges
    existing_map['edges'].extend(new_edges)
    
    # Save enhanced map
    with open(output_file, 'w') as f:
        json.dump(existing_map, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Enhanced map saved to: {output_file}")
    print(f"   Total nodes: {len(existing_map['nodes'])}")
    print(f"   Total edges: {len(existing_map['edges'])}")


def main():
    parser = argparse.ArgumentParser(description="Enhance existing knowledge map")
    parser.add_argument("input", help="Input knowledge map JSON file")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--use-semantic-scholar", action="store_true", help="Add Semantic Scholar citations")
    parser.add_argument("--use-llm-concepts", action="store_true", help="Add LLM-extracted concepts")
    parser.add_argument("--max-papers", type=int, help="Maximum papers to process")
    
    args = parser.parse_args()
    
    asyncio.run(enhance_existing_map(
        args.input,
        args.output,
        use_semantic_scholar=args.use_semantic_scholar,
        use_llm_concepts=args.use_llm_concepts,
        max_papers=args.max_papers
    ))


if __name__ == "__main__":
    main()

