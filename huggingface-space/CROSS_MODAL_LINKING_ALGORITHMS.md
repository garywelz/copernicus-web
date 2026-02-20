# Cross-Modal Linking Algorithms

**NSF Objective 2:** Unified Multi-Modal Metadata Representation  
**Purpose:** Algorithms and strategies for linking content across modalities (papers, videos, processes, podcasts, etc.)  
**Last Updated:** January 10, 2025

## Overview

Cross-modal linking enables the Knowledge Engine to discover and display relationships between different types of content, creating a unified knowledge graph. This document describes the algorithms, strategies, and implementation approaches for linking content across modalities.

## Linking Strategies

### 1. Citation/Reference-Based Linking

**Principle:** Direct citations and references provide explicit connections between content.

**Implementation:**

#### Papers → Papers
- Use existing citation networks
- Extract citations from paper metadata
- Match cited papers by DOI, PMID, arXiv ID

#### Processes → Papers
- Extract `sources[].paper_id` from process metadata
- Direct links from `sources` array
- Validate paper IDs exist in database

#### Podcasts → Papers
- Extract `references[].paper_id` from podcast metadata
- Direct links from `references` array
- Validate paper IDs exist in database

**Algorithm:**
```python
def link_by_citations(content_item, all_papers):
    """Link content to papers via citations/references."""
    related_papers = []
    
    # Check sources/references for paper IDs
    if "sources" in content_item:
        for source in content_item["sources"]:
            if "paper_id" in source:
                paper_id = source["paper_id"]
                if paper_id in all_papers:
                    related_papers.append(paper_id)
    
    if "references" in content_item:
        for ref in content_item["references"]:
            if "paper_id" in ref:
                paper_id = ref["paper_id"]
                if paper_id in all_papers:
                    related_papers.append(paper_id)
    
    return list(set(related_papers))  # Deduplicate
```

### 2. Entity-Based Linking

**Principle:** Content mentioning the same entities (genes, proteins, compounds, concepts) are related.

**Implementation:**

#### Entity Extraction
- **Papers:** Extract entities from abstracts, titles using NER (Named Entity Recognition)
- **Videos:** Extract entities from transcripts using NER
- **Podcasts:** Extract entities from scripts/transcripts using NER
- **Processes:** Extract entities from descriptions, Mermaid node labels
- **Video Data:** Extract entities from annotations, temporal metadata

#### Entity Matching
- Exact match: Same entity name
- Normalization: Case-insensitive, acronym expansion
- Synonym matching: Use entity ontologies (UniProt, ChEBI, Gene Ontology)
- Temporal matching: For video/video_data, match entities appearing at same time

**Algorithm:**
```python
def link_by_entities(content_item, all_content, entity_index):
    """Link content via shared entities."""
    related_items = []
    
    # Get entities from current item
    item_entities = extract_entities(content_item)
    item_entity_names = {e["name"].lower() for e in item_entities}
    
    # Find content with overlapping entities
    for other_item in all_content:
        if other_item["id"] == content_item["id"]:
            continue
        
        other_entities = extract_entities(other_item)
        other_entity_names = {e["name"].lower() for e in other_entities}
        
        # Calculate entity overlap
        overlap = item_entity_names & other_entity_names
        if len(overlap) > 0:
            confidence = len(overlap) / max(len(item_entity_names), len(other_entity_names))
            if confidence > 0.3:  # Threshold
                related_items.append({
                    "id": other_item["id"],
                    "confidence": confidence,
                    "shared_entities": list(overlap)
                })
    
    return sorted(related_items, key=lambda x: x["confidence"], reverse=True)
```

### 3. Keyword-Based Linking

**Principle:** Content sharing keywords are likely related.

**Implementation:**

#### Keyword Extraction
- **Papers:** From abstracts, titles, keywords fields
- **Videos:** From titles, descriptions, transcripts
- **Podcasts:** From titles, descriptions, scripts
- **Processes:** From descriptions, keywords fields

#### Keyword Matching
- Exact keyword match
- Stemmed keyword match (e.g., "replication" matches "replicate")
- TF-IDF similarity for keyword sets
- Weighted by keyword importance (title keywords > description keywords)

**Algorithm:**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def link_by_keywords(content_items):
    """Link content via keyword similarity."""
    # Extract keyword text for each item
    keyword_texts = []
    for item in content_items:
        keywords = item.get("keywords", [])
        title = item.get("title", "")
        keywords_str = " ".join(keywords + [title])
        keyword_texts.append(keywords_str)
    
    # Compute TF-IDF similarity
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(keyword_texts)
    
    # Calculate cosine similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)
    
    # Find related items
    related_links = []
    for i, item in enumerate(content_items):
        similarities = similarity_matrix[i]
        for j, similarity in enumerate(similarities):
            if i != j and similarity > 0.3:  # Threshold
                related_links.append({
                    "source": item["id"],
                    "target": content_items[j]["id"],
                    "similarity": float(similarity)
                })
    
    return related_links
```

### 4. Semantic Similarity Linking

**Principle:** Content with semantically similar text are related.

**Implementation:**

#### Embedding Generation
- Use Vertex AI embeddings (text-embedding-004)
- Generate embeddings for:
  - Paper abstracts
  - Video transcripts
  - Podcast scripts
  - Process descriptions

#### Similarity Calculation
- Cosine similarity between embeddings
- Threshold: similarity > 0.7 for strong links, > 0.5 for moderate links
- Cross-modal: Compare embeddings across different content types

**Algorithm:**
```python
def link_by_semantic_similarity(content_item, all_content, embeddings):
    """Link content via semantic similarity."""
    related_items = []
    
    item_embedding = embeddings.get(content_item["id"])
    if not item_embedding:
        return []
    
    for other_item in all_content:
        if other_item["id"] == content_item["id"]:
            continue
        
        other_embedding = embeddings.get(other_item["id"])
        if not other_embedding:
            continue
        
        # Calculate cosine similarity
        similarity = cosine_similarity([item_embedding], [other_embedding])[0][0]
        
        if similarity > 0.5:  # Threshold
            related_items.append({
                "id": other_item["id"],
                "similarity": float(similarity)
            })
    
    return sorted(related_items, key=lambda x: x["similarity"], reverse=True)
```

### 5. Temporal Linking

**Principle:** Content created or published around the same time about similar topics are related.

**Implementation:**

#### Temporal Clustering
- Group content by publication year
- Within same year, use other linking methods (keywords, entities)
- Identify temporal trends and relationships

**Algorithm:**
```python
def link_by_temporal_proximity(content_items, max_year_diff=2):
    """Link content published in similar time periods."""
    from collections import defaultdict
    
    # Group by year
    by_year = defaultdict(list)
    for item in content_items:
        year = item.get("year")
        if year:
            by_year[year].append(item)
    
    # Link within temporal windows
    related_links = []
    years = sorted(by_year.keys())
    
    for i, year in enumerate(years):
        items_in_year = by_year[year]
        
        # Link within same year
        for item1 in items_in_year:
            for item2 in items_in_year:
                if item1["id"] != item2["id"]:
                    # Apply other linking methods (keywords, entities)
                    if link_by_keywords([item1, item2]):
                        related_links.append({
                            "source": item1["id"],
                            "target": item2["id"],
                            "year": year,
                            "temporal": True
                        })
        
        # Link to nearby years
        for nearby_year in years[i+1:i+max_year_diff+1]:
            if int(nearby_year) - int(year) <= max_year_diff:
                for item1 in items_in_year:
                    for item2 in by_year[nearby_year]:
                        # Apply other linking methods
                        if link_by_keywords([item1, item2]):
                            related_links.append({
                                "source": item1["id"],
                                "target": item2["id"],
                                "year_diff": int(nearby_year) - int(year)
                            })
    
    return related_links
```

### 6. Category/Discipline-Based Linking

**Principle:** Content in the same discipline/category with overlapping subcategories are related.

**Implementation:**

#### Category Matching
- Same `category`: biology, chemistry, physics, etc.
- Overlapping `subcategories`: More specific matching
- Interdisciplinary content links to multiple categories

**Algorithm:**
```python
def link_by_category(content_item, all_content):
    """Link content in same categories/subcategories."""
    related_items = []
    
    item_category = content_item.get("category")
    item_subcats = set(content_item.get("subcategories", []))
    
    for other_item in all_content:
        if other_item["id"] == content_item["id"]:
            continue
        
        other_category = other_item.get("category")
        other_subcats = set(other_item.get("subcategories", []))
        
        # Same category
        if item_category and item_category == other_category:
            # Calculate subcategory overlap
            subcat_overlap = item_subcats & other_subcats
            if subcat_overlap:
                related_items.append({
                    "id": other_item["id"],
                    "category": item_category,
                    "subcategory_overlap": len(subcat_overlap),
                    "shared_subcategories": list(subcat_overlap)
                })
    
    return sorted(related_items, key=lambda x: x["subcategory_overlap"], reverse=True)
```

## Combined Linking Algorithm

**Principle:** Combine multiple linking strategies with weighted confidence scores.

**Implementation:**

```python
def link_content_comprehensive(content_item, all_content, embeddings=None):
    """
    Comprehensive cross-modal linking using multiple strategies.
    Returns: List of related items with confidence scores.
    """
    related_items = defaultdict(lambda: {"confidence": 0.0, "reasons": []})
    
    # 1. Citation-based (highest confidence)
    citation_links = link_by_citations(content_item, all_content)
    for paper_id in citation_links:
        related_items[paper_id]["confidence"] += 0.8
        related_items[paper_id]["reasons"].append("citation")
    
    # 2. Entity-based (high confidence)
    entity_links = link_by_entities(content_item, all_content, entity_index)
    for link in entity_links:
        item_id = link["id"]
        related_items[item_id]["confidence"] += 0.6 * link["confidence"]
        related_items[item_id]["reasons"].append(f"entities: {link['shared_entities']}")
    
    # 3. Keyword-based (moderate confidence)
    keyword_links = link_by_keywords([content_item] + all_content)
    for link in keyword_links:
        if link["source"] == content_item["id"]:
            item_id = link["target"]
            related_items[item_id]["confidence"] += 0.4 * link["similarity"]
            related_items[item_id]["reasons"].append("keywords")
    
    # 4. Semantic similarity (moderate confidence)
    if embeddings:
        semantic_links = link_by_semantic_similarity(content_item, all_content, embeddings)
        for link in semantic_links:
            item_id = link["id"]
            related_items[item_id]["confidence"] += 0.5 * link["similarity"]
            related_items[item_id]["reasons"].append("semantic")
    
    # 5. Category-based (low confidence, but useful)
    category_links = link_by_category(content_item, all_content)
    for link in category_links:
        item_id = link["id"]
        related_items[item_id]["confidence"] += 0.2
        related_items[item_id]["reasons"].append("category")
    
    # Normalize confidence (max = 1.0)
    for item_id in related_items:
        related_items[item_id]["confidence"] = min(1.0, related_items[item_id]["confidence"])
    
    # Filter by threshold and sort
    threshold = 0.3
    filtered = {
        item_id: data for item_id, data in related_items.items()
        if data["confidence"] >= threshold
    }
    
    return sorted(
        [{"id": k, **v} for k, v in filtered.items()],
        key=lambda x: x["confidence"],
        reverse=True
    )
```

## Implementation Priority

### Phase 1: Direct Links (Immediate)
1. ✅ Citation/Reference-based linking (already in schemas)
2. ✅ Category-based linking (simple implementation)

### Phase 2: Keyword & Entity Extraction
1. Extract keywords from all content types
2. Extract entities using NER (spaCy, BioBERT)
3. Implement keyword-based linking
4. Implement entity-based linking

### Phase 3: Semantic Similarity
1. Generate embeddings for all content
2. Implement semantic similarity matching
3. Cross-modal semantic linking

### Phase 4: Advanced
1. Temporal linking
2. Combined algorithm with confidence scores
3. Machine learning for link prediction
4. User feedback to improve links

## Cross-Modal Query Examples

### Find all content about DNA replication:
```python
query = "DNA replication"
related = []

# Search papers
papers = search_papers(query)
related.extend(papers)

# Search videos with transcript
videos = search_videos_transcript(query)
related.extend(videos)

# Search podcasts with script
podcasts = search_podcasts_script(query)
related.extend(podcasts)

# Search processes by description
processes = search_processes_description(query)
related.extend(processes)

# Then cross-link all results
for item in related:
    item["related_items"] = link_content_comprehensive(item, related)
```

### Find videos explaining a process:
```python
process_id = "process_biology_dna-replication"

# Direct links
related_videos = get_related_videos(process_id)

# Semantic links
process = get_process(process_id)
videos = search_videos_semantic(process["description"])
related_videos.extend(videos)

# Entity-based links
process_entities = extract_entities(process)
videos_with_entities = find_videos_with_entities(process_entities)
related_videos.extend(videos_with_entities)
```

## Metrics & Evaluation

### Link Quality Metrics
- **Precision:** % of links that are actually relevant
- **Recall:** % of relevant links found
- **Confidence Distribution:** Distribution of confidence scores
- **Cross-Modal Coverage:** % of cross-modal links vs same-modal

### Evaluation Methods
- Manual review of top links
- User feedback on link relevance
- A/B testing of different thresholds
- Comparison with ground truth (if available)

---

**Status:** ✅ Algorithms documented, 🔄 Implementation in progress  
**Next Steps:** Implement keyword extraction, entity extraction, semantic similarity  
**NSF Alignment:** Supports Objective 2 cross-modal linking requirements
