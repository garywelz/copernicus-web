"""PR 1 follow-up: no long-lived private links to owners (design Q2), the owner dashboard hides Listen for a private episode and no longer promises feed
access, and the admin RSS buttons use the editors-only route. Offline."""
import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import completion_link as cl
import media_store as ms
from email_service import EmailService

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "cloud-run-backend"
ADMIN_ID, OWNER_ID = "admin-sub", "owner-sub"
SIGNED = "https://storage.googleapis.com/regal-scholar-453620-r7-private-media/audio/ever-x-1.mp3?X-Goog-Expires=604800&X-Goog-Signature=abc"


def read(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def send(**kw):
    """Run the real email builder with SMTP replaced; return the HTML body that would have been sent."""
    svc = EmailService()
    svc.sender_password = "x"
    sent = []

    class Server:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **k): pass
        def login(self, *a): pass
        def send_message(self, msg): sent.append(msg)

    base = dict(recipient_email="o@example.org", job_id="job1", podcast_title="T", topic="t", duration="5-10 minutes", canonical_filename="ever-x-1")
    loop = asyncio.new_event_loop()          # a private loop: asyncio.run() would close the global one other tests rely on
    try:
        with patch("email_service.smtplib.SMTP", Server):
            ok = loop.run_until_complete(svc.send_podcast_completion_email(**{**base, **kw}))
    finally:
        loop.close()
    assert ok is True and len(sent) == 1
    return sent[0].get_payload()[0].get_payload(decode=True).decode("utf-8")


# ---- 3a. the ready email -------------------------------------------------------------------------------------------------------------------
def test_an_owners_ready_email_has_no_storage_link_and_opens_the_dashboard():
    never = MagicMock(side_effect=AssertionError("a link must not be signed for an owner"))
    args = cl.completion_email_link(OWNER_ID, "https://storage.googleapis.com/pub/audio/ever-x-1.mp3", ADMIN_ID, "ever-x-1", sign=never)
    never.assert_not_called()
    assert args == {"audio_url": None, "link_valid_days": None, "dashboard_url": cl.DASHBOARD_URL}
    body = send(audio_url=args["audio_url"], link_valid_days=args["link_valid_days"], dashboard_url=args["dashboard_url"])
    assert "storage.googleapis.com" not in body and "X-Goog" not in body and "audio/ever-x-1" not in body
    assert cl.DASHBOARD_URL in body and "Open your dashboard to listen" in body and "stays private until you make it public" in body
    assert "Private link, valid for" not in body


def test_the_administrators_own_review_link_is_unchanged():
    calls = []
    args = cl.completion_email_link(ADMIN_ID, "pub-url", ADMIN_ID, "ever-x-1", sign=lambda eid, days: calls.append((eid, days)) or SIGNED)
    assert calls == [("ever-x-1", ms.MAX_SIGNED_DAYS)] and args == {"audio_url": SIGNED, "link_valid_days": 7, "dashboard_url": None}
    body = send(audio_url=args["audio_url"], link_valid_days=args["link_valid_days"], dashboard_url=args["dashboard_url"])
    assert "X-Goog-Expires=604800" in body and "valid for 7 days" in body and "Listen to Podcast" in body        # curated / admin review mail as before


def test_the_admin_link_falls_back_to_the_public_address_if_signing_fails():
    def boom(eid, days):
        raise RuntimeError("no signer")
    assert cl.completion_email_link(ADMIN_ID, "pub-url", ADMIN_ID, "e", sign=boom) == {"audio_url": "pub-url", "link_valid_days": None, "dashboard_url": None}
    assert cl.completion_email_link(ADMIN_ID, "pub-url", ADMIN_ID, "e", sign=lambda e, d: None)["audio_url"] == "pub-url"


@pytest.mark.parametrize("sub,admin", [(None, ADMIN_ID), ("", ADMIN_ID), (OWNER_ID, None), (OWNER_ID, "")])
def test_no_subscriber_or_no_admin_id_never_gets_a_signed_link(sub, admin):
    never = MagicMock(side_effect=AssertionError("must not sign"))
    assert cl.completion_email_link(sub, "p", admin, "e", sign=never)["dashboard_url"] == cl.DASHBOARD_URL
    never.assert_not_called()


def test_the_generation_service_sends_the_ready_email_through_the_helper_only():
    src = read(BACKEND / "services" / "podcast_generation_service.py")
    assert "completion_email_link" in src and "signed_audio_link" not in src and "MAX_SIGNED_DAYS" not in src
    assert "dashboard_url=link_args" in src


# ---- 3c. no long-lived signed link is stored on a job or episode record ---------------------------------------------------------------------------
LONG_LIVED_MINTS = re.compile(r"signed_audio_link|MAX_SIGNED_DAYS|signed_links\(|signed_url\(|owner_media_links")


def test_signing_happens_only_in_the_reviewed_places_and_never_in_a_record_writer():
    allowed = {"media_store.py", "completion_link.py", "elevenlabs_voice_service.py", "endpoints/admin/routes.py", "endpoints/subscriber/episode_access.py"}
    found = set()
    for p in BACKEND.rglob("*.py"):
        rel = p.relative_to(BACKEND).as_posix()
        if rel.startswith(("tests/", "test_env/", "backend_venv/", "venv/", "scripts/")) or "site-packages" in rel:
            continue
        if LONG_LIVED_MINTS.search(read(p)):
            found.add(rel)
    assert found <= allowed, found - allowed                     # nothing that writes a job, episode or feed record mints a signed link
    for writer in ("services/podcast_generation_service.py", "services/episode_service.py", "services/rss_service.py", "endpoints/podcast/routes.py",
                   "endpoints/subscriber/routes.py", "endpoints/curated/routes.py"):
        assert not LONG_LIVED_MINTS.search(read(BACKEND / writer)), writer


def test_a_new_job_record_carries_no_signed_link(monkeypatch):
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from endpoints.podcast import routes as pr
    from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber
    db = FakeDB(subscribers={"s1": subscriber("tok", can_generate=True, monthly_quota=5)}, podcast_jobs={})

    class Service:
        async def run_podcast_generation_job(self, job_id, request, subscriber_id=None, **kw):
            db.collection("podcast_jobs").document(job_id).update({"status": "completed", "result": {
                "canonical_filename": "ever-x-1", "audio_url": ms.public_url("audio/ever-x-1.mp3"), "thumbnail_url": ms.public_url("thumbnails/ever-x-1-thumb.jpg")}})
    for mod in (pr, config.database):
        monkeypatch.setattr(mod, "db", db)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "k")
    monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
    monkeypatch.setattr(pr, "_get_service", lambda: Service())
    app = FastAPI(); app.include_router(pr.router)
    r = TestClient(app).post("/generate-podcast-with-subscriber?subscriber_id=s1", json={"topic": "t"}, headers={"X-Subscriber-Token": "tok"})
    assert r.status_code == 200
    job = next(iter(db.data["podcast_jobs"].values()))

    def strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)
    assert job["result"]["audio_url"].startswith("https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/")        # the eventual public form
    assert not [s for s in strings(job) if "X-Goog-" in s or "604800" in s]


# ---- 1 + 3b. the owner dashboard ---------------------------------------------------------------------------------------------------------------
def test_dashboard_hides_every_file_link_for_a_private_episode_and_keeps_them_for_a_public_one():
    html = read(ROOT / "public" / "subscriber-dashboard.html")
    # each link's own wrapper: the nearest <template ...> opening before the link is the "not private" one (the thumbnail also needs its address)
    for label, wrapper in (("🎧 Listen", 'x-if="!podcast.is_private"'), ("📝 Transcript", 'x-if="!podcast.is_private"'),
                           ("🖼️ Thumbnail", 'x-if="!podcast.is_private && podcast.result.thumbnail_url"')):
        assert html.count(label) == 1, label
        i = html.index(label)
        nearest = html[html.rfind("<template", 0, i):i]
        assert wrapper in nearest.splitlines()[0], (label, nearest[:120])
    # the stills list is empty for a private episode and is the stored list otherwise
    assert "(podcast.is_private ? [] : (podcast.result.episode_images || [])).filter(Boolean)" in html and html.count("🎬 Still") == 1
    # no file link is left outside those wrappers: every href to a result address sits after one of the four guards
    for field in ("audio_url", "transcript_url", "thumbnail_url"):
        for m in re.finditer(r'<a :href="podcast\.result\.%s"' % field, html):
            before = html[max(0, m.start() - 400):m.start()]
            assert "is_private" in before, field
    assert 'x-if="privateAccessEnabled && podcast.is_private"' in html          # Play is the owner's way to listen


def test_no_owner_facing_page_promises_posting_to_the_feed():
    texts = {p.name: read(p) for p in (ROOT / "public").glob("subscriber-*.html")}
    for name, html in texts.items():
        for phrase in ("post it to RSS", "Post to RSS", "Remove from RSS", "post to the RSS", "submit to RSS"):
            assert phrase.lower() not in html.lower(), (name, phrase)
    dash = texts["subscriber-dashboard.html"]
    assert dash.count("It stays private until you make it public.") == 2          # the two messages that used to say "post it to RSS"


# ---- 2. the admin RSS buttons -------------------------------------------------------------------------------------------------------------------
def test_admin_rss_buttons_send_the_admin_key_to_the_editors_only_route():
    html = read(ROOT / "public" / "admin-dashboard.html")
    assert "/api/admin/podcasts/${podcastId}/rss" not in html                       # the route that never existed
    for fn, flag in (("addToRss", "true"), ("removeFromRss", "false")):
        start = html.index(f"async function {fn}(")
        body = html[start:html.index("async function", start + 20)]
        assert "fetch(`${API_BASE_URL}/api/subscribers/podcasts/submit-to-rss`" in body, fn
        assert "method: 'POST'" in body and "headers: getAuthHeaders()" in body, fn
        assert f"body: JSON.stringify({{ podcast_id: podcastId, submit_to_rss: {flag} }})" in body, fn
        assert "confirm(" in body, fn                                                 # the confirmation is kept
    assert re.search(r"function getAuthHeaders\(\)\s*\{\s*return \{\s*'X-Admin-API-Key': adminApiKey,\s*'Content-Type': 'application/json'", html)


def test_the_payload_the_buttons_send_is_what_the_route_expects():
    from models.subscriber import PodcastSubmission
    assert set(PodcastSubmission.model_fields) == {"podcast_id", "submit_to_rss"}
    assert PodcastSubmission(**{"podcast_id": "ever-x-1", "submit_to_rss": True}).submit_to_rss is True
    assert PodcastSubmission(**{"podcast_id": "ever-x-1", "submit_to_rss": False}).submit_to_rss is False
