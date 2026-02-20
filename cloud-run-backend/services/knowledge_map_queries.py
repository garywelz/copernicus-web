"""
Knowledge Map Query Service

Provides interactive query capabilities for the knowledge map:
- Find papers by concept
- Find path between papers
- Find related papers
- Cluster analysis

Copyright (c) 2025 Gary Welz / CopernicusAI
Licensed under MIT License
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, deque

from services.knowledge_map_service import KnowledgeMapService
from utils.logging import structured_logger

logger = logging.getLogger(__name__)


class KnowledgeMapQueryService:
    """Service for querying the knowledge map."""
    
    def __init__(self, knowledge_map_service: KnowledgeMapService):
        """Initialize query service with knowledge map service."""
        self.km_service = knowledge_map_service
        self.nodes = knowledge_map_service.nodes
        self.edges = knowledge_map_service.edges
        
        # Build index for faster queries
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes for fast querying."""
        # Paper ID to node index
        self.paper_index = {}
        self.concept_index = {}
        self.edge_index = defaultdict(list)  # source -> [edges]
        self.reverse_edge_index = defaultdict(list)  # target -> [edges]
        
        for node_id, node in self.nodes.items():
            node_type = node.get('type', node.get('data', {}).get('type'))
            if node_type == 'paper':
                self.paper_index[node_id] = node
            elif node_type == 'concept':
                self.concept_index[node_id] = node
        
        for edge in self.edges:
            source = edge.get('source') or edge.get('data', {}).get('source')
            target = edge.get('target') or edge.get('data', {}).get('target')
            
            if source and target:
                self.edge_index[source].append(edge)
                self.reverse_edge_index[target].append(edge)
    
    def find_papers_by_concept(self, concept_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find papers that mention a specific concept.
        
        Args:
            concept_name: Name of the concept to search for
            limit: Maximum number of papers to return
        
        Returns:
            List of paper nodes
        """
        concept_id = f'concept:{concept_name.lower()}'
        
        # Find concept node
        concept_node = self.concept_index.get(concept_id)
        if not concept_node:
            # Try fuzzy match
            for cid, cnode in self.concept_index.items():
                if concept_name.lower() in cid.lower():
                    concept_id = cid
                    concept_node = cnode
                    break
        
        if not concept_node:
            return []
        
        # Find papers connected to this concept
        papers = []
        for edge in self.edge_index.get(concept_id, []):
            target = edge.get('target') or edge.get('data', {}).get('target')
            if target in self.paper_index:
                papers.append(self.paper_index[target])
        
        # Also check reverse edges
        for edge in self.reverse_edge_index.get(concept_id, []):
            source = edge.get('source') or edge.get('data', {}).get('source')
            if source in self.paper_index:
                papers.append(self.paper_index[source])
        
        # Remove duplicates and limit
        seen = set()
        unique_papers = []
        for paper in papers:
            paper_id = paper.get('id') or paper.get('data', {}).get('id')
            if paper_id not in seen:
                seen.add(paper_id)
                unique_papers.append(paper)
                if len(unique_papers) >= limit:
                    break
        
        return unique_papers
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        relationship_types: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two papers.
        
        Args:
            source_id: Source paper ID
            target_id: Target paper ID
            max_depth: Maximum path length
            relationship_types: Filter by relationship types (None for all)
        
        Returns:
            List of edges representing the path, or None if no path found
        """
        if source_id == target_id:
            return []
        
        # BFS to find shortest path
        queue = deque([(source_id, [])])
        visited = {source_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if len(path) >= max_depth:
                continue
            
            # Check outgoing edges
            for edge in self.edge_index.get(current_id, []):
                edge_type = edge.get('type') or edge.get('data', {}).get('type')
                target = edge.get('target') or edge.get('data', {}).get('target')
                
                if relationship_types and edge_type not in relationship_types:
                    continue
                
                if target == target_id:
                    return path + [edge]
                
                if target not in visited:
                    visited.add(target)
                    queue.append((target, path + [edge]))
            
            # Check incoming edges (for bidirectional relationships)
            for edge in self.reverse_edge_index.get(current_id, []):
                edge_type = edge.get('type') or edge.get('data', {}).get('type')
                source = edge.get('source') or edge.get('data', {}).get('source')
                
                if relationship_types and edge_type not in relationship_types:
                    continue
                
                if source == target_id:
                    return path + [edge]
                
                if source not in visited:
                    visited.add(source)
                    queue.append((source, path + [edge]))
        
        return None
    
    def find_related_papers(
        self,
        paper_id: str,
        depth: int = 2,
        max_papers: int = 20,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find papers related to a given paper.
        
        Args:
            paper_id: Paper ID to find related papers for
            depth: How many relationship hops to explore
            max_papers: Maximum number of papers to return
            relationship_types: Filter by relationship types
        
        Returns:
            List of related paper nodes
        """
        related = []
        visited = {paper_id}
        queue = deque([(paper_id, 0)])
        
        while queue and len(related) < max_papers:
            current_id, current_depth = queue.popleft()
            
            if current_depth >= depth:
                continue
            
            # Get connected papers
            for edge in self.edge_index.get(current_id, []):
                edge_type = edge.get('type') or edge.get('data', {}).get('type')
                target = edge.get('target') or edge.get('data', {}).get('target')
                
                if relationship_types and edge_type not in relationship_types:
                    continue
                
                if target in self.paper_index and target not in visited:
                    visited.add(target)
                    related.append(self.paper_index[target])
                    queue.append((target, current_depth + 1))
            
            for edge in self.reverse_edge_index.get(current_id, []):
                edge_type = edge.get('type') or edge.get('data', {}).get('type')
                source = edge.get('source') or edge.get('data', {}).get('source')
                
                if relationship_types and edge_type not in relationship_types:
                    continue
                
                if source in self.paper_index and source not in visited:
                    visited.add(source)
                    related.append(self.paper_index[source])
                    queue.append((source, current_depth + 1))
        
        return related[:max_papers]
    
    def search_papers(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search papers by title or other metadata.
        
        Args:
            query: Search query string
            limit: Maximum number of results
        
        Returns:
            List of matching paper nodes
        """
        query_lower = query.lower()
        matches = []
        
        for paper_id, paper in self.paper_index.items():
            title = paper.get('label') or paper.get('data', {}).get('label', '')
            if query_lower in title.lower():
                matches.append(paper)
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_paper_cluster(
        self,
        paper_id: str,
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get cluster of closely connected papers.
        
        Uses simple community detection: papers connected by multiple relationship types.
        
        Args:
            paper_id: Seed paper ID
            min_cluster_size: Minimum papers in cluster
        
        Returns:
            List of papers in the cluster
        """
        if paper_id not in self.paper_index:
            return []
        
        cluster = {paper_id}
        queue = deque([paper_id])
        
        while queue:
            current_id = queue.popleft()
            
            # Count connections to other papers
            connections = defaultdict(int)
            
            for edge in self.edge_index.get(current_id, []):
                target = edge.get('target') or edge.get('data', {}).get('target')
                if target in self.paper_index:
                    connections[target] += 1
            
            for edge in self.reverse_edge_index.get(current_id, []):
                source = edge.get('source') or edge.get('data', {}).get('source')
                if source in self.paper_index:
                    connections[source] += 1
            
            # Add papers with multiple connections
            for connected_id, connection_count in connections.items():
                if connected_id not in cluster and connection_count >= 2:
                    cluster.add(connected_id)
                    queue.append(connected_id)
        
        if len(cluster) < min_cluster_size:
            return []
        
        return [self.paper_index[pid] for pid in cluster if pid in self.paper_index]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge map."""
        paper_count = len(self.paper_index)
        concept_count = len(self.concept_index)
        edge_count = len(self.edges)
        
        # Count by relationship type
        relationship_counts = defaultdict(int)
        for edge in self.edges:
            edge_type = edge.get('type') or edge.get('data', {}).get('type', 'unknown')
            relationship_counts[edge_type] += 1
        
        return {
            'papers': paper_count,
            'concepts': concept_count,
            'edges': edge_count,
            'relationship_types': dict(relationship_counts),
            'total_nodes': paper_count + concept_count
        }


def get_query_service(knowledge_map_service: KnowledgeMapService) -> KnowledgeMapQueryService:
    """Get or create query service instance."""
    return KnowledgeMapQueryService(knowledge_map_service)

