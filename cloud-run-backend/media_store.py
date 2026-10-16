"""Where an episode's media files live (private-episode access control, stage 2, 2026-10-15).

The public bucket grants `allUsers` read on every object, so a file there is public by definition. Generation therefore writes every media file
(audio, transcript, thumbnail, episode images, video, animation packs, scratch segments) to the PRIVATE bucket. The episode record keeps the URL fields
in their eventual public form (https://storage.googleapis.com/<public bucket>/<name>), so promoting an episode changes no record and the feed needs no edit.
Publishing calls `promote()`, which copies the episode's files private -> public and verifies every copy before anything is flagged or written to the
feed. Review of a private episode uses short-lived signed links (`signed_links`). Both bucket names are constants, not environment variables, so a
deploy still changes only the image.
"""
from datetime import timedelta
from typing import Any, Dict, List, Optional

PUBLIC_BUCKET = "regal-scholar-453620-r7-podcast-storage"
PRIVATE_BUCKET = "regal-scholar-453620-r7-private-media"
MAX_SIGNED_DAYS = 7  # the V4 signing maximum


class MediaError(RuntimeError):
    """A media step failed; the caller must stop (publishing is fail-closed)."""


def public_url(name: str) -> str:
    """The public address a file will have once its episode is promoted (stored on the record from the start)."""
    return f"https://storage.googleapis.com/{PUBLIC_BUCKET}/{name}"


def episode_prefixes(episode_id: str) -> List[str]:
    """Object-name prefixes that belong to one episode, in either bucket."""
    return [f"audio/{episode_id}.", f"transcripts/{episode_id}-", f"thumbnails/{episode_id}-", f"episode-images/{episode_id}-",
            f"animations/{episode_id}/", f"generated/videos/{episode_id}."]


def _client(client: Any = None):
    if client is not None:
        return client
    from google.cloud import storage
    return storage.Client()


def list_objects(bucket_name: str, episode_id: str, client: Any = None) -> List[Any]:
    c = _client(client)
    found: Dict[str, Any] = {}
    for prefix in episode_prefixes(episode_id):
        for blob in c.bucket(bucket_name).list_blobs(prefix=prefix):
            found[blob.name] = blob
    return [found[n] for n in sorted(found)]


def promote(episode_id: str, client: Any = None) -> Dict[str, Any]:
    """Copy an episode's files from the private bucket to the public bucket and verify every copy (MD5, CRC32C and size).

    Fail closed: on any mismatch the copies made in this call are removed and MediaError is raised, so the caller writes nothing. An episode with no private
    files whose audio is already public (older episodes) is reported as already public; an episode with no audio anywhere is an error.
    """
    c = _client(client)
    private = c.bucket(PRIVATE_BUCKET)
    public = c.bucket(PUBLIC_BUCKET)
    blobs = list_objects(PRIVATE_BUCKET, episode_id, c)
    audio = f"audio/{episode_id}.mp3"
    if not blobs:
        if public.get_blob(audio) is not None:
            return {"episode_id": episode_id, "promoted": 0, "already_public": True, "objects": []}
        raise MediaError(f"no media found for {episode_id} in either bucket")
    if audio not in {b.name for b in blobs} and public.get_blob(audio) is None:
        raise MediaError(f"{episode_id} has no audio file")
    made: List[str] = []
    try:
        for src in blobs:
            private.copy_blob(src, public, new_name=src.name)
            made.append(src.name)
            dst = public.get_blob(src.name)
            if dst is None or not (dst.md5_hash == src.md5_hash and dst.crc32c == src.crc32c and dst.size == src.size):
                raise MediaError(f"checksum mismatch after copying {src.name}")
    except Exception as exc:
        for name in made:
            try:
                public.blob(name).delete()
            except Exception:
                pass
        if isinstance(exc, MediaError):
            raise
        raise MediaError(f"promotion of {episode_id} failed: {exc}") from exc
    return {"episode_id": episode_id, "promoted": len(made), "already_public": False, "objects": made}


def demote(names: List[str], client: Any = None) -> int:
    """Remove files that `promote()` just copied to the public bucket (used when a publish fails after the copy). Returns how many were removed."""
    public = _client(client).bucket(PUBLIC_BUCKET)
    removed = 0
    for name in names:
        try:
            public.blob(name).delete()
            removed += 1
        except Exception:
            pass
    return removed


def _signing_kwargs() -> Dict[str, Any]:
    """Arguments that let `generate_signed_url` sign without a key file: on Cloud Run the service account signs through the IAM API for itself
    (it holds roles/iam.serviceAccountTokenCreator on itself only); a key-file credential signs directly."""
    import google.auth
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if isinstance(creds, service_account.Credentials):
        return {"credentials": creds}
    creds.refresh(Request())
    return {"service_account_email": getattr(creds, "service_account_email", None), "access_token": creds.token}


def signed_url(bucket_name: str, name: str, expires: timedelta, client: Any = None, signer: Any = None) -> str:
    """A V4 signed GET link for one object (at most 7 days)."""
    if expires > timedelta(days=MAX_SIGNED_DAYS):
        expires = timedelta(days=MAX_SIGNED_DAYS)
    blob = _client(client).bucket(bucket_name).blob(name)
    return blob.generate_signed_url(version="v4", expiration=expires, method="GET", **(signer() if signer else _signing_kwargs()))


def signed_links(episode_id: str, expires: timedelta, client: Any = None, signer: Any = None) -> Dict[str, Any]:
    """Links to every file of an episode: signed links for files in the private bucket, public addresses for files already public."""
    c = _client(client)
    links: Dict[str, str] = {}
    state = "public"
    for blob in list_objects(PRIVATE_BUCKET, episode_id, c):
        links[blob.name] = signed_url(PRIVATE_BUCKET, blob.name, expires, c, signer)
        state = "private"
    for blob in list_objects(PUBLIC_BUCKET, episode_id, c):
        links.setdefault(blob.name, public_url(blob.name))
    return {"episode_id": episode_id, "media_state": state, "expires_in_seconds": int(min(expires, timedelta(days=MAX_SIGNED_DAYS)).total_seconds()), "links": links}


def signed_audio_link(episode_id: str, days: int = MAX_SIGNED_DAYS, client: Any = None, signer: Any = None) -> Optional[str]:
    """A signed link to the episode's audio for the ready email (None if the file is not in the private bucket)."""
    name = f"audio/{episode_id}.mp3"
    c = _client(client)
    if c.bucket(PRIVATE_BUCKET).get_blob(name) is None:
        return None
    return signed_url(PRIVATE_BUCKET, name, timedelta(days=days), c, signer)
