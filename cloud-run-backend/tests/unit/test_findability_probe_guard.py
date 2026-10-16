"""The findability probe's existence guard (2026-10-16): an anchor whose expected document is gone is reported as STALE ANCHOR (a WARNING that counts in the
overall result), not ALERT. ALERT is reserved for "the document exists but is not retrievable". Offline: fake Firestore, fake HTTP."""
import importlib.util
import pathlib
import sys

import pytest

PROBE = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "findability_probe.py"


@pytest.fixture(scope="module")
def probe():
    spec = importlib.util.spec_from_file_location("findability_probe_under_test", PROBE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod            # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


class Snap:
    def __init__(self, data):
        self._d, self.exists = data, data is not None

    def to_dict(self):
        return dict(self._d) if self._d is not None else None


class FakeDB:
    def __init__(self, docs):
        self.docs = docs  # {(collection, id): record}

    def collection(self, name):
        db = self

        class C:
            def document(self, id_):
                class D:
                    def get(_self):
                        return Snap(db.docs.get((name, id_)))
                return D()
        return C()


class Resp:
    def __init__(self, key, ids):
        self._key, self._ids = key, ids

    def raise_for_status(self):
        pass

    def json(self):
        return {self._key: [{"job_id": i, "paper_id": i, "process_id": i} for i in self._ids]}


def only(probe, monkeypatch, collection, anchors):
    monkeypatch.setattr(probe, "ANCHORS", {collection: anchors})


EXP = "ever-bio-250007"
ANCHOR = [{"query": "gene editing without cutting DNA", "expected_id": EXP}]


def test_the_guard_fires_on_a_deleted_id_without_querying(probe, monkeypatch):
    only(probe, monkeypatch, "episodes", ANCHOR)

    def no_http(*a, **k):
        raise AssertionError("a stale anchor must not be queried")
    res = probe.run_check_a(FakeDB({}), http_get=no_http)
    assert len(res) == 1 and res[0].severity == probe.SEV_STALE and res[0].rank is None
    assert EXP in res[0].note and "does not exist" in res[0].note
    report = probe.build_report(res, [], [])
    assert report["summary"]["overall"] == "WARNING"                      # counts in the overall result, but is not an ALERT
    assert report["summary"]["check_a_stale"] == 1 and report["summary"]["check_a_alerts"] == 0
    assert report["check_a_positive_findability"][0]["note"] == res[0].note


def test_the_guard_does_not_fire_on_a_present_id(probe, monkeypatch):
    only(probe, monkeypatch, "episodes", [{"query": "q", "expected_id": "ever-math-260010"}])
    db = FakeDB({("episodes", "ever-math-260010"): {"submitted_to_rss": True}})
    res = probe.run_check_a(db, http_get=lambda *a, **k: Resp("podcasts", ["x", "ever-math-260010"]))
    assert res[0].severity == probe.SEV_PASS and res[0].rank == 2
    assert probe.build_report(res, [], [])["summary"]["overall"] == "OK"


def test_alert_is_kept_for_a_present_document_that_is_not_retrievable(probe, monkeypatch):
    only(probe, monkeypatch, "episodes", [{"query": "q", "expected_id": "ever-math-260010"}])
    db = FakeDB({("episodes", "ever-math-260010"): {"visible_on_web": True}})
    res = probe.run_check_a(db, http_get=lambda *a, **k: Resp("podcasts", ["a", "b", "c"]))
    assert res[0].severity == probe.SEV_ALERT and res[0].rank is None
    report = probe.build_report(res, [], [])
    assert report["summary"]["overall"] == "ALERT" and report["summary"]["check_a_alerts"] == 1 and report["summary"]["check_a_stale"] == 0


def test_a_request_failure_on_a_present_document_is_an_alert(probe, monkeypatch):
    only(probe, monkeypatch, "research_papers", [{"query": "q", "expected_id": "pubmed_1"}])
    db = FakeDB({("research_papers", "pubmed_1"): {"title": "t"}})

    def boom(*a, **k):
        raise RuntimeError("timeout")
    res = probe.run_check_a(db, http_get=boom)
    assert res[0].severity == probe.SEV_ALERT and "request failed" in res[0].note
    assert probe.build_report(res, [], [])["summary"]["overall"] == "ALERT"


def test_a_private_episode_is_a_stale_anchor_because_the_endpoint_hides_it(probe, monkeypatch):
    only(probe, monkeypatch, "episodes", [{"query": "q", "expected_id": "ever-bio-260001"}])
    db = FakeDB({("episodes", "ever-bio-260001"): {"title": "t", "submitted_to_rss": False, "visible_on_web": False}})
    res = probe.run_check_a(db, http_get=lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not be queried")))
    assert res[0].severity == probe.SEV_STALE and "not public" in res[0].note


def test_a_stale_anchor_and_a_real_alert_together_report_alert(probe):
    stale = probe.AnchorResult("episodes", "q", "gone", None, probe.SEV_STALE, "gone")
    alert = probe.AnchorResult("episodes", "q", "here", None, probe.SEV_ALERT)
    s = probe.build_report([stale, alert], [], [])["summary"]
    assert s["overall"] == "ALERT" and s["check_a_alerts"] == 1 and s["check_a_stale"] == 1 and s["check_a_total"] == 2


def test_report_keeps_the_fields_glmp_reads(probe):
    s = probe.build_report([], [], [])["summary"]
    for key in ("overall", "check_a_alerts", "check_a_total", "check_c_warnings"):    # glmp scripts/build_master_todo.py read_findability_status
        assert key in s


def test_every_collection_has_at_least_two_anchors_and_none_names_a_deleted_episode(probe):
    for collection, anchors in probe.ANCHORS.items():
        assert len(anchors) >= 2, collection
        assert len({a["expected_id"] for a in anchors}) == len(anchors), collection
    episode_ids = {a["expected_id"] for a in probe.ANCHORS["episodes"]}
    assert {"ever-math-260010", "ever-compsci-250041"} <= episode_ids
    assert "ever-bio-250007" not in episode_ids                                         # deleted 2026-09-29 under rule 16


def test_the_probe_copy_of_the_public_rule_matches_the_backend_rule(probe):
    from utils.episode_access import is_public_episode
    for rec in ({"submitted_to_rss": True}, {"visible_on_web": True}, {"visibility": "public"}, {}, None, "x"):
        assert probe._is_public_episode(rec) == is_public_episode(rec)
