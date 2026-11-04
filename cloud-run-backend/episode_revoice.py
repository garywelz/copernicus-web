"""Re-voice a PRIVATE episode from its stored script: new audio only, through the existing text-to-speech path.

Why it exists: the audio is made only inside the generation job, so a pronunciation fix (or a better voice setting) after a producer has listened meant
generating a whole new episode. This keeps the episode: the script, the description, the thumbnail and the artwork are not touched.

What it does, in this order, and what it refuses:
  * the episode must still be private (not in the feed, not on the website); a published episode's audio is never swapped here;
  * the script is the one stored on the episode's own job, and its SHA-256 must equal the one the caller names, so a re-voice is always of a script
    somebody has read;
  * the current audio is first copied, and the copy verified, to `audio/previous/<name>_<UTC time>.mp3` in the private bucket;
  * the new audio is made under a temporary name. The current audio is replaced only if no text-to-speech request failed, the length can be read and
    is within MAX_LENGTH_CHANGE of the old, and nothing changed the current file meanwhile (the replacement is conditional on its generation);
  * the episode record gets the new length, the time, the previous file's name and the text-to-speech counts. Nothing else on it changes.
A failure at any point leaves the current audio exactly as it was.

Nothing here talks to ElevenLabs, Firestore or storage by itself: the caller passes them in, so the tests run offline.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import media_store
from tts_usage import TtsUsage

MAX_LENGTH_CHANGE = 0.20                 # the new audio may differ from the old by at most this fraction of the old length
INTRO_PATH = "bumpers/copernicus-intro.mp3"
OUTRO_PATH = "bumpers/copernicus-outro.mp3"


class RevoiceError(Exception):
    """A refusal. `status` is the HTTP status the route answers with; nothing was changed."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def script_sha256(script: str) -> str:
    return hashlib.sha256((script or "").strip().encode("utf-8")).hexdigest()


def _stamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


async def revoice_private_episode(episode_id: str, expected_script_sha256: str, *, db: Any, client: Any, voice_service: Any,
                                  seconds_of: Callable[[Optional[bytes]], Optional[float]], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Make new audio for a private episode from its stored script. Returns a summary (counts, names and lengths; no text, no links)."""
    now = now or datetime.now(timezone.utc)
    ref = db.collection("episodes").document(episode_id)
    snap = ref.get()
    if not snap.exists:
        raise RevoiceError(404, "Episode not found")
    ep = snap.to_dict() or {}
    if ep.get("submitted_to_rss") or ep.get("visible_on_web"):
        raise RevoiceError(409, "This episode is published (in the feed or on the website). Only a private episode can be re-voiced here.")

    canonical = ep.get("canonical_filename") or episode_id
    name = f"audio/{canonical}.mp3"
    private = client.bucket(media_store.PRIVATE_BUCKET)
    current = private.get_blob(name)
    if current is None:
        raise RevoiceError(409, "The episode has no audio in the private bucket")
    current_generation = current.generation          # taken now: the replacement below is conditional on the file still being this one

    job_id = ep.get("job_id")
    job = (db.collection("podcast_jobs").document(job_id).get() if job_id else None)
    if job is None or not job.exists:
        raise RevoiceError(409, "The episode's job record is missing, so its script cannot be found")
    jd = job.to_dict() or {}
    script = ((jd.get("result") or {}).get("script") or "").strip()
    if not script:
        raise RevoiceError(409, "The episode's job record holds no script")
    actual = script_sha256(script)
    if actual != (expected_script_sha256 or "").strip().lower():
        raise RevoiceError(409, f"The stored script's SHA-256 is {actual}, not the one named; nothing was changed")
    request = jd.get("request") or {}

    previous_name = f"audio/previous/{canonical}_{_stamp(now)}.mp3"
    if private.get_blob(previous_name) is not None:
        raise RevoiceError(409, "A previous copy with this name already exists; try again in a second")
    copied = private.copy_blob(current, private, previous_name, if_generation_match=0)
    if getattr(copied, "md5_hash", None) != current.md5_hash:
        raise RevoiceError(500, "The copy of the current audio could not be verified; nothing was changed")
    old_seconds = seconds_of(current.download_as_bytes())

    temp_canonical = f"{canonical}-revoice-tmp"
    temp_name = f"audio/{temp_canonical}.mp3"
    if private.get_blob(temp_name) is not None:
        raise RevoiceError(409, "A temporary re-voice file already exists (an earlier run was interrupted); remove it first")

    usage = TtsUsage()
    try:
        await voice_service.generate_multi_voice_audio_with_bumpers(
            script, job_id, temp_canonical, intro_path=INTRO_PATH, outro_path=OUTRO_PATH,
            host_voice_id=request.get("host_voice_id"), expert_voice_id=request.get("expert_voice_id"), tts_usage=usage)
    except Exception as e:
        _discard(private, temp_name)
        raise RevoiceError(502, f"The text-to-speech step failed ({type(e).__name__}); the current audio is unchanged")

    fresh = private.get_blob(temp_name)
    try:
        if fresh is None:
            raise RevoiceError(502, "No new audio was written; the current audio is unchanged")
        if usage.failed_segments:
            raise RevoiceError(409, f"{usage.failed_segments} text-to-speech request(s) failed, so the new audio would be missing speech; the current audio is unchanged")
        new_bytes = fresh.download_as_bytes()
        new_seconds = seconds_of(new_bytes)
        if not new_seconds:
            raise RevoiceError(409, "The length of the new audio could not be read; the current audio is unchanged")
        if old_seconds and abs(new_seconds - old_seconds) > MAX_LENGTH_CHANGE * old_seconds:
            raise RevoiceError(409, f"The new audio is {new_seconds:.0f}s against {old_seconds:.0f}s: more than {int(MAX_LENGTH_CHANGE * 100)}% different; the current audio is unchanged")
        try:
            replaced = private.copy_blob(fresh, private, name, if_generation_match=current_generation)
        except Exception as e:
            raise RevoiceError(409, f"The current audio changed while the new audio was being made ({type(e).__name__}); nothing was replaced")
        if getattr(replaced, "md5_hash", None) != fresh.md5_hash:
            raise RevoiceError(500, "The replacement could not be verified")
    finally:
        _discard(private, temp_name)

    record = usage.as_record()
    ref.update({"audio_seconds": round(new_seconds, 1), "audio_revoiced_at": now.astimezone(timezone.utc).isoformat(),
                "audio_previous": previous_name, "audio_revoice_script_sha256": actual, "audio_revoice_tts": record})
    return {"episode_id": episode_id, "audio": name, "previous_audio": previous_name, "script_sha256": actual,
            "old_seconds": round(old_seconds, 1) if old_seconds else None, "new_seconds": round(new_seconds, 1), "bytes": len(new_bytes), **record}


def _discard(bucket: Any, name: str) -> None:
    try:
        blob = bucket.get_blob(name)
        if blob is not None:
            blob.delete()
    except Exception:
        pass
