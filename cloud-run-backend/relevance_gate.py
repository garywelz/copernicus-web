"""Relevance gate (gap 3 fix 1b, stage b).

Confirmation proves a paper exists; it does not prove the paper is about the topic. On the first real generation through the new
image, arXiv was unreachable and five unrelated Zenodo records (garment design, crop yields, ...) were confirmed and became an
episode. This module scores each confirmed paper against the topic with the system's own embedding model
(text-embedding-3-small, the model stored on every episode) and drops papers below RELEVANCE_THRESHOLD. It also enforces that at
least ``minimum`` of the kept papers come from outside Zenodo (arXiv, PubMed or Crossref): Zenodo records do not count toward the
minimum. If the scoring itself cannot run, the episode fails (RelevanceCheckUnavailable); an unchecked paper is never let through.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from paper_confirmation import Dropped

# Calibrated 2026-10-13 on the 119 confirmed papers of the 10 sandbox topics (see sandbox/relevance_calibration.json): 0.25 removes
# the clearly unrelated papers (industrial IoT among metalloenzymes papers, garment and crop records for a mathematics topic) and
# keeps 9-12 of 12 papers for every on-topic sandbox topic.
RELEVANCE_THRESHOLD = 0.25
ZENODO_DOI_PREFIX = "10.5281/zenodo."
MAX_TEXT_CHARS = 6000

EmbedBatch = Callable[[List[str]], List[List[float]]]


class RelevanceCheckUnavailable(Exception):
    """The embedding service could not score the papers, so relevance could not be checked."""


def paper_text(c: Any) -> str:
    return f"{c.title}. {c.abstract or ''}"[:MAX_TEXT_CHARS]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def is_zenodo(c: Any) -> bool:
    return ((c.ids or {}).get("doi") or "").lower().startswith(ZENODO_DOI_PREFIX)


def default_embed_batch() -> EmbedBatch:
    from services.llm_providers.openai_embedding import OpenAIEmbeddingService
    return OpenAIEmbeddingService().embed_batch


async def relevance_scores(topic: str, papers: Sequence[Any], embed_batch: Optional[EmbedBatch] = None) -> Dict[str, float]:
    """Cosine similarity of each paper (title + abstract) to the topic, by pid. One embeddings call, retried once."""
    if not papers:
        return {}
    texts = [topic[:MAX_TEXT_CHARS]] + [paper_text(p) for p in papers]
    last: Optional[BaseException] = None
    for _ in range(2):
        try:
            embed = embed_batch or default_embed_batch()
            vectors = await asyncio.to_thread(embed, texts)
            if len(vectors) != len(texts):
                raise ValueError(f"expected {len(texts)} embeddings, got {len(vectors)}")
            return {p.pid: round(cosine(vectors[0], v), 4) for p, v in zip(papers, vectors[1:])}
        except Exception as e:  # network, key, quota
            last = e
    raise RelevanceCheckUnavailable(f"{type(last).__name__}: {last}")


def apply_gate(papers: Sequence[Any], scores: Dict[str, float], threshold: float = RELEVANCE_THRESHOLD,
               exempt_pids: Sequence[str] = ()) -> Tuple[List[Any], List[Dropped]]:
    """Keep papers scoring at least the threshold; a directly requested paper (exempt) is always kept."""
    kept, dropped = [], []
    for p in papers:
        s = scores.get(p.pid)
        if p.pid in exempt_pids or s is None or s >= threshold:
            kept.append(p)
        else:
            dropped.append(Dropped(p.title, "off_topic", dict(p.ids or {}), s))
    return kept, dropped


def outside_zenodo(papers: Sequence[Any]) -> int:
    """How many papers come from arXiv, PubMed or Crossref (everything except Zenodo)."""
    return sum(1 for p in papers if not is_zenodo(p))
