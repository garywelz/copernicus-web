"""The time shown in notification emails must be real UTC (it printed the server's local time labelled UTC)."""
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import email_service

EDT = timezone(timedelta(hours=-4))


def test_utc_text_converts_from_another_zone():
    local = datetime(2026, 10, 13, 10, 58, tzinfo=EDT)               # 10:58 in New York = 14:58 UTC
    assert email_service.utc_timestamp_text(local) == "October 13, 2026 at 02:58 PM UTC"


def test_utc_text_for_a_utc_time_and_default_is_utc():
    assert email_service.utc_timestamp_text(datetime(2026, 10, 13, 14, 58, tzinfo=timezone.utc)) == "October 13, 2026 at 02:58 PM UTC"
    now = datetime.now(timezone.utc)
    text = email_service.utc_timestamp_text()
    assert text.endswith(" UTC") and now.strftime("%B %d, %Y") in text or (now + timedelta(minutes=1)).strftime("%B %d, %Y") in text


def test_both_emails_use_the_utc_helper(monkeypatch):
    fixed = datetime(2026, 10, 13, 14, 58, tzinfo=timezone.utc)

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed.astimezone(tz) if tz else fixed.astimezone(EDT).replace(tzinfo=None)  # naive local time, as before

    monkeypatch.setattr(email_service, "datetime", FakeDT)
    sent = []

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, *a, **k): pass
        def login(self, *a): pass
        def send_message(self, msg): sent.append(msg.as_string())
        def sendmail(self, *a): sent.append(a[-1])

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("NOTIFICATION_EMAIL_PASSWORD", "x" * 16)
    svc = email_service.EmailService()
    loop = asyncio.new_event_loop()
    try:
        assert loop.run_until_complete(svc.send_podcast_failure_email("a@b.c", "job1", "topic", "boom"))
        assert loop.run_until_complete(svc.send_podcast_completion_email("a@b.c", "job1", "T", "topic", "http://x/a.mp3", "10:00", "f.mp3"))
    finally:
        loop.close()
    blob = "\n".join(sent)
    import email, quopri
    text = "".join(str(p.get_payload(decode=True), "utf-8", "ignore") for m in sent for p in email.message_from_string(m).walk() if p.get_content_type() == "text/html")
    assert text.count("02:58 PM UTC") == 2 and "10:58 AM UTC" not in text
