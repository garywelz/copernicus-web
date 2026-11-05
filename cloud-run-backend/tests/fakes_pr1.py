"""Offline fakes for the private-episode access tests (onboarding PR 1): an in-memory Firestore and session-token helpers.

The fake records every write (collection, document id, operation) in `db.writes`, so a test can prove that a route did NOT write somewhere (the feed)."""
import hashlib
from datetime import datetime, timedelta


class Snap:
    def __init__(self, ref, data):
        self.reference, self.id, self._d, self.exists = ref, ref.id, data, data is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class Ref:
    def __init__(self, db, col, id_):
        self.db, self.col, self.id = db, col, id_

    @property
    def _store(self):
        return self.db.data.setdefault(self.col, {})

    def get(self, transaction=None):
        return Snap(self, self._store.get(self.id))

    def set(self, data, merge=False):
        if self.col in self.db.fail_set_on:
            raise RuntimeError("forced write failure")
        self.db.writes.append((self.col, self.id, "set"))
        self._store[self.id] = {**self._store.get(self.id, {}), **data} if merge else dict(data)

    def update(self, data):
        self.db.writes.append((self.col, self.id, "update"))
        self._store.setdefault(self.id, {}).update(data)

    def delete(self):
        self.db.writes.append((self.col, self.id, "delete"))
        self._store.pop(self.id, None)


class Query:
    def __init__(self, db, col, filters=(), order=None, cap=None):
        self.db, self.col, self.filters, self.order, self.cap = db, col, filters, order, cap

    def order_by(self, field, direction=None):
        return Query(self.db, self.col, self.filters, field, self.cap)

    def limit(self, n):
        return Query(self.db, self.col, self.filters, self.order, n)

    def where(self, field, op, value):
        assert op == "=="
        return Query(self.db, self.col, self.filters + ((field, value),), self.order, self.cap)

    def stream(self):
        out = []
        for id_, d in list(self.db.data.get(self.col, {}).items()):
            if all(d.get(f) == v for f, v in self.filters):
                out.append(Snap(Ref(self.db, self.col, id_), d))
        if self.order:
            out.sort(key=lambda x: str(x.to_dict().get(self.order, "")), reverse=True)
        return out[: self.cap] if self.cap else out


class Col(Query):
    def document(self, id_):
        return Ref(self.db, self.col, id_)


class Txn:
    def update(self, ref, data):
        ref.update(data)

    def set(self, ref, data):
        ref.set(data)


class FakeDB:
    def __init__(self, **collections):
        self.data = {k: {i: dict(d) for i, d in v.items()} for k, v in collections.items()}
        self.writes = []
        self.fail_set_on = set()      # collection names whose set() should raise
        self.collections_read = []

    def collection(self, name):
        self.collections_read.append(name)
        return Col(self, name)

    def transaction(self):
        return Txn()


def passthrough_transactional(fn):
    """Stands in for firestore.transactional: runs the function directly with a fake transaction."""
    def runner(transaction, *args):
        return fn(Txn(), *args)
    return runner


def subscriber(raw_token=None, **fields):
    """A subscriber document. With `raw_token`, the document holds that token's sha256 and a future expiry, as login stores it."""
    d = dict(fields)
    if raw_token:
        d["session_token_hash"] = hashlib.sha256(raw_token.encode()).hexdigest()
        d["session_token_expires"] = (datetime.utcnow() + timedelta(days=1)).isoformat()
    return d
