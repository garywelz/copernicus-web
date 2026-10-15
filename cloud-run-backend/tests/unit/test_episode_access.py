"""Access control stage 1 (2026-10-15): one is_public rule on every route that returns episode data; a private episode answers 404 without the
admin key header and is visible with it. Offline, with a fake Firestore."""
import asyncio

import pytest
from fastapi import HTTPException

from utils.episode_access import admin_key_ok, can_view, is_public_episode

FEED = {"title": "Feed episode alpha", "description_markdown": "alpha text", "submitted_to_rss": True, "generated_at": "2026-10-03", "transcript_url": ""}
SITE = {"title": "Site only alpha", "description_markdown": "alpha text", "visible_on_web": True, "generated_at": "2026-10-02"}
PRIV = {"title": "Private alpha", "description_markdown": "alpha text", "submitted_to_rss": False, "visible_on_web": False,
        "visibility": "public", "script": "SECRET SCRIPT", "generated_at": "2026-10-04"}      # stale visibility must not make it public
EMPTY = {"title": "No flags alpha", "description_markdown": "alpha text", "generated_at": "2026-10-01"}
DOCS = {"ever-math-1": FEED, "ever-math-2": SITE, "ever-math-3": PRIV, "ever-math-4": EMPTY}
PUBLIC_IDS = {"ever-math-1", "ever-math-2"}


class Doc:
    def __init__(self, id_, data):
        self.id, self._d, self.exists = id_, data, data is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class Query:
    def __init__(self, docs):
        self.docs = docs

    def order_by(self, *a, **k):
        return Query(self.docs)

    def where(self, field, op, value):
        return Query([d for d in self.docs if d.to_dict().get(field) == value])

    def limit(self, n):
        return Query(self.docs[:n])

    def offset(self, n):
        return Query(self.docs[n:])

    def stream(self):
        return iter(self.docs)

    def document(self, id_):
        return type("Ref", (), {"get": staticmethod(lambda: next((d for d in self.docs if d.id == id_), Doc(id_, None)))})()


class FakeDB:
    def collection(self, name):
        return Query([Doc(k, v) for k, v in DOCS.items()])


def run(coro):
    loop = asyncio.new_event_loop()       # not asyncio.run: it unsets the thread's event loop, which other tests rely on
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ------------------------------------------------------------------ the rule
def test_rule_uses_the_two_flags_and_ignores_stored_visibility():
    assert is_public_episode(FEED) and is_public_episode(SITE)
    assert not is_public_episode(PRIV) and not is_public_episode(EMPTY)
    assert not is_public_episode({"visibility": "public"}) and not is_public_episode(None) and not is_public_episode("x")


def test_admin_key_only_with_the_right_value(monkeypatch):
    import utils.auth as auth
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "k-123")
    assert admin_key_ok("k-123") and admin_key_ok(" k-123 ")
    assert not admin_key_ok("wrong") and not admin_key_ok(None) and not admin_key_ok("")
    assert can_view(PRIV, "k-123") and not can_view(PRIV, None) and can_view(FEED, None)


@pytest.fixture
def routes(monkeypatch):
    from endpoints.public import routes as r
    monkeypatch.setattr(r, "db", FakeDB())
    monkeypatch.setattr(r, "admin_key_ok", lambda k: k == "ADMIN")
    return r


# ------------------------------------------------------------------ GET /api/episodes/{id}
def test_episode_record(routes):
    for pid in PUBLIC_IDS:
        assert run(routes.get_episode_record(pid, None))["episode_id"] == pid
    for pid in ("ever-math-3", "ever-math-4"):
        with pytest.raises(HTTPException) as e:
            run(routes.get_episode_record(pid, None))
        assert e.value.status_code == 404 and "SECRET" not in str(e.value.detail)         # 404, not 403, and no content
        with pytest.raises(HTTPException) as e2:
            run(routes.get_episode_record(pid, "wrong-key"))
        assert e2.value.status_code == 404
        assert run(routes.get_episode_record(pid, "ADMIN"))["episode_id"] == pid           # the admin key sees private
    with pytest.raises(HTTPException) as e3:
        run(routes.get_episode_record("does-not-exist", None))
    assert e3.value.status_code == 404                                                      # same answer as a private one


# ------------------------------------------------------------------ GET /api/episodes
def test_list(routes):
    out = run(routes.list_episode_catalog(category=None, submitted=None, limit=500, x_admin_api_key=None))
    assert {e["episode_id"] for e in out["episodes"]} == PUBLIC_IDS
    assert all("script" not in e for e in out["episodes"])
    out = run(routes.list_episode_catalog(category=None, submitted=None, limit=500, x_admin_api_key="ADMIN"))
    assert {e["episode_id"] for e in out["episodes"]} == set(DOCS)
    out = run(routes.list_episode_catalog(category=None, submitted=None, limit=1, x_admin_api_key=None))
    assert len(out["episodes"]) == 1                                                       # limit counts public episodes only


# ------------------------------------------------------------------ GET /api/episodes/search
def test_search(routes):
    out = run(routes.search_episodes(q="alpha", limit=100, search_transcripts=False, x_admin_api_key=None))
    assert {e["episode_id"] for e in out["episodes"]} == PUBLIC_IDS
    assert not any("Private" in e["title"] for e in out["episodes"])
    out = run(routes.search_episodes(q="alpha", limit=100, search_transcripts=False, x_admin_api_key="ADMIN"))
    assert {e["episode_id"] for e in out["episodes"]} == set(DOCS)
    out = run(routes.search_episodes(q="private", limit=100, search_transcripts=False, x_admin_api_key=None))
    assert out["episodes"] == []                                                           # a private title cannot be found


# ------------------------------------------------------------------ GET /browse?content_type=podcasts
def test_browse_podcasts_lists_and_counts_public_only(monkeypatch):
    from endpoints.content import routes as c
    monkeypatch.setattr(c, "db", FakeDB())
    out = run(c.browse_content(content_type="podcasts", process_family=None, discipline=None, question=None, engine=None,
                               keyword=None, channel=None, page=1, limit=50))
    items = out["items"] if isinstance(out, dict) else out.get("items")
    assert {i["id"] for i in items} == PUBLIC_IDS
    assert out["total"] == 2 if isinstance(out, dict) and "total" in out else True
    page2 = run(c.browse_content(content_type="podcasts", process_family=None, discipline=None, question=None, engine=None,
                                 keyword=None, channel=None, page=2, limit=1))
    assert len(page2["items"]) == 1 and page2["items"][0]["id"] in PUBLIC_IDS


# ------------------------------------------------------------------ knowledge map sampler and keyword/vector search
def test_knowledge_map_sampler(monkeypatch):
    from services.knowledge_map_service import KnowledgeMapService
    svc = KnowledgeMapService.__new__(KnowledgeMapService)
    svc.db = FakeDB()
    found = svc._fetch_podcast_items("alpha", 10)
    assert {d["job_id"] for d in found} == PUBLIC_IDS


def test_keyword_fallback_search_skips_private():
    from mcp_server.tools import vector_search as vs
    out = vs._keyword_fallback_search(FakeDB(), "alpha", ["podcasts"], 10)
    assert {d["job_id"] for d in out["podcasts"]} == PUBLIC_IDS


def test_the_remaining_episode_readers_are_all_behind_the_rule():
    """Static guard: every live module that streams the episode collection for a public answer imports the rule."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    for rel in ("endpoints/public/routes.py", "endpoints/content/routes.py", "services/knowledge_map_service.py", "mcp_server/tools/vector_search.py"):
        assert "is_public_episode" in (root / rel).read_text(encoding="utf-8"), rel
