"""The real length of an episode's audio, for the feed's itunes:duration (the feed used to show the top of the requested range, "10:00",
whatever the audio length was). Reads the MP3 itself; returns None when it cannot, and the caller falls back to the old rule."""
import io
from typing import Optional


def mp3_seconds(data: Optional[bytes]) -> Optional[float]:
    """Length in seconds of a whole MP3 file held in memory (exact for constant and variable bitrate), or None if unreadable."""
    if not data:
        return None
    try:
        from mutagen.mp3 import MP3
        length = MP3(io.BytesIO(data)).info.length
    except Exception:
        return None
    return float(length) if length and length > 0 else None


def format_itunes_duration(seconds: Optional[float]) -> Optional[str]:
    """M:SS under an hour, H:MM:SS from an hour up (the forms the existing feed items use); None for no usable length."""
    if seconds is None or seconds <= 0:
        return None
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
