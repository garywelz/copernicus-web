"""Who may see an episode. One rule for every route that returns episode data (access-control stage 1, 2026-10-15).

An episode is public when it is in the podcast feed (`submitted_to_rss`) or listed on the website (`visible_on_web`). Everything else is private:
routes answer 404 for it (never 403, so a guesser learns nothing), unless the request carries the admin key in the X-Admin-API-Key header.
The stored `visibility` field is not used: older records carry stale values of it (some say "public" for items that are in neither list).
"""
from typing import Any, Optional


def is_public_episode(record: Any) -> bool:
    """True only for a record that is in the feed or on the website."""
    return isinstance(record, dict) and bool(record.get("submitted_to_rss") or record.get("visible_on_web"))


def admin_key_ok(provided: Optional[str]) -> bool:
    """True when the X-Admin-API-Key header value is the admin key (constant-time comparison). Imported lazily: utils/__init__ imports auth eagerly."""
    from utils.auth import _admin_key_matches
    return _admin_key_matches(provided)


def can_view(record: Any, provided_admin_key: Optional[str]) -> bool:
    return is_public_episode(record) or admin_key_ok(provided_admin_key)
