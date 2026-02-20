#!/usr/bin/env python3
"""
Batch Indexing Script for Vector Search

Generates embeddings for all existing content (papers, GLMP processes, podcasts)
and stores them in Firestore for vector search capabilities.

Usage:
    python scripts/index_existing_content.py [--content-type papers|glmp|podcasts|all] [--limit N] [--dry-run]
"""

import asyncio
import sys
import os
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.embedding_service import get_embedding_service
from mcp_server.utils.firestore_client import get_firestore_client
from google.cloud.firestore_v1.vector import Vector
from mcp_server.config import (
    COLLECTION_PAPERS,
    COLLECTION_PODCASTS,
    COLLECTION_EPISODES,
    COLLECTION_GLMP_PROCESSES,
    COLLECTION_MATH_PROCESSES,
    COLLECTION_CHEMISTRY_PROCESSES,
    COLLECTION_PHYSICS_PROCESSES,
    COLLECTION_COMPUTER_SCIENCE_PROCESSES,
)
from utils.logging import structured_logger

# Initialize services
embedding_service = get_embedding_service()
db = get_firestore_client()


def create_text_for_paper(paper: Dict[str, Any]) -> str:
    """Create text representation of paper for embedding (cheap RAG/search mode)."""
    parts = []
    
    if paper.get('title'):
        parts.append(paper['title'])
    
    if paper.get('abstract'):
        parts.append(paper['abstract'])
    
    return '\n'.join(parts)


def create_text_for_process(process: Dict[str, Any]) -> str:
    """Create text representation of a process for embedding (cheap mode)."""
    parts = []
    
    title = process.get('title') or process.get('name')
    if title:
        parts.append(str(title))
    
    if process.get('description'):
        parts.append(process['description'])
    
    return '\n'.join(parts)


def create_text_for_podcast(podcast: Dict[str, Any]) -> str:
    """Create text representation of podcast for embedding (cheap mode)."""
    parts = []
    
    result = podcast.get("result", {}) if isinstance(podcast.get("result"), dict) else {}
    title = result.get("title") or podcast.get("title")
    if title:
        parts.append(str(title))
    
    description = result.get("description") or podcast.get("description")
    if description:
        parts.append(str(description))
    
    return '\n'.join(parts)


async def index_papers(limit: Optional[int] = None, dry_run: bool = False) -> int:
    """Generate and store embeddings for research papers."""
    structured_logger.info("Starting paper indexing", limit=limit, dry_run=dry_run)
    
    papers_ref = db.collection(COLLECTION_PAPERS)
    papers = papers_ref.stream()
    
    indexed_count = 0
    skipped_count = 0
    error_count = 0
    
    texts_to_embed = []
    paper_refs = []
    paper_ids = []
    
    # Collect papers that need indexing
    for paper_doc in papers:
        if limit and indexed_count + skipped_count >= limit:
            break
        
        paper_data = paper_doc.to_dict()
        paper_id = paper_doc.id
        
        # Skip if already has embedding
        if paper_data.get('embedding'):
            skipped_count += 1
            continue
        
        # Create text for embedding
        text = create_text_for_paper(paper_data)
        if not text or not text.strip():
            skipped_count += 1
            continue
        
        texts_to_embed.append(text)
        paper_refs.append(papers_ref.document(paper_id))
        paper_ids.append(paper_id)
    
    if not texts_to_embed:
        structured_logger.info("No papers need indexing", skipped=skipped_count)
        return 0
    
    structured_logger.info(
        f"Processing {len(texts_to_embed)} papers",
        total=len(texts_to_embed),
        skipped=skipped_count
    )
    
    if dry_run:
        structured_logger.info("DRY RUN: Would index papers", count=len(texts_to_embed))
        return len(texts_to_embed)
    
    # Generate embeddings in batches
    try:
        embeddings = embedding_service.embed_batch(texts_to_embed, batch_size=50)
        
        # Update Firestore documents
        batch = db.batch()
        batch_count = 0
        
        for i, (paper_ref, embedding, paper_id) in enumerate(zip(paper_refs, embeddings, paper_ids)):
            if embedding is None:
                error_count += 1
                continue
            
            batch.update(paper_ref, {
                # IMPORTANT: store as Firestore Vector type for vector search.
                'embedding': Vector(embedding),
                'embedding_model': getattr(embedding_service, "model_name", "text-embedding-004"),
                'embedding_updated': datetime.utcnow().isoformat()
            })
            
            indexed_count += 1
            batch_count += 1
            
            # Firestore batch limit is 500
            if batch_count >= 500:
                batch.commit()
                batch = db.batch()
                batch_count = 0
                structured_logger.info(f"Indexed batch: {indexed_count} papers so far")
        
        # Commit remaining
        if batch_count > 0:
            batch.commit()
        
        structured_logger.info(
            "Paper indexing complete",
            indexed=indexed_count,
            skipped=skipped_count,
            errors=error_count
        )
        
    except Exception as e:
        structured_logger.error("Error during paper indexing", error=str(e))
        raise
    
    return indexed_count


async def index_glmp_processes(limit: Optional[int] = None, dry_run: bool = False) -> int:
    """Generate and store embeddings for process collections in Firestore."""
    structured_logger.info("Starting process indexing", limit=limit, dry_run=dry_run)
    
    async def _index_process_collection(collection_name: str) -> int:
        processes_ref = db.collection(collection_name)
        docs = processes_ref.stream()
        
        indexed_count = 0
        skipped_count = 0
        error_count = 0
        
        texts_to_embed: List[str] = []
        doc_refs = []
        doc_ids = []
        
        for doc in docs:
            if limit and indexed_count + skipped_count >= limit:
                break
            d = doc.to_dict() or {}
            if d.get("embedding"):
                skipped_count += 1
                continue
            text = create_text_for_process(d)
            if not text or not text.strip():
                skipped_count += 1
                continue
            texts_to_embed.append(text)
            doc_refs.append(processes_ref.document(doc.id))
            doc_ids.append(doc.id)
        
        if not texts_to_embed:
            structured_logger.info("No processes need indexing", collection=collection_name, skipped=skipped_count)
            return 0
        
        structured_logger.info(
            "Processing processes for embedding",
            collection=collection_name,
            total=len(texts_to_embed),
            skipped=skipped_count
        )
        
        if dry_run:
            structured_logger.info("DRY RUN: Would index processes", collection=collection_name, count=len(texts_to_embed))
            return len(texts_to_embed)
        
        embeddings = embedding_service.embed_batch(texts_to_embed, batch_size=50)
        
        batch = db.batch()
        batch_count = 0
        for ref, embedding, _id in zip(doc_refs, embeddings, doc_ids):
            if embedding is None:
                error_count += 1
                continue
            batch.update(ref, {
                "embedding": Vector(embedding),
                "embedding_model": getattr(embedding_service, "model_name", "text-embedding-004"),
                "embedding_updated": datetime.utcnow().isoformat(),
            })
            indexed_count += 1
            batch_count += 1
            if batch_count >= 500:
                batch.commit()
                batch = db.batch()
                batch_count = 0
                structured_logger.info("Indexed process batch", collection=collection_name, indexed=indexed_count)
        
        if batch_count > 0:
            batch.commit()
        
        structured_logger.info(
            "Process indexing complete",
            collection=collection_name,
            indexed=indexed_count,
            skipped=skipped_count,
            errors=error_count
        )
        return indexed_count
    
    total = 0
    for coll in [
        COLLECTION_GLMP_PROCESSES,
        COLLECTION_MATH_PROCESSES,
        COLLECTION_CHEMISTRY_PROCESSES,
        COLLECTION_PHYSICS_PROCESSES,
        COLLECTION_COMPUTER_SCIENCE_PROCESSES,
    ]:
        total += await _index_process_collection(coll)
    
    return total


async def index_podcasts(limit: Optional[int] = None, dry_run: bool = False) -> int:
    """Generate and store embeddings for podcasts."""
    structured_logger.info("Starting podcast indexing", limit=limit, dry_run=dry_run)
    
    podcasts_ref = db.collection(COLLECTION_PODCASTS)
    podcasts = podcasts_ref.stream()
    
    indexed_count = 0
    skipped_count = 0
    error_count = 0
    
    texts_to_embed = []
    podcast_refs = []
    podcast_ids = []
    
    # Collect podcasts that need indexing
    for podcast_doc in podcasts:
        if limit and indexed_count + skipped_count >= limit:
            break
        
        podcast_data = podcast_doc.to_dict()
        podcast_id = podcast_doc.id
        
        # Skip if already has embedding
        if podcast_data.get('embedding'):
            skipped_count += 1
            continue
        
        # Create text for embedding
        text = create_text_for_podcast(podcast_data)
        if not text or not text.strip():
            skipped_count += 1
            continue
        
        texts_to_embed.append(text)
        podcast_refs.append(podcasts_ref.document(podcast_id))
        podcast_ids.append(podcast_id)
    
    if not texts_to_embed:
        structured_logger.info("No podcasts need indexing", skipped=skipped_count)
        return 0
    
    structured_logger.info(
        f"Processing {len(texts_to_embed)} podcasts",
        total=len(texts_to_embed),
        skipped=skipped_count
    )
    
    if dry_run:
        structured_logger.info("DRY RUN: Would index podcasts", count=len(texts_to_embed))
        return len(texts_to_embed)
    
    # Generate embeddings in batches
    try:
        embeddings = embedding_service.embed_batch(texts_to_embed, batch_size=50)
        
        # Update Firestore documents
        batch = db.batch()
        batch_count = 0
        
        for i, (podcast_ref, embedding, podcast_id) in enumerate(zip(podcast_refs, embeddings, podcast_ids)):
            if embedding is None:
                error_count += 1
                continue
            
            batch.update(podcast_ref, {
                'embedding': Vector(embedding),
                'embedding_model': getattr(embedding_service, "model_name", "text-embedding-004"),
                'embedding_updated': datetime.utcnow().isoformat()
            })
            
            indexed_count += 1
            batch_count += 1
            
            # Firestore batch limit is 500
            if batch_count >= 500:
                batch.commit()
                batch = db.batch()
                batch_count = 0
                structured_logger.info(f"Indexed batch: {indexed_count} podcasts so far")
        
        # Commit remaining
        if batch_count > 0:
            batch.commit()
        
        structured_logger.info(
            "Podcast indexing complete",
            indexed=indexed_count,
            skipped=skipped_count,
            errors=error_count
        )
        
    except Exception as e:
        structured_logger.error("Error during podcast indexing", error=str(e))
        raise
    
    return indexed_count


async def main():
    """Main entry point for batch indexing."""
    parser = argparse.ArgumentParser(description='Index existing content with embeddings')
    parser.add_argument(
        '--content-type',
        choices=['papers', 'processes', 'podcasts', 'all'],
        default='all',
        help='Type of content to index'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of items to process (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate embeddings but do not store them'
    )
    
    args = parser.parse_args()
    
    structured_logger.info(
        "Starting batch indexing",
        content_type=args.content_type,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    total_indexed = 0
    
    try:
        if args.content_type in ['papers', 'all']:
            count = await index_papers(limit=args.limit, dry_run=args.dry_run)
            total_indexed += count
            structured_logger.info(f"Papers indexed: {count}")
        
        if args.content_type in ['processes', 'all']:
            count = await index_glmp_processes(limit=args.limit, dry_run=args.dry_run)
            total_indexed += count
            structured_logger.info(f"Processes indexed: {count}")
        
        if args.content_type in ['podcasts', 'all']:
            count = await index_podcasts(limit=args.limit, dry_run=args.dry_run)
            total_indexed += count
            structured_logger.info(f"Podcasts indexed: {count}")
        
        structured_logger.info(
            "Batch indexing complete",
            total_indexed=total_indexed,
            dry_run=args.dry_run
        )
        
    except Exception as e:
        structured_logger.error("Batch indexing failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


