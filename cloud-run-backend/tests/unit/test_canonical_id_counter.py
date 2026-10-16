"""Episode IDs are never reused (ever-math-260007 was deleted and the next episode got the same ID again). Offline: a fake Firestore."""
import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

from google.cloud import firestore

import services.canonical_service as cs


def run(coro):
    loop = asyncio.new_event_loop()      # not asyncio.run: that leaves no current loop and breaks later tests that call get_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class Snap:
    def __init__(self, data):
        self._d, self.exists = data, data is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class Ref:
    def __init__(self, store, key):
        self.store, self.key = store, key

    def get(self, transaction=None):
        return Snap(self.store.get(self.key))


class Collection:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def stream(self):
        if self.db.fail_reads:
            raise RuntimeError("Firestore unavailable")
        return [SimpleNamespace(to_dict=lambda d=d: d) for d in self.db.docs.get(self.name, [])]

    def document(self, key):
        return Ref(self.db.counters, key)


class FakeDb:
    def __init__(self, live_ids=(), fail_reads=False):
        self.docs = {"episodes": [{"canonical_filename": i} for i in live_ids]}
        self.counters, self.fail_reads = {}, fail_reads

    def collection(self, name):
        return Collection(self, name)

    def transaction(self):
        db = self
        return SimpleNamespace(set=lambda ref, data, merge=False: db.counters.setdefault(ref.key, {}).update(data))


@pytest.fixture
def world(monkeypatch):
    monkeypatch.setattr(firestore, "transactional", lambda f: f)            # a transaction on the fake is just a call
    state = SimpleNamespace(db=FakeDb(), gcs=[])
    monkeypatch.setattr(cs, "db", state.db)
    import requests

    def fake_get(url, timeout=10):
        items = [{"name": "audio/" + n + ".mp3"} for n in state.gcs]
        return SimpleNamespace(status_code=200, json=lambda: {"items": items})
    monkeypatch.setattr(requests, "get", fake_get)
    return state


def use(state, **kw):
    state.db = FakeDb(**kw)
    cs.db = state.db
    return state.db


def allocate(category="Mathematics", fmt="feature"):
    return run(cs.CanonicalService().determine_canonical_filename("t", "t", category, fmt))


def test_a_deleted_episode_id_is_not_issued_again(world):
    use(world, live_ids=[f"ever-math-26{n:04d}" for n in range(1, 7)])
    assert allocate() == "ever-math-260007"
    world.db.docs["episodes"].append({"canonical_filename": "ever-math-260007"})
    # rule-16 deletion: the episode, its job and its audio are gone, so nothing live names 260007 any more
    world.db.docs["episodes"] = [d for d in world.db.docs["episodes"] if d["canonical_filename"] != "ever-math-260007"]
    world.gcs = []
    assert allocate() == "ever-math-260008"                                 # this was 260007 again before the counter


def test_ids_keep_rising_and_each_category_year_has_its_own_counter(world):
    use(world, live_ids=["ever-math-260003", "ever-bio-260040"])
    assert [allocate(), allocate(), allocate("Biology")] == ["ever-math-260004", "ever-math-260005", "ever-bio-260041"]
    assert set(world.db.counters) == {"ever-math-26", "ever-bio-26"}


def test_a_missing_counter_starts_above_everything_that_exists_in_firestore_or_storage(world):
    use(world, live_ids=["ever-math-260002"])
    world.gcs = ["ever-math-260009"]                                        # in the bucket but not in Firestore
    assert allocate() == "ever-math-260010"


def test_a_counter_ahead_of_the_live_episodes_wins(world):
    db = use(world, live_ids=["ever-math-260002"])
    db.counters["ever-math-26"] = {"last_seq": 7}
    assert allocate() == "ever-math-260008"


def test_two_requests_never_get_the_same_id(world):
    use(world)

    async def both():
        svc = cs.CanonicalService()
        return await asyncio.gather(*[svc.determine_canonical_filename("t", "t", "Mathematics", "feature") for _ in range(2)])
    a, b = run(both())
    assert a != b


def test_when_firestore_cannot_be_read_the_episode_fails_instead_of_guessing(world):
    use(world, fail_reads=True)
    with pytest.raises(cs.CanonicalAllocationError):
        allocate()
    cs.db = None
    with pytest.raises(cs.CanonicalAllocationError):
        allocate()


def test_news_serials_are_not_reused_either(world):
    use(world)
    first = allocate("Biology", "news")
    world.gcs = []                                                          # the news episode was deleted
    second = allocate("Biology", "news")
    assert first.endswith("-0001") and second.endswith("-0002")


def test_the_old_helper_is_unchanged():
    assert cs.next_evergreen_filename(["ever-math-260006"], "math", 2026) == "ever-math-260007"
