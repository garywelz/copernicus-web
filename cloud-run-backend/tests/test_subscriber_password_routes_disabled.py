"""POST /api/subscribers/password-reset is disabled for every caller (403), and POST /api/subscribers/register never modifies an
existing account (409). In both cases an existing account's password hash must be unchanged afterwards."""
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from google.api_core.exceptions import AlreadyExists

with patch('config.database.db', MagicMock()), \
     patch('utils.logging.structured_logger', MagicMock()):
    from endpoints.subscriber import routes
    from endpoints.subscriber.routes import router

from utils import subscriber_helpers
from utils.subscriber_helpers import generate_subscriber_id, hash_password

app = FastAPI()
app.include_router(router)
client = TestClient(app)

EMAIL = "existing.person@example.invalid"
OLD_PASSWORD = "old-password-123"


class _Snap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class FakeDB:
    """In-memory 'subscribers' collection that records every write."""

    def __init__(self):
        self.docs = {}
        self.writes = []

    def collection(self, name):
        assert name == 'subscribers'
        return self

    def document(self, doc_id):
        db = self

        class Ref:
            def get(self_inner):
                return _Snap(doc_id, db.docs.get(doc_id))

            def set(self_inner, data, **kw):
                db.writes.append(('set', doc_id))
                db.docs[doc_id] = dict(data)

            def update(self_inner, data):
                db.writes.append(('update', doc_id))
                db.docs[doc_id].update(data)

            def create(self_inner, data):
                db.writes.append(('create', doc_id))
                if doc_id in db.docs:
                    raise AlreadyExists("exists")
                db.docs[doc_id] = dict(data)

        return Ref()


def _db_with_existing(legacy_id=False):
    fake = FakeDB()
    doc_id = generate_subscriber_id(EMAIL)
    if legacy_id:
        doc_id = doc_id[:16]
    fake.docs[doc_id] = {
        'subscriber_id': doc_id, 'email': EMAIL, 'name': 'Existing', 'subscription_tier': 'free',
        'password_hash': hash_password(OLD_PASSWORD), 'can_generate': True,
    }
    return fake, doc_id


def _call(fake, path, **kw):
    with patch.object(routes, 'db', fake), patch.object(subscriber_helpers, 'db', fake):
        return client.post(path, **kw)


# --- password-reset ---------------------------------------------------------------------------------------

def test_password_reset_is_403_for_an_existing_account_and_changes_nothing():
    fake, doc_id = _db_with_existing()
    before = fake.docs[doc_id]['password_hash']
    r = _call(fake, "/api/subscribers/password-reset", json={"email": EMAIL, "new_password": "attacker-chosen-1"})
    assert r.status_code == 403
    assert r.json()["detail"] == "Password reset is temporarily unavailable; contact the administrator"
    assert fake.docs[doc_id]['password_hash'] == before
    assert fake.writes == []


def test_password_reset_is_403_for_unknown_email_empty_and_malformed_bodies():
    fake, doc_id = _db_with_existing()
    before = dict(fake.docs[doc_id])
    for kw in ({"json": {"email": "nobody@example.invalid", "new_password": "x"}},
               {"json": {}},
               {"content": "not json at all", "headers": {"content-type": "application/json"}},
               {}):
        r = _call(fake, "/api/subscribers/password-reset", **kw)
        assert r.status_code == 403, kw
    assert fake.docs[doc_id] == before
    assert fake.writes == []


def test_password_reset_makes_no_database_call_at_all():
    spy = MagicMock()
    r = _call(spy, "/api/subscribers/password-reset", json={"email": EMAIL, "new_password": "x"})
    assert r.status_code == 403
    assert spy.mock_calls == []


def test_old_password_still_logs_in_after_an_attempted_reset():
    fake, doc_id = _db_with_existing()
    _call(fake, "/api/subscribers/password-reset", json={"email": EMAIL, "new_password": "attacker-chosen-1"})
    with patch.object(routes, 'check_rate_limit', return_value=None):
        ok = _call(fake, "/api/subscribers/login", json={"email": EMAIL, "password": OLD_PASSWORD})
        bad = _call(fake, "/api/subscribers/login", json={"email": EMAIL, "password": "attacker-chosen-1"})
    assert ok.status_code == 200
    assert bad.status_code == 401


# --- register -----------------------------------------------------------------------------------------------

def test_register_existing_email_is_409_and_the_password_hash_is_unchanged():
    fake, doc_id = _db_with_existing()
    before = dict(fake.docs[doc_id])
    r = _call(fake, "/api/subscribers/register", json={"email": EMAIL, "name": "Someone", "password": "attacker-chosen-1"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]
    assert fake.docs[doc_id] == before            # every field, not only the hash
    assert fake.writes == []                       # no set, update or create


def test_register_existing_email_found_under_the_legacy_id_format_is_also_409():
    fake, doc_id = _db_with_existing(legacy_id=True)
    before = dict(fake.docs[doc_id])
    r = _call(fake, "/api/subscribers/register", json={"email": EMAIL, "name": "Someone", "password": "attacker-chosen-1"})
    assert r.status_code == 409
    assert fake.docs[doc_id] == before
    assert fake.writes == []


def test_old_password_still_logs_in_after_an_attempted_register_overwrite():
    fake, doc_id = _db_with_existing()
    _call(fake, "/api/subscribers/register", json={"email": EMAIL, "name": "Someone", "password": "attacker-chosen-1"})
    with patch.object(routes, 'check_rate_limit', return_value=None):
        ok = _call(fake, "/api/subscribers/login", json={"email": EMAIL, "password": OLD_PASSWORD})
        bad = _call(fake, "/api/subscribers/login", json={"email": EMAIL, "password": "attacker-chosen-1"})
    assert ok.status_code == 200
    assert bad.status_code == 401


def test_register_new_email_still_works_and_stores_a_hashed_password():
    fake = FakeDB()
    r = _call(fake, "/api/subscribers/register", json={"email": "new.person@example.invalid", "name": "New", "password": "fresh-pass-1"})
    assert r.status_code == 200
    doc_id = generate_subscriber_id("new.person@example.invalid")
    assert fake.writes == [('create', doc_id)]
    stored = fake.docs[doc_id]['password_hash']
    assert stored.startswith("scrypt$") and "fresh-pass-1" not in stored
    assert 'can_generate' not in fake.docs[doc_id]          # a new account is not on the allow-list


def test_register_losing_a_creation_race_is_409_not_an_overwrite():
    fake = FakeDB()
    doc_id = generate_subscriber_id("race.person@example.invalid")
    real_document = fake.document

    def racing_document(d):
        ref = real_document(d)
        orig_create = ref.create

        def create(data):
            fake.docs[d] = {'password_hash': 'winner-hash'}   # another request created it first
            return orig_create(data)
        ref.create = create
        return ref

    fake.document = racing_document
    r = _call(fake, "/api/subscribers/register", json={"email": "race.person@example.invalid", "name": "R", "password": "loser-pass-1"})
    assert r.status_code == 409
    assert fake.docs[doc_id] == {'password_hash': 'winner-hash'}
