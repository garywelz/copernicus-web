"""Tests for the failure notices (gap 3 fix 1, C8). Offline: no mail is sent."""
import asyncio
import importlib
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

import named_work_check as nw
import paper_confirmation as pc
from failure_notice import describe_failure


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------- what each failure says
def test_each_known_failure_has_its_own_plain_message():
    cases = {
        "insufficient_confirmed_papers": pc.InsufficientConfirmedPapers("dark matter", 9, 2, 3, {"no_identifier": 5}),
        "registry_unavailable": pc.RegistryUnavailable(["arxiv"]),
        "requested_paper_not_confirmed": pc.PaperNotConfirmed("the requested paper could not be confirmed (not_found)"),
        "naming_violation": nw.NamingViolationError([{"kind": "unlisted_work", "where": "script", "quote": "x", "authors": ["Z"], "year": 2019}]),
        "naming_check_unavailable": nw.NamingCheckUnavailable("model down"),
        "generation_failed": RuntimeError("boom"),
    }
    seen = set()
    for kind, exc in cases.items():
        n = describe_failure(exc)
        assert n["kind"] == kind and n["summary"] and n["what_to_do"]
        seen.add(n["summary"])
    assert len(seen) == 6


def test_insufficient_papers_message_gives_the_numbers_and_what_to_try():
    n = describe_failure(pc.InsufficientConfirmedPapers("dark matter", 9, 2, 3, {"no_identifier": 5}))
    assert "9 possible research sources" in n["summary"] and "only 2" in n["summary"] and "at least 3" in n["summary"]
    assert "No episode was generated or published" in n["summary"] and "broader" in n["what_to_do"] and "DOI" in n["what_to_do"]


def test_requester_text_never_contains_internal_error_text():
    for exc in (RuntimeError("secret-internal: traceback at line 42 in db.py"), nw.NamingCheckUnavailable("quota: key AIza-secret"),
                nw.NamingViolationError([{"kind": "unlisted_work", "where": "script", "quote": "Zorblatt showed", "authors": ["Zorblatt"], "year": 2019}])):
        n = describe_failure(exc)
        text = n["summary"] + n["what_to_do"]
        assert "secret" not in text and "Zorblatt" not in text and "traceback" not in text


# ---------------------------------------------------------------- who is told
svc = pytest.importorskip("services.podcast_generation_service")


class FakeEmail:
    def __init__(self, fail_first=False):
        self.sent, self.fail_first = [], fail_first

    async def send_podcast_failure_email(self, recipient_email, job_id, topic, error_message, what_to_do=None):
        if self.fail_first and not self.sent:
            self.sent.append(("FAILED", recipient_email))
            raise RuntimeError("smtp down")
        self.sent.append((recipient_email, error_message, what_to_do))
        return True


def notify(exc, subscriber, admin="admin@example.org", fail_first=False):
    service = svc.PodcastGenerationService()
    service.email_service = FakeEmail(fail_first)
    old = svc.ERROR_NOTIFICATION_EMAIL
    svc.ERROR_NOTIFICATION_EMAIL = admin
    try:
        run(service._notify_failure(exc, "job1", "dark matter", subscriber))
    finally:
        svc.ERROR_NOTIFICATION_EMAIL = old
    return service.email_service.sent


def test_requester_gets_the_plain_message_and_admin_gets_the_raw_error():
    sent = notify(RuntimeError("secret-internal db error"), "user@example.org")
    assert [s[0] for s in sent] == ["user@example.org", "admin@example.org"]
    assert "secret-internal" not in sent[0][1] and "secret-internal" in sent[1][1] and "RuntimeError" in sent[1][1]
    assert sent[0][2] and sent[1][2]


def test_same_address_gets_one_email_with_the_detail():
    sent = notify(RuntimeError("secret-internal"), "Admin@Example.org")
    assert len(sent) == 1 and "secret-internal" in sent[0][1]


def test_no_subscriber_address_means_only_the_administrator():
    sent = notify(pc.RegistryUnavailable(["pubmed"]), None)
    assert [s[0] for s in sent] == ["admin@example.org"]


def test_a_failing_send_does_not_block_the_other_or_raise():
    sent = notify(RuntimeError("x"), "user@example.org", fail_first=True)
    assert sent[0][0] == "FAILED" and sent[1][0] == "admin@example.org"


def test_known_failure_reaches_the_requester_with_numbers():
    sent = notify(pc.InsufficientConfirmedPapers("dark matter", 9, 2, 3, {"no_identifier": 5}), "user@example.org")
    assert "only 2" in sent[0][1] and "Not enough confirmed research papers" in sent[1][1]


# ---------------------------------------------------------------- the email itself and the recipient setting
def test_failure_email_body_uses_the_specific_advice(monkeypatch):
    import email_service as es
    captured = {}

    class FakeSMTP:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self, **k):
            pass

        def login(self, *a):
            pass

        def send_message(self, msg):
            captured["body"] = msg.get_payload()[0].get_payload(decode=True).decode("utf-8")
            captured["to"] = msg["To"]
    monkeypatch.setenv("NOTIFICATION_EMAIL_PASSWORD", "x")
    monkeypatch.setattr(es.smtplib, "SMTP", FakeSMTP)
    ok = run(es.EmailService().send_podcast_failure_email("u@example.org", "job1", "dark matter", "summary text", what_to_do="Try a broader topic."))
    assert ok and captured["to"] == "u@example.org" and "Try a broader topic." in captured["body"] and "summary text" in captured["body"]
    ok = run(es.EmailService().send_podcast_failure_email("u@example.org", "job1", "t", "e"))
    assert "Please try generating the podcast again" in captured["body"]


def test_error_recipient_is_not_chained_to_the_sender_address(monkeypatch):
    import config.constants as c
    monkeypatch.delenv("ERROR_NOTIFICATION_EMAIL", raising=False)
    monkeypatch.setenv("NOTIFICATION_EMAIL", "sender@example.org")
    importlib.reload(c)
    try:
        assert c.ERROR_NOTIFICATION_EMAIL != "sender@example.org"
        monkeypatch.setenv("ERROR_NOTIFICATION_EMAIL", "me@example.org")
        importlib.reload(c)
        assert c.ERROR_NOTIFICATION_EMAIL == "me@example.org"
    finally:
        monkeypatch.undo()
        importlib.reload(c)
