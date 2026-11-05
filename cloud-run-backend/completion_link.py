"""Which link the "your episode is ready" email carries (onboarding PR 1 follow-up, design Q2).

An owner's private episode is opened only through short-lived links minted per play (15 minutes, the dashboard's Play button). The ready email therefore
does NOT mail a file link to an owner: it links to the subscriber dashboard. The one exception is the administrator's own account, whose review links only the
administrator sees: it keeps the 7-day signed link the email always had (curated and admin-generated episodes are reviewed that way).
"""
from typing import Any, Callable, Dict, Optional

import media_store

DASHBOARD_URL = "https://www.copernicusai.fyi/subscriber-dashboard.html"


def completion_email_link(subscriber_id: Optional[str], public_audio_url: Optional[str], admin_subscriber_id: Optional[str], episode_id: str,
                          sign: Optional[Callable[..., Optional[str]]] = None) -> Dict[str, Any]:
    """Arguments for the ready email: {audio_url, link_valid_days, dashboard_url}. Nothing is signed unless the recipient is the administrator's own account."""
    if not (subscriber_id and admin_subscriber_id and subscriber_id == admin_subscriber_id):
        return {"audio_url": None, "link_valid_days": None, "dashboard_url": DASHBOARD_URL}
    try:
        signed = (sign or media_store.signed_audio_link)(episode_id, media_store.MAX_SIGNED_DAYS)
    except Exception:
        signed = None
    if signed:
        return {"audio_url": signed, "link_valid_days": media_store.MAX_SIGNED_DAYS, "dashboard_url": None}
    return {"audio_url": public_audio_url, "link_valid_days": None, "dashboard_url": None}
