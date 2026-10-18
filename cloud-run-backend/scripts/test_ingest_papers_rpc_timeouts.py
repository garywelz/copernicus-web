#!/usr/bin/env python3
"""RPC deadline + logging checks for ingest_papers_from_metadata_json.

Run: python scripts/test_ingest_papers_rpc_timeouts.py
"""
from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from types import SimpleNamespace

from google.api_core.exceptions import AlreadyExists, DeadlineExceeded

SCRIPT = Path(__file__).resolve().parent / "ingest_papers_from_metadata_json.py"


def _load():
    spec = importlib.util.spec_from_file_location("ingest_papers_from_metadata_json", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _StuckBatch:
    def __init__(self):
        self.seen_timeout = None
        self.seen_retry = None

    def commit(self, retry=None, timeout=None):
        self.seen_timeout = timeout
        self.seen_retry = retry
        # Simulate a wedged RPC that eventually surfaces as DeadlineExceeded.
        raise DeadlineExceeded("simulated stuck batch.commit")


class _StuckDocRef:
    def __init__(self, doc_id: str = "paper_deadbeef"):
        self.id = doc_id
        self.seen_timeout = None

    def create(self, doc, retry=None, timeout=None):
        self.seen_timeout = timeout
        raise DeadlineExceeded(f"simulated stuck create for {self.id}")


class _ExistsDocRef:
    def __init__(self, doc_id: str = "paper_exists"):
        self.id = doc_id
        self.calls = 0

    def create(self, doc, retry=None, timeout=None):
        self.calls += 1
        raise AlreadyExists("already there")


class _StuckBlob:
    def __init__(self):
        self.seen_timeout = None

    def upload_from_filename(self, path, timeout=None, retry=None):
        self.seen_timeout = timeout
        raise DeadlineExceeded("simulated stuck GCS upload")


def main() -> int:
    m = _load()

    # 1) batch.commit: stuck call times out, logs DeadlineExceeded, re-raises
    batch = _StuckBatch()
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        try:
            m._batch_commit(batch)
            raise AssertionError("expected DeadlineExceeded")
        except DeadlineExceeded:
            pass
    finally:
        sys.stdout = old
    out = buf.getvalue()
    assert "batch.commit timed out" in out, out
    assert "DeadlineExceeded" in out, out
    assert batch.seen_timeout == m._firestore_rpc_timeout_s()
    assert batch.seen_retry is not None

    # 2) doc create: stuck call times out and is logged
    ref = _StuckDocRef()
    buf = io.StringIO()
    sys.stdout = buf
    try:
        try:
            m._doc_create(ref, {"title": "x"})
            raise AssertionError("expected DeadlineExceeded")
        except DeadlineExceeded:
            pass
    finally:
        sys.stdout = old
    out = buf.getvalue()
    assert "document.create timed out" in out, out
    assert ref.id in out
    assert ref.seen_timeout == m._firestore_rpc_timeout_s()

    # 3) AlreadyExists is not swallowed by the deadline path
    exists = _ExistsDocRef()
    try:
        m._doc_create(exists, {"title": "y"})
        raise AssertionError("expected AlreadyExists")
    except AlreadyExists:
        pass
    assert exists.calls == 1

    # 4) GCS upload: stuck call times out, logged, returned as error string
    class _FakeStorage:
        class Client:
            def __init__(self, project=None):
                pass

            def bucket(self, name):
                return SimpleNamespace(blob=lambda n: stuck_blob)

    stuck_blob = _StuckBlob()
    # Inject fake google.cloud.storage into the function's import path
    import types

    fake_cloud = types.ModuleType("google.cloud.storage")
    fake_cloud.Client = _FakeStorage.Client
    sys.modules["google.cloud.storage"] = fake_cloud

    tmp = Path(__file__).resolve().parent / "_tmp_reject_log.jsonl"
    tmp.write_text('{"reject":1}\n', encoding="utf-8")
    try:
        buf = io.StringIO()
        sys.stdout = buf
        try:
            err = m._upload_reject_log_gcs(tmp, "gs://bucket/obj.jsonl")
        finally:
            sys.stdout = old
        assert err and "DeadlineExceeded" in err, err
        assert "GCS reject-log upload timed out" in buf.getvalue()
        assert stuck_blob.seen_timeout == m._gcs_upload_timeout_s()
    finally:
        tmp.unlink(missing_ok=True)
        sys.modules.pop("google.cloud.storage", None)

    # 5) Client helper logs configured deadlines (construction itself is local)
    class _FakeFS:
        def __init__(self, project=None, database=None):
            self.project = project
            self.database = database

    real_fs = m.firestore.Client
    m.firestore.Client = _FakeFS
    buf = io.StringIO()
    sys.stdout = buf
    try:
        client = m._firestore_client("proj", "copernicusai")
    finally:
        sys.stdout = old
        m.firestore.Client = real_fs
    assert client.project == "proj"
    assert "rpc_timeout_s=" in buf.getvalue()

    print("OK test_ingest_papers_rpc_timeouts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
