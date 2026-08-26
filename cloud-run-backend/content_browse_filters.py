"""Pure browse-filter helpers for /api/content/browse.

Keep this module free of Firestore so unit tests do not need GCP.
Keyword matching is literal substring (title/description/tags/channel),
not vector search — Browse is inventory, Search is meaning.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DISC_ALIASES = {
    "cs": "computer_science",
    "computer-science": "computer_science",
    "computer_science": "computer_science",
    "math": "mathematics",
    "mathematics": "mathematics",
    "bio": "biology",
    "biology": "biology",
    "chem": "chemistry",
    "chemistry": "chemistry",
    "physics": "physics",
    "interdisciplinary": "interdisciplinary",
}

PAPER_KEYWORD_SCAN_CAP = 1500
PAPER_QUESTION_SCAN_CAP = 25000
VIDEO_SCAN_CAP = 3000


def normalize_discipline(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = str(value).strip().lower().replace(" ", "_")
    if not key:
        return None
    return DISC_ALIASES.get(key, key)


def video_disciplines(doc: Dict[str, Any]) -> List[str]:
    raw = doc.get("disciplines") or []
    if isinstance(raw, str):
        raw = [raw]
    out: List[str] = []
    for item in raw:
        norm = normalize_discipline(str(item))
        if norm:
            out.append(norm)
    return out


def video_question_ids(doc: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    top = doc.get("question_scope_ids")
    if isinstance(top, list):
        ids.extend(str(x) for x in top if x)
    meta = doc.get("metadata")
    if isinstance(meta, dict):
        nested = meta.get("question_scope_ids")
        if isinstance(nested, list):
            ids.extend(str(x) for x in nested if x)
    seen = set()
    unique: List[str] = []
    for qid in ids:
        qid = qid.strip()
        if qid and qid not in seen:
            seen.add(qid)
            unique.append(qid)
    return unique


def _haystack(*parts: Any) -> str:
    chunks: List[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, (list, tuple)):
            chunks.extend(str(x) for x in part if x)
        else:
            chunks.append(str(part))
    return " ".join(chunks).lower()


def matches_keyword(haystack: str, keyword: Optional[str]) -> bool:
    needle = (keyword or "").strip().lower()
    if not needle:
        return True
    return needle in haystack


def video_matches(
    doc: Dict[str, Any],
    *,
    discipline: Optional[str] = None,
    channel: Optional[str] = None,
    question: Optional[str] = None,
    keyword: Optional[str] = None,
) -> bool:
    want_disc = normalize_discipline(discipline)
    if want_disc and want_disc not in video_disciplines(doc):
        return False
    want_channel = (channel or "").strip()
    if want_channel and (doc.get("channel_name") or "").strip() != want_channel:
        return False
    want_q = (question or "").strip()
    if want_q and want_q not in video_question_ids(doc):
        return False
    hay = _haystack(
        doc.get("title"),
        doc.get("description"),
        doc.get("channel_name"),
        doc.get("tags"),
        video_question_ids(doc),
    )
    return matches_keyword(hay, keyword)


def paper_matches_keyword(doc: Dict[str, Any], keyword: Optional[str]) -> bool:
    hay = _haystack(
        doc.get("title"),
        doc.get("abstract"),
        doc.get("journal"),
        doc.get("journal_full"),
        (doc.get("metadata") or {}).get("categories") if isinstance(doc.get("metadata"), dict) else None,
        doc.get("question_scope_ids"),
    )
    return matches_keyword(hay, keyword)


def paper_matches_discipline(doc: Dict[str, Any], discipline: Optional[str]) -> bool:
    want = normalize_discipline(discipline)
    if not want:
        return True
    return normalize_discipline(doc.get("discipline")) == want


def paginate(items: Sequence[Any], page: int, limit: int) -> Tuple[List[Any], int]:
    page = max(int(page), 1)
    limit = max(int(limit), 1)
    total = len(items)
    start = (page - 1) * limit
    return list(items[start : start + limit]), total


def facet_values(
    docs: Iterable[Dict[str, Any]],
    *,
    discipline: Optional[str] = None,
    channel: Optional[str] = None,
    question: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Counts for each facet with the other filters applied (classic faceted browse)."""
    material = list(docs)
    disc_base = [
        d
        for d in material
        if video_matches(d, channel=channel, question=question, keyword=keyword)
    ]
    chan_base = [
        d
        for d in material
        if video_matches(d, discipline=discipline, question=question, keyword=keyword)
    ]
    q_base = [
        d
        for d in material
        if video_matches(d, discipline=discipline, channel=channel, keyword=keyword)
    ]

    disc_counts: Counter[str] = Counter()
    for doc in disc_base:
        for disc in video_disciplines(doc):
            disc_counts[disc] += 1

    chan_counts: Counter[str] = Counter()
    for doc in chan_base:
        name = (doc.get("channel_name") or "").strip()
        if name:
            chan_counts[name] += 1

    q_counts: Counter[str] = Counter()
    for doc in q_base:
        for qid in video_question_ids(doc):
            q_counts[qid] += 1

    return {
        "disciplines": [
            {"id": k, "count": v} for k, v in sorted(disc_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "channels": [
            {"id": k, "label": k, "count": v}
            for k, v in sorted(chan_counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
        ],
        "questions": [
            {"id": k, "count": v} for k, v in sorted(q_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    }
