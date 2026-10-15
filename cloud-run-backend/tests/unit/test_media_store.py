"""Stage 2 of private-episode access control: media files are written to the private bucket, promoted to the public bucket (verified, fail closed)
at publish time, and reviewed through signed links. Offline: fake storage and fake Firestore."""
import asyncio
import hashlib
import pathlib
import re
import zlib
from datetime import timedelta
from unittest.mock import MagicMock

import pytest

import media_store as ms

EID = "ever-math-990001"
OTHER = "ever-math-990002"


class FakeBlob:
    def __init__(self, bucket, name, data=b""):
        self.bucket, self.name, self.data = bucket, name, data

    @property
    def md5_hash(self):
        import base64
        return base64.b64encode(hashlib.md5(self.data).digest()).decode()

    @property
    def crc32c(self):
        return str(zlib.crc32(self.data))

    @property
    def size(self):
        return len(self.data)

    def delete(self):
        self.bucket.store.pop(self.name, None)

    def generate_signed_url(self, **kw):
        self.bucket.signed.append((self.name, kw))
        return f"signed://{self.bucket.name}/{self.name}?exp={int(kw['expiration'].total_seconds())}"


class FakeBucket:
    def __init__(self, name, corrupt_on=None):
        self.name, self.store, self.signed, self.corrupt_on = name, {}, [], corrupt_on

    def add(self, name, data=b"x"):
        self.store[name] = FakeBlob(self, name, data)

    def blob(self, name):
        return self.store.get(name) or FakeBlob(self, name)

    def get_blob(self, name):
        return self.store.get(name)

    def list_blobs(self, prefix=""):
        return [b for n, b in sorted(self.store.items()) if n.startswith(prefix)]

    def copy_blob(self, src, dst_bucket, new_name):
        data = src.data if new_name != dst_bucket.corrupt_on else src.data + b"!"
        dst_bucket.store[new_name] = FakeBlob(dst_bucket, new_name, data)


class FakeClient:
    def __init__(self, corrupt_on=None):
        self.buckets = {ms.PRIVATE_BUCKET: FakeBucket(ms.PRIVATE_BUCKET), ms.PUBLIC_BUCKET: FakeBucket(ms.PUBLIC_BUCKET, corrupt_on)}

    def bucket(self, name):
        return self.buckets[name]


def files(eid):
    return [f"audio/{eid}.mp3", f"transcripts/{eid}-transcript.md", f"thumbnails/{eid}-thumb.jpg", f"episode-images/{eid}-image-1.jpg",
            f"episode-images/{eid}-image-2.jpg", f"animations/{eid}/cues.json", f"animations/{eid}/f0.png", f"generated/videos/{eid}.mp4"]


@pytest.fixture
def client():
    c = FakeClient()
    for eid in (EID, OTHER):
        for n in files(eid):
            c.buckets[ms.PRIVATE_BUCKET].add(n, f"{n}-bytes".encode())
    return c


def test_names_are_constants_and_urls_are_the_eventual_public_ones():
    assert ms.PRIVATE_BUCKET == "regal-scholar-453620-r7-private-media" and ms.PUBLIC_BUCKET == "regal-scholar-453620-r7-podcast-storage"
    assert ms.public_url("audio/a.mp3") == "https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/audio/a.mp3"


def test_promote_copies_every_file_of_the_episode_and_nothing_else(client):
    out = ms.promote(EID, client)
    pub = client.buckets[ms.PUBLIC_BUCKET].store
    assert sorted(out["objects"]) == sorted(files(EID)) and out["promoted"] == len(files(EID)) and not out["already_public"]
    assert set(pub) == set(files(EID))                                   # the other episode stays private
    assert all(n not in pub for n in files(OTHER))


def test_promote_is_fail_closed_on_a_checksum_mismatch(client):
    c = FakeClient(corrupt_on=f"transcripts/{EID}-transcript.md")
    c.buckets[ms.PRIVATE_BUCKET].store = client.buckets[ms.PRIVATE_BUCKET].store
    for b in c.buckets[ms.PRIVATE_BUCKET].store.values():
        b.bucket = c.buckets[ms.PRIVATE_BUCKET]
    with pytest.raises(ms.MediaError):
        ms.promote(EID, c)
    assert c.buckets[ms.PUBLIC_BUCKET].store == {}                       # every copy made in the call was removed


def test_promote_handles_older_episodes_and_missing_media():
    c = FakeClient()
    c.buckets[ms.PUBLIC_BUCKET].add(f"audio/{EID}.mp3")
    assert ms.promote(EID, c) == {"episode_id": EID, "promoted": 0, "already_public": True, "objects": []}
    with pytest.raises(ms.MediaError):
        ms.promote("ever-math-999999", c)
    c2 = FakeClient()
    c2.buckets[ms.PRIVATE_BUCKET].add(f"transcripts/{EID}-transcript.md")
    with pytest.raises(ms.MediaError):                                    # files but no audio anywhere
        ms.promote(EID, c2)


def test_demote_removes_only_the_named_public_copies(client):
    ms.promote(EID, client)
    assert ms.demote([f"audio/{EID}.mp3", "audio/not-there.mp3"], client) == 2
    assert f"audio/{EID}.mp3" not in client.buckets[ms.PUBLIC_BUCKET].store
    assert f"transcripts/{EID}-transcript.md" in client.buckets[ms.PUBLIC_BUCKET].store


def test_signed_links_cap_at_seven_days_and_use_signing_arguments(client):
    signer = lambda: {"service_account_email": "sa@x", "access_token": "t"}
    out = ms.signed_links(EID, timedelta(days=30), client, signer)
    assert out["media_state"] == "private" and out["expires_in_seconds"] == 7 * 86400
    assert set(out["links"]) == set(files(EID)) and all(v.startswith("signed://") and "exp=604800" in v for v in out["links"].values())
    name, kw = client.buckets[ms.PRIVATE_BUCKET].signed[0]
    assert kw["version"] == "v4" and kw["method"] == "GET" and kw["service_account_email"] == "sa@x" and kw["access_token"] == "t"


def test_signed_links_give_public_addresses_for_public_files():
    c = FakeClient()
    c.buckets[ms.PUBLIC_BUCKET].add(f"audio/{EID}.mp3")
    out = ms.signed_links(EID, timedelta(hours=1), c, lambda: {})
    assert out["media_state"] == "public" and out["links"][f"audio/{EID}.mp3"] == ms.public_url(f"audio/{EID}.mp3")


def test_signed_audio_link_only_for_private_audio(client):
    signer = lambda: {}
    assert ms.signed_audio_link(EID, 7, client, signer).startswith("signed://" + ms.PRIVATE_BUCKET)
    assert ms.signed_audio_link("ever-math-999999", 7, client, signer) is None


# ------------------------------------------------------------------ the publish path
def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def submit_env(monkeypatch):
    from endpoints.subscriber import routes as r
    doc = MagicMock()
    doc.exists = True
    doc.to_dict.return_value = {"subscriber_id": "sub1", "result": {"canonical_filename": EID}}
    db = MagicMock()
    db.collection.return_value.document.return_value.get.return_value = doc
    monkeypatch.setattr(r, "db", db)
    monkeypatch.setattr(r, "require_admin_or_podcast_owner", lambda *a, **k: None)
    monkeypatch.setattr(r.episode_service, "ensure_episode_document_from_job", lambda *a, **k: None)
    monkeypatch.setattr(r.rss_service, "update_episode_submission_state", lambda *a, **k: None)
    calls = []

    async def feed(*a, **k):
        calls.append("feed")
    monkeypatch.setattr(r.rss_service, "update_rss_feed", feed)
    monkeypatch.setattr(ms, "promote", lambda eid, client=None: calls.append("promote") or {"promoted": 2, "objects": ["audio/x.mp3", "thumbnails/x.jpg"]})
    monkeypatch.setattr(ms, "demote", lambda names, client=None: calls.append(("demote", list(names))) or len(names))
    return r, db, calls


def submit(r):
    from models.subscriber import PodcastSubmission
    return run(r.submit_podcast_to_rss(PodcastSubmission(podcast_id=EID, submit_to_rss=True), "k", None))


def test_publish_copies_the_files_before_the_feed_write(submit_env):
    r, db, calls = submit_env
    assert submit(r)["submitted_to_rss"] is True
    assert calls == ["promote", "feed"]


def test_publish_stops_with_nothing_written_if_the_copy_fails(submit_env, monkeypatch):
    r, db, calls = submit_env
    monkeypatch.setattr(ms, "promote", lambda eid, client=None: (_ for _ in ()).throw(ms.MediaError("mismatch")))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        submit(r)
    assert e.value.status_code == 500 and "feed" not in calls
    db.collection.return_value.document.return_value.update.assert_not_called()


def test_publish_takes_the_public_copies_back_out_if_the_feed_write_fails(submit_env, monkeypatch):
    r, db, calls = submit_env

    async def broken(*a, **k):
        raise RuntimeError("feed write failed")
    monkeypatch.setattr(r.rss_service, "update_rss_feed", broken)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        submit(r)
    assert calls == ["promote", ("demote", ["audio/x.mp3", "thumbnails/x.jpg"])]


# ------------------------------------------------------------------ admin endpoints
def test_publish_site_and_media_links_endpoints(monkeypatch):
    from endpoints.admin import routes as a
    doc = MagicMock()
    doc.exists = True
    db = MagicMock()
    db.collection.return_value.document.return_value.get.return_value = doc
    monkeypatch.setattr(a, "db", db)
    monkeypatch.setattr(ms, "promote", lambda eid, client=None: {"promoted": 3, "already_public": False, "objects": ["audio/x.mp3"]})
    monkeypatch.setattr(ms, "signed_links", lambda eid, expires, client=None, signer=None: {"episode_id": eid, "links": {"audio": "signed://x"}, "hours": expires.total_seconds() / 3600})
    out = run(a.publish_episode_to_site(EID, True))
    assert out == {"episode_id": EID, "visible_on_web": True, "promoted_files": 3, "already_public": False}
    sent = db.collection.return_value.document.return_value.set.call_args[0][0]
    assert sent["visible_on_web"] is True and sent["media_state"] == "public"
    assert run(a.episode_media_links(EID, 2, True))["hours"] == 2
    doc.exists = False
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        run(a.episode_media_links(EID, 1, True))
    assert e.value.status_code == 404


# ------------------------------------------------------------------ static guards on the live code
ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE = [p for d in ("services", "endpoints", "mcp_server", "utils") for p in (ROOT / d).rglob("*.py")] + [ROOT / "main.py", ROOT / "elevenlabs_voice_service.py", ROOT / "email_service.py"]


def test_no_live_code_makes_a_file_public_or_reads_a_blob_public_url():
    bad = [f"{p.relative_to(ROOT)}:{m.start()}" for p in LIVE for m in re.finditer(r"\.make_public\(|(?<!media_store)\.public_url\b", p.read_text(encoding="utf-8"))]
    assert not bad, bad


def test_media_writers_write_only_to_the_private_bucket():
    for rel in ("elevenlabs_voice_service.py", "services/podcast_generation_service.py", "main.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert 'bucket("regal-scholar-453620-r7-podcast-storage")' not in src and ".bucket(self.bucket_name)" not in src, rel
        assert "media_store.PRIVATE_BUCKET" in src, rel
    video = (ROOT / "services/video_generation_service.py").read_text(encoding="utf-8")
    assert "bucket(media_store.PRIVATE_BUCKET).blob(video_blob_name)" in video


def test_the_ready_email_signs_its_link_and_says_how_long_it_lasts():
    gen = (ROOT / "services/podcast_generation_service.py").read_text(encoding="utf-8")
    assert "media_store.signed_audio_link" in gen and "link_valid_days=link_valid_days" in gen
    assert "link_valid_days" in (ROOT / "email_service.py").read_text(encoding="utf-8")


def test_dead_player_map_entries_are_gone():
    for rel in ("api/episodes/index.js", "api/episodes/[episodeId].js"):
        s = (ROOT.parent / rel).read_text(encoding="utf-8")
        assert "ever-math-260001" not in s and "ever-math-260002" not in s and "ever-bio-260010" in s
