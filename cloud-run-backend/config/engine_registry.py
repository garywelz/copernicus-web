"""Engine registry (architecture review Phase 2, gap 1, 2026-10-02).

Maps each knowledge-engine project to its question_scope_ids tags, label,
and description. Scoped retrieval filters on
`question_scope_ids ARRAY_CONTAINS_ANY <engine's tags>` -- not discipline,
and not a tag-prefix match (Firestore has no "starts with" operator on
array elements) -- per the architecture review's own finding: GLMP is not
"the biology discipline" and ATAP is not "the mathematics discipline"
(lib/knowledge-engine-projects.ts's header comment says so directly).

Gary's decision (architecture review Phase 2, gap 1, 2026-10-02): v1 drops
"include general corpus" from the design. An engine toggle scopes
strictly to that engine's tagged papers; "All projects" (engine=None, or
omitted) stays exactly as today -- fully unscoped, no question_scope_ids
filter at all.

Tag lists below are the exact, live distinct `question_scope_ids` values
found in `research_papers` as of 2026-10-02 (23 total: 12 GLMP, 9 ATAP,
2 TDAP), not hand-derived from each engine's `research_focus.json` --
that file declares a question's existence, not whether any paper has
actually been tagged with it, and the two have already drifted once
(GLMP's own q1/q11 split). This list needs updating by hand whenever a
new question is added and acquisition actually tags papers with it --
there is no live auto-discovery here. See BULLETIN entries and the
Phase 2 gap-1 report for the investigation this is built from.

**Design item recorded for later, not built here: "gap 1b" -- auto-tag
newly ingested papers against each engine's research_focus.json questions
at ingest time, so this list (and the underlying corpus coverage) doesn't
keep drifting from what's actually been declared. Today, daily ingestion
never tags anything; question_scope_ids is only ever written by two
manual scripts (citation_expansion_pilot.py, researcher_cited_intake.py).**
"""

from typing import Dict, List, Optional, TypedDict


class EngineConfig(TypedDict):
    label: str
    full_name: str
    tags: List[str]


ENGINE_REGISTRY: Dict[str, EngineConfig] = {
    "glmp": {
        "label": "GLMP",
        "full_name": "Genome Logic Modeling Project",
        "tags": [
            "glmp-q1", "glmp-q2", "glmp-q3", "glmp-q4", "glmp-q5", "glmp-q6",
            "glmp-q7", "glmp-q8", "glmp-q9", "glmp-q10", "glmp-q11", "glmp-f1",
        ],
    },
    "atap": {
        "label": "ATAP",
        "full_name": "Axiomatic Theories, Algorithms and Proofs",
        "tags": [
            "atap-q1", "atap-q2", "atap-q3", "atap-q4",
            "atap-f1", "atap-f2", "atap-f3", "atap-f4", "atap-f5",
        ],
    },
    "tdap": {
        "label": "TDAP",
        "full_name": "Topological Data Analysis Project",
        "tags": ["tdap-q1", "tdap-q2"],
    },
}

ENGINE_IDS = tuple(ENGINE_REGISTRY.keys())

# Firestore's array_contains_any accepts at most 30 values per query. Every
# current engine is well under that (GLMP's 12 is the largest) -- this
# constant exists so a future engine with a larger tag list fails loudly
# at registry-definition time, not with an opaque Firestore error at
# request time.
ARRAY_CONTAINS_ANY_MAX_VALUES = 30


def is_valid_engine_id(engine_id: Optional[str]) -> bool:
    return bool(engine_id) and engine_id in ENGINE_REGISTRY


def engine_tags(engine_id: str) -> List[str]:
    """Raises KeyError for an unknown engine_id -- callers should validate
    with is_valid_engine_id() first and return 400 on failure, not let
    this raise as an unhandled 500."""
    tags = ENGINE_REGISTRY[engine_id]["tags"]
    assert len(tags) <= ARRAY_CONTAINS_ANY_MAX_VALUES, (
        f"engine {engine_id!r} has {len(tags)} tags, over Firestore's "
        f"array_contains_any limit of {ARRAY_CONTAINS_ANY_MAX_VALUES} -- "
        "split into multiple queries before shipping this engine."
    )
    return tags


def engine_label(engine_id: str) -> str:
    return ENGINE_REGISTRY[engine_id]["label"]
