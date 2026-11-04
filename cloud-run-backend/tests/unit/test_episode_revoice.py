"""Re-voice a private episode from its stored script (episode_revoice.py). Offline: fake storage, fake Firestore and a fake voice service."""
import asyncio
import base64
import hashlib
from datetime import datetime, timezone

import pytest

import episode_revoice as er
import media_store

EID = "ever-compsci-990002"
JOB = "job-1"
SCRIPT = "HOST: Welcome to CopernicusAI. Today ETH and k-SAT.\nEXPERT: Yes.\n"
SHA = hashlib.sha256(SCRIPT.strip().encode("utf-8")).hexdigest()
NOW = datetime(2026, 11, 4, 18, 30, 5, tzinfo=timezone.utc)
OLD, NEW = b"OLD-AUDIO-" * 100, b"NEW-AUDIO-" * 100


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- fakes ------------------------------------------------------------------------------------------------------------------------------
class Blob:
    def __init__(self, bucket, name):
        self.bucket, self.name = bucket, name
        self.generation = bucket.store[name][1]           # a snapshot, as a real blob's metadata is when it is fetched

    @property
    def data(self):
        return self.bucket.store[self.name][0]

    @property
    def md5_hash(self):
        return base64.b64encode(hashlib.md5(self.data).digest()).decode()

    def download_as_bytes(self):
        return self.data

    def delete(self):
        self.bucket.store.pop(self.name)


class Bucket:
    def __init__(self, name):
        self.name, self.store, self.counter = name, {}, 0

    def put(self, name, data):
        self.counter += 1
        self.store[name] = (data, self.counter)

    def get_blob(self, name):
        return Blob(self, name) if name in self.store else None

    def copy_blob(self, src, dest_bucket, new_name, if_generation_match=None):
        existing = dest_bucket.store.get(new_name)
        if if_generation_match == 0 and existing is not None:
            raise RuntimeError("412 destination exists")
        if if_generation_match not in (None, 0) and (existing is None or existing[1] != if_generation_match):
            raise RuntimeError("412 destination generation changed")
        dest_bucket.put(new_name, src.data)
        return Blob(dest_bucket, new_name)


class Client:
    def __init__(self):
        self.buckets = {}

    def bucket(self, name):
        return self.buckets.setdefault(name, Bucket(name))


class Doc:
    def __init__(self, store, key):
        self.store, self.key = store, key

    @property
    def exists(self):
        return self.key in self.store

    def get(self):
        return self

    def to_dict(self):
        return dict(self.store[self.key]) if self.key in self.store else None

    def update(self, fields):
        self.store[self.key].update(fields)


class Coll:
    def __init__(self, store):
        self.store = store

    def document(self, key):
        return Doc(self.store, key)


class Db:
    def __init__(self):
        self.data = {"episodes": {}, "podcast_jobs": {}}

    def collection(self, name):
        return Coll(self.data[name])


class Voice:
    """Writes NEW to the temporary name, as the real service does, and counts characters like the real one."""

    def __init__(self, client, fail=None, failed_segments=0, audio=NEW, boom=False, race=False):
        self.client, self.fail, self.failed_segments, self.audio, self.boom, self.race, self.calls = client, fail, failed_segments, audio, boom, race, []

    async def generate_multi_voice_audio_with_bumpers(self, script, job_id, canonical_filename, intro_path, outro_path, host_voice_id=None,
                                                      expert_voice_id=None, tts_usage=None):
        self.calls.append(dict(script=script, job_id=job_id, canonical=canonical_filename, host=host_voice_id, expert=expert_voice_id))
        if self.boom:
            raise RuntimeError("elevenlabs down")
        private = self.client.bucket(media_store.PRIVATE_BUCKET)
        private.put(f"audio/{canonical_filename}.mp3", self.audio)
        tts_usage.sent("voiceA", "hello there")
        for _ in range(self.failed_segments):
            tts_usage.sent("voiceB", "lost")
            tts_usage.failed("lost")
        if self.race:                                         # somebody replaces the current audio while the new one is being made
            private.put(f"audio/{EID}.mp3", b"SOMEONE-ELSE")
        return "https://example.org/x.mp3"


def seconds(data):
    return {OLD: 600.0, NEW: 620.0}.get(data) if data in (OLD, NEW) else (float(len(data)) / 10 if data else None)


def world(published=False, visible=False, script=SCRIPT, with_job=True, with_audio=True, voices=("hv", "ev")):
    db, client = Db(), Client()
    db.data["episodes"][EID] = {"episode_id": EID, "canonical_filename": EID, "job_id": JOB, "submitted_to_rss": published, "visible_on_web": visible,
                                "description_markdown": "D", "thumbnail_url": "T"}
    if with_job:
        db.data["podcast_jobs"][JOB] = {"result": {"script": script}, "request": {"host_voice_id": voices[0], "expert_voice_id": voices[1]}}
    private = client.bucket(media_store.PRIVATE_BUCKET)
    if with_audio:
        private.put(f"audio/{EID}.mp3", OLD)
    return db, client, private


def revoice(db, client, voice, sha=SHA):
    return run(er.revoice_private_episode(EID, sha, db=db, client=client, voice_service=voice, seconds_of=seconds, now=NOW))


# --- the happy path ----------------------------------------------------------------------------------------------------------------------
def test_a_private_episode_is_re_voiced_and_the_old_audio_is_kept():
    db, client, private = world()
    voice = Voice(client)
    out = revoice(db, client, voice)
    assert private.store[f"audio/{EID}.mp3"][0] == NEW                                               # replaced
    prev = f"audio/previous/{EID}_20261104T183005Z.mp3"
    assert private.store[prev][0] == OLD and out["previous_audio"] == prev                            # kept, verified
    assert f"audio/{EID}-revoice-tmp.mp3" not in private.store                                         # the temporary file is gone
    assert voice.calls == [dict(script=SCRIPT.strip(), job_id=JOB, canonical=f"{EID}-revoice-tmp", host="hv", expert="ev")]
    assert out["old_seconds"] == 600.0 and out["new_seconds"] == 620.0 and out["script_sha256"] == SHA
    assert out["tts_characters"] == len("hello there") and out["tts_failed_segments"] == 0


def test_only_the_audio_fields_of_the_episode_record_change():
    db, client, _ = world()
    before = dict(db.data["episodes"][EID])
    revoice(db, client, Voice(client))
    after = db.data["episodes"][EID]
    changed = {k for k in after if after[k] != before.get(k)}
    assert changed == {"audio_seconds", "audio_revoiced_at", "audio_previous", "audio_revoice_script_sha256", "audio_revoice_tts"}
    assert after["audio_seconds"] == 620.0 and after["description_markdown"] == "D" and after["thumbnail_url"] == "T"


# --- refusals: nothing changes -----------------------------------------------------------------------------------------------------------
def _assert_untouched(db, client, before_episode, status, exc):
    assert exc.value.status == status
    private = client.bucket(media_store.PRIVATE_BUCKET)
    assert private.store[f"audio/{EID}.mp3"][0] in (OLD, b"SOMEONE-ELSE") and db.data["episodes"][EID] == before_episode
    assert f"audio/{EID}-revoice-tmp.mp3" not in private.store


@pytest.mark.parametrize("published,visible", [(True, False), (False, True), (True, True)])
def test_a_published_episode_is_refused(published, visible):
    db, client, _ = world(published=published, visible=visible)
    voice, before = Voice(client), dict(db.data["episodes"][EID])
    with pytest.raises(er.RevoiceError) as e:
        revoice(db, client, voice)
    _assert_untouched(db, client, before, 409, e)
    assert voice.calls == []


def test_a_script_that_is_not_the_one_named_is_refused():
    db, client, _ = world()
    voice, before = Voice(client), dict(db.data["episodes"][EID])
    with pytest.raises(er.RevoiceError) as e:
        revoice(db, client, voice, sha="0" * 64)
    _assert_untouched(db, client, before, 409, e)
    assert voice.calls == [] and SHA in e.value.message and "script" not in e.value.message.replace("script's", "")


def test_missing_episode_job_script_or_audio_are_refused():
    for kw, status in (({"with_job": False}, 409), ({"script": "  "}, 409), ({"with_audio": False}, 409)):
        db, client, _ = world(**kw)
        with pytest.raises(er.RevoiceError) as e:
            revoice(db, client, Voice(client))
        assert e.value.status == status
    with pytest.raises(er.RevoiceError) as e:
        run(er.revoice_private_episode("nope", SHA, db=Db(), client=Client(), voice_service=None, seconds_of=seconds, now=NOW))
    assert e.value.status == 404


# --- failures leave the current audio exactly as it was ----------------------------------------------------------------------------------
def test_a_failed_text_to_speech_request_means_nothing_is_replaced():
    db, client, private = world()
    before = dict(db.data["episodes"][EID])
    with pytest.raises(er.RevoiceError) as e:
        revoice(db, client, Voice(client, failed_segments=1))
    _assert_untouched(db, client, before, 409, e)
    assert private.store[f"audio/{EID}.mp3"][0] == OLD


def test_an_error_from_the_voice_service_means_nothing_is_replaced():
    db, client, private = world()
    before = dict(db.data["episodes"][EID])
    with pytest.raises(er.RevoiceError) as e:
        revoice(db, client, Voice(client, boom=True))
    _assert_untouched(db, client, before, 502, e)


def test_a_new_audio_much_shorter_or_unreadable_is_not_accepted():
    for audio in (b"X" * 50, b""):                                       # 5 seconds against 600; unreadable (zero bytes)
        db, client, private = world()
        before = dict(db.data["episodes"][EID])
        with pytest.raises(er.RevoiceError) as e:
            revoice(db, client, Voice(client, audio=audio))
        _assert_untouched(db, client, before, 409, e)


def test_the_current_audio_changing_during_the_run_stops_the_replacement():
    db, client, private = world()
    before = dict(db.data["episodes"][EID])
    with pytest.raises(er.RevoiceError) as e:
        revoice(db, client, Voice(client, race=True))
    assert e.value.status == 409 and private.store[f"audio/{EID}.mp3"][0] == b"SOMEONE-ELSE"      # not overwritten by the new audio
    assert db.data["episodes"][EID] == before and f"audio/{EID}-revoice-tmp.mp3" not in private.store


def test_an_existing_previous_copy_or_leftover_temporary_file_is_never_overwritten():
    db, client, private = world()
    private.put(f"audio/previous/{EID}_20261104T183005Z.mp3", b"KEEP")
    with pytest.raises(er.RevoiceError):
        revoice(db, client, Voice(client))
    assert private.store[f"audio/previous/{EID}_20261104T183005Z.mp3"][0] == b"KEEP"
    db, client, private = world()
    private.put(f"audio/{EID}-revoice-tmp.mp3", b"LEFTOVER")
    with pytest.raises(er.RevoiceError):
        revoice(db, client, Voice(client))
    assert private.store[f"audio/{EID}.mp3"][0] == OLD and private.store[f"audio/{EID}-revoice-tmp.mp3"][0] == b"LEFTOVER"


def test_the_hash_helper_ignores_surrounding_whitespace():
    assert er.script_sha256("  " + SCRIPT + "\n\n") == SHA
