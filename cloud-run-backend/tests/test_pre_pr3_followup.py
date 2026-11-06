"""Pre-PR 3 follow-up (from the PR 2 smoke test, 2026-11-05): the invitation email names the engine and the inviter, and the dashboard no longer depends on a
Firestore composite index. Offline: SMTP and the clock are replaced; the fake Firestore REFUSES order_by on `episodes`, as Firestore did while the index
was missing."""
import asyncio
import inspect
import re
from datetime import datetime, timezone
from email import message_from_string
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import email_service as email_module
from tests.fakes_pr1 import FakeDB, passthrough_transactional, subscriber

LINK = "https://www.copernicusai.fyi/onboarding/accept.html#token=TOKENVALUE123"


# ---- change 1: the invitation email ----------------------------------------------------------------------------------------------------------------
def send(label="TDAP smoke test", link=LINK, days=7):
    """Run the real builder with SMTP replaced; return (subject, plain body, html body, headers as text)."""
    with patch.dict("os.environ", {"NOTIFICATION_EMAIL": "site@example.invalid", "NOTIFICATION_EMAIL_PASSWORD": "not-a-real-secret"}):
        svc = email_module.EmailService()
    sent = []
    loop = asyncio.new_event_loop()                          # a private loop: asyncio.run() would close the global one other tests rely on
    try:
        with patch.object(email_module.smtplib, "SMTP") as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = lambda m: sent.append(m)
            assert loop.run_until_complete(svc.send_invitation_email("someone@example.invalid", link, days, label)) is True
    finally:
        loop.close()
    msg = sent[0]
    parts = {p.get_content_type(): p.get_payload(decode=True).decode("utf-8") for p in msg.get_payload()}
    return msg["Subject"], parts["text/plain"], parts["text/html"], msg


def test_the_subject_and_body_name_the_engine_and_the_inviter():
    subject, text, html, msg = send()
    assert subject == "Gary Welz invited you to the TDAP smoke test engine on CopernicusAI"
    assert "Gary Welz has invited you to the TDAP smoke test knowledge engine on CopernicusAI (www.copernicusai.fyi)." in text
    assert "To accept, open this link. It works once and expires in 7 days:" in text
    assert "If you weren't expecting this invitation, ignore this email; nothing will happen." in text
    assert text.rstrip().endswith("CopernicusAI")                                    # signed by the site
    assert "Gary Welz has invited you to the TDAP smoke test knowledge engine on CopernicusAI (www.copernicusai.fyi)." in html
    assert "expires in 7 days" in html and "weren't expecting this invitation" in html
    assert msg["From"].startswith("CopernicusAI")                                      # still the site's existing sender


def test_the_link_carries_the_token_in_the_fragment_only_and_no_address_appears_in_it():
    subject, text, html, msg = send()
    links = re.findall(r"https?://\S+", text)
    assert links == [LINK] and "?" not in links[0] and links[0].count("#token=") == 1 and "@" not in links[0]
    assert LINK in html and "@" not in re.findall(r'href="([^"]+)"', html)[0]
    assert "someone@example.invalid" not in text and "someone@example.invalid" not in html         # the address is only in the To header
    assert "someone@example.invalid" not in subject


def test_the_inviter_is_a_constant_not_text_in_the_template():
    assert email_module.INVITER_NAME == "Gary Welz"
    source = inspect.getsource(email_module.EmailService.send_invitation_email)
    assert "Gary Welz" not in source and "INVITER_NAME" in source
    with patch.object(email_module, "INVITER_NAME", "Test Person"):                       # change the one constant: subject and both bodies follow
        subject, text, html, _ = send()
    assert subject.startswith("Test Person invited you to the") and "Test Person has invited you" in text and "Test Person has invited you" in html
    assert "Gary Welz" not in subject + text + html


def test_the_label_is_cleaned_for_a_mail_header_escaped_in_html_and_cut_to_length():
    subject, text, html, msg = send(label="Evil\r\nBcc: someone@example.invalid\nX-Injected: yes")
    assert "\n" not in subject and "\r" not in subject and msg["Bcc"] is None and msg["X-Injected"] is None        # no header can be injected through the label
    assert "Bcc" in subject                                                                 # the text stays (as text), harmlessly, on one line
    subject2, text2, html2, _ = send(label="A <b>bold</b> & co")
    assert "A <b>bold</b> & co" in text2 and "A &lt;b&gt;bold&lt;/b&gt; &amp; co" in html2 and "<b>bold</b>" not in html2
    long_label = "x" * 200
    subject3, text3, _, _ = send(label=long_label)
    assert ("x" * 80) in text3 and ("x" * 81) not in text3
    assert email_module.clean_header_text("  a \t\t b \x00 c  ") == "a b c"


@pytest.mark.parametrize("label", [None, "", "   ", "\r\n"])
def test_an_empty_label_falls_back_to_the_site_name(label):
    subject, text, html, _ = send(label=label)
    assert subject == "Gary Welz invited you to the CopernicusAI engine on CopernicusAI" and "knowledge engine on CopernicusAI" in text


def test_the_route_passes_the_engine_label_and_falls_back_to_the_engine_id(monkeypatch):
    import config.database
    import utils.auth as auth
    from endpoints.onboarding import routes
    from tests.fakes_pr2 import FakeDB as AtomicDB, run_in_transaction
    from utils import onboarding as ob
    db = AtomicDB(onboarding_engines={"with-label": {"label": "  Fancy Engine  ", "state": "open", "final_say_subscriber_id": None},
                                      "no-label": {"state": "open", "final_say_subscriber_id": None},
                                      "blank-label": {"label": "   ", "state": "open", "final_say_subscriber_id": None}})
    seen = []

    class Mail:
        async def send_invitation_email(self, address, link, days, engine_label=None):
            seen.append(engine_label)
            return True
    monkeypatch.setattr(ob, "_run_in_transaction", run_in_transaction)
    monkeypatch.setattr(routes, "db", db)
    monkeypatch.setattr(config.database, "db", db)
    monkeypatch.setattr(routes, "email_service", Mail())
    monkeypatch.setattr(routes, "check_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
    app = FastAPI()
    app.include_router(routes.router)
    c = TestClient(app)
    for engine in ("with-label", "no-label", "blank-label"):
        r = c.post("/api/admin/onboarding/invites", json={"engine_id": engine, "email": f"{engine}@example.invalid"}, headers={"X-Admin-API-Key": "test-key"})
        assert r.status_code == 200 and set(r.json()) == {"invite_id", "engine_id", "expires_at", "email_sent"}, r.text      # the response is unchanged: no label, token or address
    assert seen == ["Fancy Engine", "no-label", "blank-label"]                       # the record's label (trimmed), else the engine id


# ---- change 2: the dashboard without the index ----------------------------------------------------------------------------------------------------
A, TOK = "sub-a", "token-a"
H = {"X-Subscriber-Token": TOK}


class NoIndexDB(FakeDB):
    """Refuses order_by on `episodes` (query and where-query alike), as Firestore did while the composite index was missing."""

    def collection(self, name):
        col = super().collection(name)
        if name == "episodes":
            def refuse(*a, **k):
                raise RuntimeError("400 The query requires an index. You can create it here: https://console.firebase.google.com/...")
            orig_where = col.where
            col.order_by = refuse

            def where(*a, **k):
                q = orig_where(*a, **k)
                q.order_by = refuse
                return q
            col.where = where
        return col


class BrokenEpisodesDB(FakeDB):
    """Any read of `episodes` fails with an unrelated error that carries identifying detail."""

    def collection(self, name):
        col = super().collection(name)
        if name == "episodes":
            def boom(*a, **k):
                raise RuntimeError("boom with secret detail for sub-a")
            orig_where = col.where

            def where(*a, **k):
                q = orig_where(*a, **k)
                q.stream = boom
                return q
            col.where = where
        return col


def ep(owner, created=None, **extra):
    d = {"title": "T", "subscriber_id": owner, "submitted_to_rss": False, "visible_on_web": False}
    if created is not None:
        d["created_at"] = created
    d.update(extra)
    return d


@pytest.fixture
def dash(monkeypatch):
    import config.database
    import utils.auth as auth
    import utils.generation_quota as gq
    from endpoints.subscriber import routes as sub_routes
    holder = {}

    def build(db_class, episodes, jobs=None):
        db = db_class(subscribers={A: subscriber(TOK, email="a@example.invalid")}, episodes=episodes, podcast_jobs=jobs or {})
        for mod in (sub_routes, config.database):
            monkeypatch.setattr(mod, "db", db)
        monkeypatch.setattr(auth, "get_admin_api_key", lambda: "test-key")
        monkeypatch.setattr(gq.firestore, "transactional", passthrough_transactional)
        app = FastAPI()
        app.include_router(sub_routes.router)
        holder["client"], holder["db"], holder["routes"] = TestClient(app), db, sub_routes
        return holder["client"]
    return build


def rows(client):
    r = client.get(f"/api/subscribers/podcasts/{A}", headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def test_episodes_still_load_and_carry_private_and_public_when_order_by_is_refused(dash):
    client = dash(NoIndexDB, {
        "ever-x-1": ep(A, "2026-11-01T10:00:00"),                                       # private
        "ever-x-2": ep(A, "2026-11-02T10:00:00", visible_on_web=True),                   # on the site
        "ever-x-3": ep(A, "2026-11-03T10:00:00", submitted_to_rss=True),                 # in the feed
    }, jobs={"job-1": {"subscriber_id": A, "status": "completed", "created_at": "2026-11-01T09:00:00", "result": {"canonical_filename": "ever-x-1", "title": "T"}}})
    body = rows(client)
    by = {p["canonical_filename"]: p for p in body["podcasts"]}
    assert set(by) == {"ever-x-1", "ever-x-2", "ever-x-3"}
    assert (by["ever-x-1"]["is_private"], by["ever-x-1"]["is_public"]) == (True, False)
    assert (by["ever-x-2"]["is_private"], by["ever-x-2"]["is_public"]) == (False, True)
    assert (by["ever-x-3"]["is_private"], by["ever-x-3"]["is_public"]) == (False, True)
    assert by["ever-x-1"]["visible_on_web"] is False and by["ever-x-2"]["visible_on_web"] is True
    assert by["ever-x-1"]["source"] == "podcast_jobs"                                    # the job row merged with its episode record
    assert "private_access_enabled" in body


def test_episodes_are_sorted_newest_first_in_code_across_string_datetime_and_missing_timestamps(dash):
    from endpoints.subscriber.routes import _episode_sort_key
    class Doc:
        def __init__(self, id_, data):
            self.id, self._d = id_, data
        def to_dict(self):
            return self._d
    docs = [Doc("a", {"created_at": "2026-11-05T09:00:00"}),
            Doc("b", {"created_at": datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)}),        # later the same day, as a datetime
            Doc("c", {"created_at": "2026-11-05T20:00:00Z"}),                                       # a Z suffix
            Doc("d", {"generated_at": "2026-11-04T08:00:00"}),                                      # only generated_at
            Doc("e", {}),                                                                           # no timestamp at all
            Doc("f", {"created_at": "2026-11-05T09:00:00"}),                                        # same time as a: ties by id
            Doc("g", {"created_at": "2026-11-05T07:00:00Z"}),                                       # the SAME instant three ways: a Z suffix,
            Doc("h", {"created_at": "2026-11-05T07:00:00"}),                                        # no suffix,
            Doc("i", {"created_at": datetime(2026, 11, 5, 7, 0, 0, tzinfo=timezone.utc)})]          # and a timezone-aware datetime: a tie, broken by id, not by the suffix
    assert [d.id for d in sorted(docs, key=_episode_sort_key, reverse=True)] == ["c", "b", "f", "a", "i", "h", "g", "d", "e"]
    # and through the route, with the query unable to order
    client = dash(NoIndexDB, {"ever-old": ep(A, "2026-11-01T10:00:00"), "ever-new": ep(A, "2026-11-05T10:00:00"), "ever-mid": ep(A, "2026-11-03T10:00:00")})
    assert [p["canonical_filename"] for p in rows(client)["podcasts"]] == ["ever-new", "ever-mid", "ever-old"]


def test_an_episode_with_no_timestamp_is_listed_last_instead_of_being_dropped(dash):
    client = dash(NoIndexDB, {"ever-dated": ep(A, "2026-11-05T10:00:00"), "ever-undated": ep(A)})
    ids = [p["canonical_filename"] for p in rows(client)["podcasts"]]
    assert ids == ["ever-dated", "ever-undated"]                                         # order_by used to leave an undated episode out


def test_no_order_by_is_used_on_the_episodes_query():
    from endpoints.subscriber import routes
    src = inspect.getsource(routes.get_subscriber_podcasts)
    start = src.index("episodes_query = sorted(")
    assert ".order_by(" not in src[start:src.index("for episode_doc in episodes_query:")]
    assert "key=_episode_sort_key, reverse=True" in src


def test_a_failing_episodes_read_falls_back_to_the_jobs_and_warns_with_the_error_type_only(dash):
    client = dash(BrokenEpisodesDB, {"ever-x-1": ep(A, "2026-11-01T10:00:00")},
                  jobs={"job-1": {"subscriber_id": A, "status": "completed", "created_at": "2026-11-01T09:00:00", "result": {"canonical_filename": "ever-x-1", "title": "T"}}})
    log = MagicMock()
    with patch("endpoints.subscriber.routes.structured_logger", log):
        body = rows(client)
    assert [p["canonical_filename"] for p in body["podcasts"]] == ["ever-x-1"]           # the jobs fallback still lists it
    assert body["podcasts"][0]["is_private"] is False and "visible_on_web" not in body["podcasts"][0]        # without the episode record there is no marking: the old failure mode, now only on a real error
    warnings = [c for c in log.warning.call_args_list if c.args and c.args[0] == "Could not load podcasts from episodes"]
    assert len(warnings) == 1
    kwargs = warnings[0].kwargs
    assert kwargs.get("error_type") == "RuntimeError" and "error" not in kwargs
    assert "boom" not in str(kwargs) and "secret" not in str(kwargs)                       # the error's text, which may carry detail, is not logged
