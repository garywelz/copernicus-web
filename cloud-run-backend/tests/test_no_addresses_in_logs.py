"""No email address reaches a log line, stdout or an error message from the subscriber routes or the code behind them.

Three layers: (1) a source check that no log, print or HTTPException call names an address; (2) a run of the subscriber routes,
success and failure paths, with every logger entry and all stdout searched for email-shaped text, including addresses carried
inside exception text; (3) the logger's own backstop, which replaces email-shaped text in any value before it is written.
"""
import ast
import asyncio
import io
import json
import logging
import os
import re
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

with patch('config.database.db', MagicMock()):
    from endpoints.subscriber import routes
    from endpoints.subscriber.routes import router

import email_service as email_module
from utils import credential_tokens, subscriber_helpers
from utils import logging as app_logging
from utils.logging import structured_logger, redact_addresses, ADDRESS_PLACEHOLDER
from utils.subscriber_helpers import generate_subscriber_id, hash_password

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL_SHAPED = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)

EMAIL = "log.check.person@example.invalid"
PASSWORD = "password-for-log-test-1"


# --- 1. source check ---------------------------------------------------------------------------------------------

ADDRESS_NAMES = re.compile(r"^(email|mailto|address|recipient\w*|\w+_email|\w+_address)$", re.I)
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
# Run by hand from a terminal, not by the service: they show addresses on purpose.
HAND_RUN_SCRIPTS = {"count_podcasts_by_subscriber.py", "test_vector_search.py"}
SKIP_DIRS = {"backend_venv", "test_env", "__pycache__", "tests", "scripts", "node_modules", "site-packages"}


def _is_output_call(call: ast.Call) -> bool:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id in {"print", "HTTPException"}
    if isinstance(f, ast.Attribute) and f.attr in LOG_METHODS:
        base = f.value
        name = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else "")
        return "log" in name.lower()
    return False


def _address_references(call: ast.Call):
    found = set()
    for n in ast.walk(call):
        if isinstance(n, ast.Name) and ADDRESS_NAMES.match(n.id):
            found.add(n.id)
        elif isinstance(n, ast.Attribute) and ADDRESS_NAMES.match(n.attr):
            found.add(n.attr)
        elif isinstance(n, ast.keyword) and n.arg and ADDRESS_NAMES.match(n.arg):
            found.add(n.arg)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and EMAIL_SHAPED.search(n.value):
            found.add("<address literal>")
    return found


def _service_python_files():
    for dirpath, dirnames, filenames in os.walk(BACKEND):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py") and name not in HAND_RUN_SCRIPTS:
                yield os.path.join(dirpath, name)


def test_no_log_print_or_error_call_names_an_address():
    offenders = []
    for path in _service_python_files():
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_output_call(node):
                refs = _address_references(node)
                if refs:
                    offenders.append(f"{os.path.relpath(path, BACKEND)}:{node.lineno} {sorted(refs)}")
    assert offenders == []


def test_the_source_check_can_fail():
    bad = ast.parse('structured_logger.info("x", email=user.email)\nprint(f"sent to {recipient_email}")\n'
                    'raise HTTPException(status_code=400, detail=f"no {email}")')
    calls = [n for n in ast.walk(bad) if isinstance(n, ast.Call) and _is_output_call(n)]
    assert len(calls) == 3 and all(_address_references(c) for c in calls)


# --- 2. the routes, run ------------------------------------------------------------------------------------------

class _Snap:
    def __init__(self, doc_id, data):
        self.id, self._d, self.exists = doc_id, data, data is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class FakeDB:
    def __init__(self, fail_create=False):
        self.docs = {}
        self.fail_create = fail_create

    def collection(self, name):
        return self

    def document(self, doc_id):
        db = self

        class Ref:
            def get(self_i, transaction=None):
                return _Snap(doc_id, db.docs.get(doc_id))

            def create(self_i, data):
                if db.fail_create:
                    raise RuntimeError(f"datastore refused the write for {EMAIL}")
                db.docs[doc_id] = dict(data)

            def update(self_i, data):
                db.docs[doc_id].update(data)

            def set(self_i, data, **kw):
                db.docs[doc_id] = dict(data)
        return Ref()


@pytest.fixture
def captured():
    """Everything the real structured logger writes, plus stdout, as one searchable string."""
    # Other test modules import the routes while utils.logging.structured_logger is a mock, which would leave a mock in
    # place here; use a real logger in every module under test so the real output is what gets searched.
    stream = io.StringIO()
    real = app_logging.StructuredLogger("copernicus-podcast-address-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter('%(message)s'))
    real.logger.addHandler(handler)
    real.logger.propagate = False
    real.logger.handlers = [handler]
    with patch.object(routes, 'structured_logger', real), patch.object(credential_tokens, 'structured_logger', real),          patch.object(subscriber_helpers, 'structured_logger', real), patch.object(app_logging, 'structured_logger', real):
        yield stream


def _routes_env(fake):
    return [patch.object(routes, 'db', fake), patch.object(subscriber_helpers, 'db', fake),
            patch.object(routes, 'check_rate_limit', MagicMock())]


class _Mailer:
    async def send_credential_link_email(self, *a, **k):
        return True


def _drive_every_path(fake_ok, fake_failing_create):
    """Success and failure paths of register, login, reset request and reset."""
    out = []
    with patch.object(routes, 'email_service', _Mailer()):
        for p in _routes_env(fake_ok):
            p.start()
        if True:
            if True:
                out.append(client.post("/api/subscribers/register", json={"email": EMAIL, "name": "N", "password": PASSWORD}))      # success
                out.append(client.post("/api/subscribers/register", json={"email": EMAIL, "name": "N", "password": PASSWORD}))      # 409
                out.append(client.post("/api/subscribers/login", json={"email": EMAIL, "password": PASSWORD}))                       # success
                out.append(client.post("/api/subscribers/login", json={"email": EMAIL, "password": "wrong-password-1"}))             # 401
                out.append(client.post("/api/subscribers/login", json={"email": "nobody." + EMAIL}))                                 # 404
                out.append(client.post("/api/subscribers/login", json={"email": EMAIL}))                                              # no method
                out.append(client.post("/api/subscribers/password-reset-request", json={"email": EMAIL}))
                out.append(client.post("/api/subscribers/password-reset-request", json={"email": "nobody." + EMAIL}))
                out.append(client.post("/api/subscribers/password-reset", json={"token": "T" * 43, "new_password": PASSWORD}))       # refused
        # internal-error paths: the exception text itself carries the address
        for p in _routes_env(fake_failing_create):
            p.start()
        out.append(client.post("/api/subscribers/register", json={"email": "other." + EMAIL, "name": "N", "password": PASSWORD}))   # 500
        with patch.object(routes, 'get_subscriber_by_email', side_effect=RuntimeError(f"lookup failed for {EMAIL}")):
            out.append(client.post("/api/subscribers/login", json={"email": EMAIL, "password": PASSWORD}))                            # 500
    return out


@pytest.fixture
def clean_patches():
    yield
    patch.stopall()


@pytest.mark.parametrize("backstop", [True, False], ids=["with-backstop", "call-sites-alone"])
def test_no_address_in_any_log_line_or_output_on_any_subscriber_path(captured, capsys, clean_patches, backstop):
    """With the backstop switched off, the call sites alone must already be clean."""
    if not backstop:
        patch.object(app_logging, 'redact_addresses', lambda v: v).start()
    ok = FakeDB()
    responses = _drive_every_path(ok, FakeDB(fail_create=True))
    statuses = [r.status_code for r in responses]
    assert 200 in statuses and 409 in statuses and 401 in statuses and 404 in statuses and 500 in statuses
    seen = captured.getvalue() + capsys.readouterr().out
    assert "Subscriber login successful" in seen and "Error registering subscriber" in seen and "Error during login" in seen
    assert EMAIL_SHAPED.findall(seen) == []
    assert "log.check.person" not in seen


def test_the_logs_still_say_which_account_and_what_kind_of_error(captured, clean_patches):
    _drive_every_path(FakeDB(), FakeDB(fail_create=True))
    entries = [json.loads(l) for l in captured.getvalue().splitlines() if l.startswith("{")]
    login_ok = [e for e in entries if e["message"] == "Subscriber login successful"]
    assert login_ok and login_ok[0]["subscriber_id"] == generate_subscriber_id(EMAIL)
    errors = [e for e in entries if e["message"] in ("Error registering subscriber", "Error during login")]
    assert {e["error_type"] for e in errors} == {"RuntimeError"}


# --- email sender: success and failure output ------------------------------------------------------------------------------

def _svc():
    with patch.dict('os.environ', {'NOTIFICATION_EMAIL': 'site@example.invalid', 'NOTIFICATION_EMAIL_PASSWORD': 'not-a-real-secret'}):
        return email_module.EmailService()


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_the_email_sender_prints_no_address_on_success_or_failure(capsys):
    svc = _svc()
    ok_smtp = MagicMock()
    with patch.object(email_module.smtplib, 'SMTP') as smtp:
        smtp.return_value.__enter__.return_value = ok_smtp
        _run(svc.send_podcast_completion_email(EMAIL, "job-1", "Title", "Topic", "https://example.invalid/a.mp3", "10", "canon"))
        _run(svc.send_podcast_failure_email(EMAIL, "job-2", "Topic", "went wrong", None))
    with patch.object(email_module.smtplib, 'SMTP', side_effect=OSError(f"recipient refused: <{EMAIL}>")), \
         patch.object(email_module.asyncio, 'sleep', new=lambda *_a, **_k: asyncio.sleep(0)):
        _run(svc.send_podcast_completion_email(EMAIL, "job-3", "Title", "Topic", "https://example.invalid/a.mp3", "10", "canon"))
        _run(svc.send_podcast_failure_email(EMAIL, "job-4", "Topic", "went wrong", None))
    out = capsys.readouterr()
    text = out.out + out.err
    assert "job-1" in text and EMAIL_SHAPED.findall(text) == []


def test_the_retry_wrapper_prints_the_error_type_not_its_text(capsys):
    @email_module.retry_email(max_retries=2, delay=0)
    async def always_fails():
        raise OSError(f"recipient refused: <{EMAIL}>")
    with pytest.raises(OSError):
        _run(always_fails())
    text = capsys.readouterr().out
    assert "OSError" in text and EMAIL_SHAPED.findall(text) == []


# --- 3. the logger's backstop ----------------------------------------------------------------------------------------------

def test_redact_replaces_addresses_in_strings_and_nested_values():
    value = {"message": f"failed for {EMAIL}", "error": f"<{EMAIL}> refused", "n": 3,
             "nested": {"list": [f"a {EMAIL}", 7, None]}, "ok": "no address here"}
    out = redact_addresses(value)
    assert EMAIL_SHAPED.findall(json.dumps(out)) == []
    assert out["message"] == f"failed for {ADDRESS_PLACEHOLDER}"
    assert out["n"] == 3 and out["ok"] == "no address here" and out["nested"]["list"][1:] == [7, None]


@pytest.mark.parametrize("text", ["a@b.co", "first.last+tag@sub.domain.example", "x_y%z@host-name.org", "UPPER@EXAMPLE.COM"])
def test_redact_catches_the_usual_shapes(text):
    assert redact_addresses(f"to {text}!") == f"to {ADDRESS_PLACEHOLDER}!"


def test_redact_leaves_ordinary_text_alone():
    for text in ("a 2026-10-29T10:00:00 timestamp", "path /api/x@2 (no domain)", "job-abc123", "user at host dot com"):
        assert redact_addresses(text) == text


def test_the_structured_logger_never_writes_an_address_even_if_a_call_passes_one(captured):
    app_logging.structured_logger.info(f"hello {EMAIL}", email=EMAIL, error=f"smtp said no to {EMAIL}", subscriber_id="abc")
    line = captured.getvalue()
    assert EMAIL_SHAPED.findall(line) == []
    entry = json.loads(line)
    assert entry["subscriber_id"] == "abc" and entry["email"] == ADDRESS_PLACEHOLDER
