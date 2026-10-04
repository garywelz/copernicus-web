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

**Chosen over live prefix-resolution (PR #32 review, change 1,
2026-10-04): a drift *check*, not a drift-proof mechanism.** Firestore
has no "array contains an element starting with X" operator, so a truly
live-resolving registry would mean either a full distinct-value scan of
`research_papers` per request (defeats the point of a cheap registry
lookup) or a background job that periodically rebuilds this file's
in-memory equivalent -- which is the same architecture as the drift
check below, just automated into the hot path before anyone has needed
that. `scripts/check_engine_registry_drift.py` does the live scan
instead, read-only, run by hand or in CI, and reports (not silently
fixes) any `question_scope_ids` value Firestore has that no engine here
claims -- see `find_unregistered_tags()`.

**Design item recorded for later, not built here: "gap 1b" -- auto-tag
newly ingested papers against each engine's research_focus.json questions
at ingest time, so this list (and the underlying corpus coverage) doesn't
keep drifting from what's actually been declared. Today, daily ingestion
never tags anything; question_scope_ids is only ever written by two
manual scripts (citation_expansion_pilot.py, researcher_cited_intake.py).**
"""

from typing import Dict, FrozenSet, Iterable, List, Optional, Set, TypedDict


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
# current engine is well under that (GLMP's 12 is the largest).
ARRAY_CONTAINS_ANY_MAX_VALUES = 30

#: The union of every engine's tags -- the registry's own notion of "fully
#: covered." Used by the drift check (scripts/check_engine_registry_drift.py)
#: to find any question_scope_ids value Firestore has that no engine claims.
ALL_REGISTERED_TAGS: FrozenSet[str] = frozenset(
    tag for config in ENGINE_REGISTRY.values() for tag in config["tags"]
)


class EngineTagLimitExceeded(Exception):
    """Raised by engine_tags() when an engine's tag list has grown past
    Firestore's array_contains_any limit (30). This is a registry
    misconfiguration, not a caller error -- route handlers should catch it
    and return 500, not let it surface as an unhandled AssertionError.

    Deliberately NOT auto-split-and-merged into multiple queries: no
    current engine is within even half of the limit (GLMP's 12 is the
    largest), and correctly merging paginated results across several
    Firestore queries -- preserving page/offset semantics, not just
    concatenating -- is real complexity not worth building against a
    hypothetical case. Build it when an engine actually approaches 30
    tags, informed by that engine's real pagination needs, not now.
    """

    def __init__(self, engine_id: str, tag_count: int):
        self.engine_id = engine_id
        self.tag_count = tag_count
        super().__init__(
            f"Engine {engine_id!r} has {tag_count} tags, over Firestore's "
            f"array_contains_any limit of {ARRAY_CONTAINS_ANY_MAX_VALUES}. "
            "This engine cannot be queried as a single array_contains_any "
            "call; split-and-merge was deliberately not built for this -- "
            "see EngineTagLimitExceeded's docstring."
        )


def is_valid_engine_id(engine_id: Optional[str]) -> bool:
    return bool(engine_id) and engine_id in ENGINE_REGISTRY


def engine_tags(engine_id: str) -> List[str]:
    """Raises KeyError for an unknown engine_id -- callers should validate
    with is_valid_engine_id() first and return 400 on failure, not let
    this raise as an unhandled 500. Raises EngineTagLimitExceeded if the
    engine has grown past Firestore's array_contains_any limit -- callers
    should catch that and return 500 (registry misconfiguration, not a
    caller error)."""
    tags = ENGINE_REGISTRY[engine_id]["tags"]
    if len(tags) > ARRAY_CONTAINS_ANY_MAX_VALUES:
        raise EngineTagLimitExceeded(engine_id, len(tags))
    return tags


def engine_label(engine_id: str) -> str:
    return ENGINE_REGISTRY[engine_id]["label"]


def find_unregistered_tags(live_distinct_tags: Iterable[str]) -> Set[str]:
    """Drift check (change 1 of the PR #32 review, 2026-10-04): given the
    set of question_scope_ids values actually found live in Firestore,
    return any that no engine's registry entry claims. A non-empty result
    means a new question (e.g. a hypothetical 'tdap-q3') has started
    being tagged in production without anyone updating this file --
    those papers would silently fall outside every engine's scoped
    retrieval until the registry catches up. Pure function, no Firestore
    access -- see scripts/check_engine_registry_drift.py for the live
    scan this is meant to be called with."""
    return set(live_distinct_tags) - ALL_REGISTERED_TAGS
