"""Stored text files must say they are UTF-8 (ever-math-260007: the transcript bytes were correct UTF-8 but its Content-Type was a bare
'text/markdown', so readers decoded the em dashes as Windows-1252 and showed 'â€”'). Offline: reads the source and runs the real upload helpers."""
import asyncio
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

def run(coro):
    loop = asyncio.new_event_loop()      # not asyncio.run: that leaves no current loop and breaks later tests that call get_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


ROOT = Path(__file__).resolve().parents[2]
FILES = [ROOT / "main.py", ROOT / "services" / "podcast_generation_service.py", ROOT / "services" / "rss_service.py"]


def test_every_text_upload_to_storage_declares_utf8():
    problems = []
    for f in FILES:
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"upload_from_string\((?:[^()]|\([^()]*\))*?content_type=\"((?:text/|application/(?:rss\+xml|json))[^\"]*)\"", src, re.S):
            if m.group(1).startswith("text/") and "charset=utf-8" not in m.group(1).lower():
                problems.append(f"{f.name}: {m.group(1)}")
    assert problems == []


def test_a_transcript_with_em_dashes_is_uploaded_as_utf8_text(monkeypatch):
    import sys
    try:
        import psutil  # noqa: F401
    except ImportError:
        monkeypatch.setitem(sys.modules, "psutil", MagicMock())
    from google.cloud import storage
    from services.podcast_generation_service import PodcastGenerationService
    uploaded = {}

    class Blob:
        def __init__(self, name):
            self.name = name

        def upload_from_string(self, data, content_type=None, **kw):
            uploaded[self.name] = (data, content_type)

        def make_public(self):
            pass

    monkeypatch.setattr(storage, "Client", lambda *a, **k: SimpleNamespace(bucket=lambda n: SimpleNamespace(blob=lambda name: Blob(name))))
    svc = PodcastGenerationService.__new__(PodcastGenerationService)
    run(svc.generate_and_upload_transcript("MATILDA: A map — a graph — of proofs.", "ever-math-000001"))
    data, ctype = next(v for k, v in uploaded.items() if k.startswith("transcripts/"))
    assert ctype.lower() == "text/markdown; charset=utf-8"
    text = data if isinstance(data, str) else data.decode("utf-8")
    assert "—" in text and "â€”" not in text
