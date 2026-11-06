"""An in-memory Firestore whose transactions are ATOMIC: writes made through a transaction are buffered and applied together at commit, or not at all
(unlike tests/fakes_pr1.py and the PR 0 fake, which apply each write immediately). That is what lets a test force a failure partway through an invitation
and prove that nothing was changed.

Failure injection: `db.fail_after_ops = n` raises on the n-th buffered write; `db.fail_on_commit = True` raises at commit; `db.fail_writes_to = {"collection"}`
raises when a transaction writes to that collection. Concurrency: `run_in_transaction` serializes transactions with a lock (as Firestore's
retry-on-contention does); it tests the code's checks, not Firestore's own isolation."""
import copy
import threading

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore


class Snap:
    def __init__(self, ref, data):
        self.reference, self.id, self._d, self.exists = ref, ref.id, data, data is not None

    def to_dict(self):
        return copy.deepcopy(self._d) if self._d is not None else None


def _apply_update(doc, data):
    for k, v in data.items():
        if v is firestore.DELETE_FIELD:
            doc.pop(k, None)
        else:
            doc[k] = copy.deepcopy(v)


class Ref:
    def __init__(self, db, col, id_):
        self.db, self.col, self.id = db, col, id_

    @property
    def _store(self):
        return self.db.data.setdefault(self.col, {})

    def get(self, transaction=None):
        return Snap(self, self.db.data.get(self.col, {}).get(self.id))      # a read never creates anything

    # non-transactional writes (used to seed state and by the registration route)
    def set(self, data, merge=False):
        self._store[self.id] = {**self._store.get(self.id, {}), **copy.deepcopy(data)} if merge else copy.deepcopy(data)

    def create(self, data):
        if self.id in self._store:
            raise AlreadyExists("exists")
        self._store[self.id] = copy.deepcopy(data)

    def update(self, data):
        _apply_update(self._store.setdefault(self.id, {}), data)

    def delete(self):
        self._store.pop(self.id, None)


class Query:
    def __init__(self, db, col, filters=(), cap=None):
        self.db, self.col, self.filters, self.cap = db, col, filters, cap

    def where(self, field, op, value):
        assert op == "=="
        return Query(self.db, self.col, self.filters + ((field, value),), self.cap)

    def limit(self, n):
        return Query(self.db, self.col, self.filters, n)

    def select(self, fields):                      # a projection: the fake returns whole documents, which is a superset
        return self

    def stream(self, transaction=None):
        out = [Snap(Ref(self.db, self.col, i), d) for i, d in list(self.db.data.get(self.col, {}).items()) if all(d.get(f) == v for f, v in self.filters)]
        return out[: self.cap] if self.cap else out


class Col(Query):
    def document(self, id_):
        return Ref(self.db, self.col, id_)


class Txn:
    def __init__(self, db):
        self.db, self.ops = db, []

    def _buffer(self, kind, ref, data=None):
        if ref.col in self.db.fail_writes_to:
            raise RuntimeError(f"forced failure writing to {ref.col}")
        self.ops.append((kind, ref, copy.deepcopy(data)))
        if self.db.fail_after_ops is not None and len(self.ops) >= self.db.fail_after_ops:
            raise RuntimeError("forced failure partway through the transaction")

    def set(self, ref, data):
        self._buffer("set", ref, data)

    def update(self, ref, data):
        self._buffer("update", ref, data)

    def delete(self, ref):
        self._buffer("delete", ref)

    def commit(self):
        if self.db.fail_on_commit:
            raise RuntimeError("forced failure at commit")
        for kind, ref, data in self.ops:                    # applied together, in order
            if kind == "set":
                ref._store[ref.id] = data
            elif kind == "update":
                _apply_update(ref._store.setdefault(ref.id, {}), data)
            else:
                ref._store.pop(ref.id, None)


class FakeDB:
    def __init__(self, **collections):
        self.data = {k: {i: copy.deepcopy(d) for i, d in v.items()} for k, v in collections.items()}
        self.lock = threading.RLock()
        self.fail_after_ops = None
        self.fail_on_commit = False
        self.fail_writes_to = set()

    def collection(self, name):
        return Col(self, name)

    def transaction(self):
        return Txn(self)


def run_in_transaction(db, fn, *args):
    """Stands in for utils.credential_tokens._run_in_transaction: run fn(transaction, *args), then commit atomically; an exception discards everything."""
    with db.lock:
        txn = db.transaction()
        result = fn(txn, *args)
        txn.commit()
        return result
