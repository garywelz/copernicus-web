"""Single-use, expiring emailed credential tokens, and the password-reset routes built on them.

Covers: token issue (only a hash is stored), single use, expiry, one outstanding token per account, identical refusals,
identical answers for known and unknown addresses, rate limits (per address and per client address, failing closed), and
that no address and no token reaches a log line or stdout.

The Firestore transaction itself is not simulated: the fake applies each step immediately, so "two simultaneous
redemptions" is covered by Firestore's transaction guarantee, not by these tests.
"""
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from google.cloud import firestore

with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.subscriber import routes
    from endpoints.subscriber.routes import router

from utils import credential_tokens, rate_limit, subscriber_helpers
from utils.credential_tokens import hash_token, issue_token, redeem_password_token
from utils.subscriber_helpers import generate_subscriber_id, hash_password, verify_password
import email_service as email_module

app = FastAPI()
app.include_router(router)
client = TestClient(app)

EMAIL = "reset.person@example.invalid"
OTHER_EMAIL = "other.person@example.invalid"
OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "brand-new-password-9"
IP = "203.0.113.7"
NOW = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


# --- fakes ----------------------------------------------------------------------------------------------------

class _Snap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class FakeDB:
    """Named in-memory collections. Transactions apply their writes immediately."""

    def __init__(self):
        self.cols = {}

    def collection(self, name):
        db = self
        db.cols.setdefault(name, {})

        class Col:
            def document(self_c, doc_id):
                return Ref(db, name, doc_id)
        return Col()

    def transaction(self):
        return object()

    # helpers
    def doc(self, col, doc_id):
        return self.cols.get(col, {}).get(doc_id)


class Ref:
    def __init__(self, db, col, doc_id):
        self.db, self.col, self.doc_id = db, col, doc_id

    def get(self, transaction=None):
        return _Snap(self.doc_id, self.db.cols.get(self.col, {}).get(self.doc_id))

    def _apply_update(self, data):
        doc = self.db.cols[self.col][self.doc_id]
        for k, v in data.items():
            if v is firestore.DELETE_FIELD:
                doc.pop(k, None)
            else:
                doc[k] = v

    def set(self, data, **kw):
        self.db.cols.setdefault(self.col, {})[self.doc_id] = dict(data)

    def update(self, data):
        self._apply_update(data)


class FakeTxn:
    def set(self, ref, data):
        ref.set(data)

    def update(self, ref, data):
        ref.update(data)

    def delete(self, ref):
        ref.db.cols.get(ref.col, {}).pop(ref.doc_id, None)


def _fake_run(db, fn, *args):
    return fn(FakeTxn(), *args)


@pytest.fixture(autouse=True)
def _fake_transactions():
    with patch.object(credential_tokens, '_run_in_transaction', _fake_run):
        yield


class Logs:
    """Records every structured_logger call and everything printed, so a test can search them."""

    def __init__(self):
        self.mock = MagicMock()

    def text(self):
        return repr(self.mock.mock_calls)


@pytest.fixture
def logs():
    lg = Logs()
    with patch.object(routes, 'structured_logger', lg.mock), \
         patch.object(credential_tokens, 'structured_logger', lg.mock), \
         patch.object(subscriber_helpers, 'structured_logger', lg.mock):
        yield lg


class FakeMailer:
    def __init__(self):
        self.sent = []

    async def send_credential_link_email(self, recipient_email, link, valid_minutes):
        self.sent.append({'to': recipient_email, 'link': link, 'minutes': valid_minutes})
        return True


class FakeLimiter:
    """The check_rate_limit contract: raises 429 past `limit` per (route, key); records every call."""

    def __init__(self, fail_with=None):
        self.counts = {}
        self.calls = []
        self.fail_with = fail_with

    def __call__(self, db, client_key, route, limit, window_seconds, fail_closed=False):
        self.calls.append({'key': client_key, 'route': route, 'limit': limit, 'fail_closed': fail_closed})
        if self.fail_with:
            raise self.fail_with
        k = (route, client_key)
        self.counts[k] = self.counts.get(k, 0) + 1
        if self.counts[k] > limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _db(emails=(EMAIL,)):
    fake = FakeDB()
    fake.collection('subscribers')
    for e in emails:
        sid = generate_subscriber_id(e)
        fake.cols['subscribers'][sid] = {
            'subscriber_id': sid, 'email': e, 'name': 'Person', 'subscription_tier': 'free',
            'password_hash': hash_password(OLD_PASSWORD), 'can_generate': True,
            'session_token_hash': 'old-session-hash', 'session_token_expires': '2999-01-01T00:00:00',
        }
    return fake


class Env:
    def __init__(self, fake, limiter=None):
        self.db = fake
        self.mailer = FakeMailer()
        self.limiter = limiter or FakeLimiter()

    def __enter__(self):
        self._patches = [
            patch.object(routes, 'db', self.db), patch.object(subscriber_helpers, 'db', self.db),
            patch.object(routes, 'email_service', self.mailer), patch.object(routes, 'check_rate_limit', self.limiter),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *a):
        for p in self._patches:
            p.stop()

    def request(self, email, ip=IP):
        return client.post("/api/subscribers/password-reset-request", json={"email": email}, headers={"x-forwarded-for": ip})

    def redeem(self, token, password=NEW_PASSWORD, ip=IP, **extra):
        return client.post("/api/subscribers/password-reset", json={"token": token, "new_password": password, **extra},
                           headers={"x-forwarded-for": ip})

    def token_from_mail(self, index=-1):
        link = self.mailer.sent[index]['link']
        assert '#token=' in link
        return link.split('#token=', 1)[1]


def _sid(email=EMAIL):
    return generate_subscriber_id(email)


# --- issuing a token ----------------------------------------------------------------------------------------------

def test_issue_stores_only_a_hash_with_an_expiry_and_returns_the_raw_token_once():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    stored = fake.doc('credential_tokens', hash_token(raw))
    assert stored['subscriber_id'] == _sid()
    assert stored['used_at'] is None
    assert datetime.fromisoformat(stored['expires_at']) == NOW + timedelta(minutes=30)
    assert raw not in repr(fake.cols)                       # the raw token is stored nowhere
    assert fake.doc('credential_token_index', _sid()) == {'token_hash': hash_token(raw)}
    assert len(raw) >= 43                                    # 32 random bytes, url-safe encoded


def test_the_token_lifetime_is_thirty_minutes():
    assert credential_tokens.PURPOSE_TTL_MINUTES['password_reset'] == 30


def test_tokens_are_unique_per_issue():
    fake = _db()
    assert len({issue_token(fake, _sid(), now=NOW) for _ in range(50)}) == 50


def test_a_new_token_ends_the_previous_one_for_that_account():
    fake = _db()
    first = issue_token(fake, _sid(), now=NOW)
    second = issue_token(fake, _sid(), now=NOW)
    assert fake.doc('credential_tokens', hash_token(first)) is None
    assert redeem_password_token(fake, first, 'h1', now=NOW) is None
    assert redeem_password_token(fake, second, 'h2', now=NOW) == _sid()


# --- using a token: single use, expiry, refusal --------------------------------------------------------------------

def test_a_token_sets_the_password_once_and_never_again():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    assert redeem_password_token(fake, raw, 'scrypt$first', now=NOW + timedelta(minutes=1)) == _sid()
    assert fake.doc('subscribers', _sid())['password_hash'] == 'scrypt$first'
    assert redeem_password_token(fake, raw, 'scrypt$second', now=NOW + timedelta(minutes=2)) is None
    assert fake.doc('subscribers', _sid())['password_hash'] == 'scrypt$first'      # the second use changed nothing
    assert fake.doc('credential_tokens', hash_token(raw))['used_at'] is not None
    assert fake.doc('credential_token_index', _sid()) is None                       # nothing outstanding remains


def test_an_expired_token_is_refused_and_changes_nothing():
    fake = _db()
    before = dict(fake.doc('subscribers', _sid()))
    raw = issue_token(fake, _sid(), now=NOW)
    assert redeem_password_token(fake, raw, 'scrypt$late', now=NOW + timedelta(minutes=30, seconds=1)) is None
    assert fake.doc('subscribers', _sid()) == before
    assert fake.doc('credential_tokens', hash_token(raw))['used_at'] is None


def test_a_token_is_still_good_just_inside_its_lifetime():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    assert redeem_password_token(fake, raw, 'scrypt$ok', now=NOW + timedelta(minutes=29, seconds=59)) == _sid()


@pytest.mark.parametrize("bad", ["", "not-a-token", "x" * 5000, None, 12345, "a" * 43])
def test_unknown_or_malformed_tokens_are_refused(bad):
    fake = _db()
    before = dict(fake.doc('subscribers', _sid()))
    assert redeem_password_token(fake, bad, 'scrypt$x', now=NOW) is None
    assert fake.doc('subscribers', _sid()) == before


def test_a_token_for_another_purpose_is_refused():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    fake.cols['credential_tokens'][hash_token(raw)]['purpose'] = 'something_else'
    assert redeem_password_token(fake, raw, 'scrypt$x', now=NOW) is None


def test_a_token_whose_account_no_longer_exists_is_refused():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    del fake.cols['subscribers'][_sid()]
    assert redeem_password_token(fake, raw, 'scrypt$x', now=NOW) is None


def test_redeeming_ends_the_accounts_existing_sessions():
    fake = _db()
    raw = issue_token(fake, _sid(), now=NOW)
    redeem_password_token(fake, raw, 'scrypt$new', now=NOW)
    doc = fake.doc('subscribers', _sid())
    assert 'session_token_hash' not in doc and 'session_token_expires' not in doc


# --- the routes: request ------------------------------------------------------------------------------------------

def test_request_for_a_known_address_emails_one_link_to_that_address():
    with Env(_db()) as env:
        r = env.request(EMAIL)
    assert r.status_code == 200
    assert len(env.mailer.sent) == 1
    mail = env.mailer.sent[0]
    assert mail['to'] == EMAIL and mail['minutes'] == 30
    assert mail['link'].startswith("https://www.copernicusai.fyi/subscriber-reset-password.html#token=")
    assert '?' not in mail['link']                 # the token is in the fragment, never in a query string a server logs


def test_the_answer_is_identical_for_a_known_and_an_unknown_address():
    with Env(_db()) as env:
        known = env.request(EMAIL)
        unknown = env.request("nobody@example.invalid")
        malformed = env.request("not an address at all")
    assert known.status_code == unknown.status_code == malformed.status_code == 200
    assert known.json() == unknown.json() == malformed.json()
    assert dict(known.headers).keys() == dict(unknown.headers).keys()
    assert len(env.mailer.sent) == 1                # only the real account got a mail


def test_request_finds_the_account_when_the_address_is_typed_in_another_case():
    with Env(_db()) as env:
        r = env.request("  Reset.Person@Example.invalid ")
    assert r.status_code == 200
    assert len(env.mailer.sent) == 1 and env.mailer.sent[0]['to'] == EMAIL    # sent to the address on the account


def test_a_sender_failure_looks_the_same_to_the_caller():
    with Env(_db()) as env:
        async def boom(*a, **k):
            raise RuntimeError("smtp down")
        env.mailer.send_credential_link_email = boom
        r = env.request(EMAIL)
        ok = env.request("nobody@example.invalid")
    assert r.status_code == 200 and r.json() == ok.json()


def test_request_is_limited_per_address_and_the_extra_requests_look_normal():
    with Env(_db()) as env:
        answers = [env.request(EMAIL, ip=f"198.51.100.{i}") for i in range(6)]   # six different clients, one address
    assert {a.status_code for a in answers} == {200}
    assert len({a.text for a in answers}) == 1
    assert len(env.mailer.sent) == routes.RESET_REQUEST_LIMIT_PER_ADDRESS_PER_HOUR == 3


def test_request_is_limited_per_client_address_with_429():
    with Env(_db()) as env:
        codes = [env.request(f"user{i}@example.invalid").status_code for i in range(12)]
    assert codes[:10] == [200] * 10 and codes[10:] == [429, 429]


def test_the_limits_fail_closed():
    with Env(_db()) as env:
        env.request(EMAIL)
    assert env.limiter.calls and all(c['fail_closed'] for c in env.limiter.calls)
    routes_seen = {c['route'] for c in env.limiter.calls}
    assert routes_seen == {'password_reset_request', 'password_reset_request_address'}


def test_redeem_limit_is_ten_an_hour_and_fails_closed():
    with Env(_db()) as env:
        env.redeem("E" * 43)
    call = [c for c in env.limiter.calls if c['route'] == 'password_reset_redeem']
    assert len(call) == 1 and call[0]['fail_closed'] is True and call[0]['limit'] == 10


def test_when_the_limiter_cannot_run_the_request_is_refused_not_waved_through():
    with Env(_db(), limiter=FakeLimiter(fail_with=HTTPException(status_code=503, detail="down"))) as env:
        r = env.request(EMAIL)
        r2 = env.redeem("whatever-token")
    assert r.status_code == 503 and r2.status_code == 503
    assert env.mailer.sent == []


def test_the_real_limiter_fails_closed_when_asked_and_open_otherwise():
    bad = MagicMock()
    bad.collection.side_effect = RuntimeError("firestore down")
    with pytest.raises(HTTPException) as e:
        rate_limit.check_rate_limit(bad, "k", "r", limit=1, window_seconds=60, fail_closed=True)
    assert e.value.status_code == 503
    with pytest.raises(HTTPException):
        rate_limit.check_rate_limit(None, "k", "r", limit=1, window_seconds=60, fail_closed=True)
    rate_limit.check_rate_limit(bad, "k", "r", limit=1, window_seconds=60)            # default: fails open
    rate_limit.check_rate_limit(None, "k", "r", limit=1, window_seconds=60)


# --- the routes: redeem -------------------------------------------------------------------------------------------

def test_the_whole_flow_reset_by_email_then_log_in_with_the_new_password():
    with Env(_db()) as env:
        env.request(EMAIL)
        token = env.token_from_mail()
        r = env.redeem(token)
        assert r.status_code == 200
        stored = env.db.doc('subscribers', _sid())['password_hash']
        assert verify_password(NEW_PASSWORD, stored)[0] and not verify_password(OLD_PASSWORD, stored)[0]
        with patch.object(routes, 'check_rate_limit', return_value=None):
            ok = client.post("/api/subscribers/login", json={"email": EMAIL, "password": NEW_PASSWORD})
            old = client.post("/api/subscribers/login", json={"email": EMAIL, "password": OLD_PASSWORD})
    assert ok.status_code == 200 and old.status_code == 401


def test_a_used_token_gets_the_same_refusal_as_an_unknown_one():
    with Env(_db()) as env:
        env.request(EMAIL)
        token = env.token_from_mail()
        assert env.redeem(token).status_code == 200
        used = env.redeem(token, password="another-password-1")
        unknown = env.redeem("A" * 43, password="another-password-1")
    assert used.status_code == unknown.status_code == 400
    assert used.json() == unknown.json()


def test_an_expired_token_gets_the_same_refusal_too():
    with Env(_db()) as env:
        raw = issue_token(env.db, _sid(), now=datetime.now(timezone.utc) - timedelta(hours=1))
        expired = env.redeem(raw)
        unknown = env.redeem("B" * 43)
    assert expired.status_code == unknown.status_code == 400 and expired.json() == unknown.json()


def test_the_old_password_still_works_after_a_refused_attempt():
    with Env(_db()) as env:
        before = env.db.doc('subscribers', _sid())['password_hash']
        for t in ("C" * 43, "", "x" * 5000):
            assert env.redeem(t).status_code in (400, 422)
        assert env.db.doc('subscribers', _sid())['password_hash'] == before


def test_the_request_names_no_account_the_token_alone_decides_whose_password_changes():
    with Env(_db(emails=(EMAIL, OTHER_EMAIL))) as env:
        env.request(EMAIL)
        token = env.token_from_mail()
        other_before = env.db.doc('subscribers', _sid(OTHER_EMAIL))['password_hash']
        r = env.redeem(token, email=OTHER_EMAIL, subscriber_id=_sid(OTHER_EMAIL))     # extra fields are ignored
        assert r.status_code == 200
        assert env.db.doc('subscribers', _sid(OTHER_EMAIL))['password_hash'] == other_before
        assert verify_password(NEW_PASSWORD, env.db.doc('subscribers', _sid())['password_hash'])[0]


def test_a_request_without_a_token_is_refused_and_changes_nothing():
    with Env(_db()) as env:
        before = dict(env.db.doc('subscribers', _sid()))
        r = client.post("/api/subscribers/password-reset", json={"email": EMAIL, "new_password": "other-password-1"},
                        headers={"x-forwarded-for": IP})
        assert r.status_code == 422
        assert env.db.doc('subscribers', _sid()) == before


@pytest.mark.parametrize("pw", ["short", "x" * 129, ""])
def test_a_bad_password_is_refused_and_the_token_is_not_spent(pw):
    with Env(_db()) as env:
        env.request(EMAIL)
        token = env.token_from_mail()
        assert env.redeem(token, password=pw).status_code == 400
        assert env.redeem(token).status_code == 200            # the same token still works with a good password


def test_redeem_is_limited_per_client_address():
    with Env(_db()) as env:
        codes = [env.redeem(f"{chr(65 + i)}" * 43).status_code for i in range(12)]
    assert codes[:10] == [400] * 10 and codes[10:] == [429, 429]


def test_redeem_with_no_database_is_503():
    with patch.object(routes, 'db', None), patch.object(routes, 'check_rate_limit', FakeLimiter()):
        r = client.post("/api/subscribers/password-reset", json={"token": "T" * 43, "new_password": NEW_PASSWORD})
    assert r.status_code == 503


# --- nothing sensitive in any log -------------------------------------------------------------------------------------

def test_no_address_and_no_token_in_any_log_line_or_output(logs, capsys):
    with Env(_db()) as env:
        env.request(EMAIL)
        env.request("nobody@example.invalid")
        token = env.token_from_mail()
        env.redeem(token)
        env.redeem(token)                                    # a refused attempt
        env.redeem("D" * 43)
    out = capsys.readouterr()
    haystack = logs.text() + out.out + out.err
    for secret in (EMAIL, "nobody@example.invalid", EMAIL.split('@')[0], token, hash_token(token), "D" * 43):
        assert secret not in haystack, secret
    assert logs.mock.mock_calls                                # something was logged, and it was searched


def test_a_failure_while_sending_logs_only_the_error_type(logs, capsys):
    with Env(_db()) as env:
        async def boom(*a, **k):
            raise RuntimeError("smtp refused " + EMAIL)
        env.mailer.send_credential_link_email = boom
        env.request(EMAIL)
    assert EMAIL not in logs.text() + capsys.readouterr().out


# --- the email itself -----------------------------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine on a private loop. asyncio.run() would leave the thread with no current event loop and break
    later tests that call get_event_loop()."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _service(password="app-password-not-real"):
    with patch.dict('os.environ', {'NOTIFICATION_EMAIL': 'site@example.invalid', 'NOTIFICATION_EMAIL_PASSWORD': password}):
        return email_module.EmailService()


def test_the_email_is_plain_signed_by_the_site_and_carries_the_link_once_per_part(capsys):
    svc = _service()
    sent = []
    svc._send_message_blocking = lambda msg: sent.append(msg)
    link = "https://www.copernicusai.fyi/subscriber-reset-password.html#token=TESTTOKEN"
    assert _run(svc.send_credential_link_email(EMAIL, link, 30)) is True
    msg = sent[0]
    assert msg['To'] == EMAIL and msg['Subject'] == "Reset your CopernicusAI password"
    assert 'CopernicusAI' in msg['From'] and 'site@example.invalid' in msg['From']
    parts = [p.get_payload(decode=True).decode() for p in msg.get_payload()]
    assert len(parts) == 2 and all(link in p for p in parts)
    assert "30 minutes" in parts[0] and parts[0].rstrip().endswith("CopernicusAI")
    assert "ignore this email" in parts[0]
    out = capsys.readouterr()
    assert EMAIL not in out.out + out.err and "TESTTOKEN" not in out.out + out.err


def test_the_email_is_not_sent_when_no_sender_password_is_configured(capsys):
    svc = _service(password="")
    svc.sender_password = None
    called = []
    svc._send_message_blocking = lambda msg: called.append(msg)
    assert _run(svc.send_credential_link_email(EMAIL, "https://example.invalid/#token=T", 30)) is False
    assert called == []
    out = capsys.readouterr()
    assert EMAIL not in out.out + out.err


def test_a_smtp_failure_returns_false_and_prints_no_address(capsys):
    svc = _service()

    def fail(msg):
        raise OSError("connection refused for " + EMAIL)
    svc._send_message_blocking = fail
    assert _run(svc.send_credential_link_email(EMAIL, "https://example.invalid/#token=T", 30)) is False
    out = capsys.readouterr()
    assert EMAIL not in out.out + out.err
