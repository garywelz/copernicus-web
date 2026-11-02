"""The series thumbnail drawn by code (series_thumbnail.py) and its use in curated mode: the generic image prompts are never used, the run record says
where the thumbnail came from, and a failure falls back to the default series artwork, not to a generic picture."""
import asyncio
import io
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import series_thumbnail as st
from tests.unit.test_curated_generation import svc

TITLE = "722 papers overnight: OpenAI's mathematics release"
ROOT = Path(__file__).resolve().parents[2]


def px(png):
    return Image.open(io.BytesIO(png)).convert("RGB")


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_the_font_and_its_licence_are_shipped():
    assert os.path.getsize(st.FONT_PATH) > 100_000 and (ROOT / "assets" / "fonts" / "Inter-OFL.txt").exists()


def test_the_16x9_thumbnail_has_the_template_size_panels_and_a_clear_corner():
    im = px(st.render_16x9(TITLE))
    assert im.size == (1280, 720)
    assert im.getpixel((5, 5)) == st.WHITE and im.getpixel((1000, 5)) == st.INK                      # white title panel, ink motif panel
    corner = im.crop((1060, 630, 1280, 720))                                                           # the video timestamp area
    assert set(corner.getdata()) == {st.INK}
    assert (st.GOLD in set(im.crop((900, 60, 1180, 600)).getdata()))   # the one accent is in the motif slot


def test_the_title_is_drawn_in_ink_on_the_white_panel_only():
    im = px(st.render_16x9(TITLE))
    left = im.crop((0, 0, 800, 720))
    assert sum(1 for p in left.getdata() if p == st.INK) > 20_000                                      # the title is large
    right_text_zone = im.crop((800, 640, 1280, 720))
    assert set(right_text_zone.getdata()) == {st.INK}


def test_the_square_artwork_is_3000_square_with_the_split_turned_horizontal():
    im = px(st.render_square(TITLE))
    assert im.size == (3000, 3000) and im.getpixel((10, 10)) == st.WHITE and im.getpixel((10, 2990)) == st.INK


def test_a_title_splits_at_the_colon_and_keeps_at_most_five_words_in_three_lines():
    assert st.title_parts(TITLE) == (["722", "papers", "overnight"], "OpenAI's mathematics release")
    lines, sub = st.title_parts("One two three four five six seven: the subtitle")
    assert sub == "the subtitle" and len(lines) == 3 and len(" ".join(lines).split()) == 5
    assert st.title_parts("") == (["CopernicusAI"], "")


def test_a_very_long_word_is_shrunk_to_fit_not_cut_off():
    im = px(st.render_16x9("Electroencephalographically: sub"))
    assert set(im.crop((775, 100, 796, 700)).getdata()) == {st.WHITE}          # nothing runs into the gap before the dark panel


# --- the job -----------------------------------------------------------------------------------------------------------------------------------------
class FakeBlob:
    def __init__(self, store, name):
        self.store, self.name = store, name

    def upload_from_string(self, data, content_type=None):
        self.store[self.name] = (len(data), content_type)


class FakeStorage:
    store = {}

    class Client:
        def bucket(self, name):
            assert name == svc.media_store.PRIVATE_BUCKET
            return SimpleNamespace(blob=lambda n: FakeBlob(FakeStorage.store, n))


def service(monkeypatch):
    import google.cloud.storage as gcs
    FakeStorage.store = {}
    monkeypatch.setattr(gcs, "Client", FakeStorage.Client)
    monkeypatch.setattr(svc, "dalle_thumbnail_attempts", lambda *a: pytest.fail("the generic image prompts must not be used in curated mode"))
    return svc.PodcastGenerationService()


def test_curated_mode_uses_the_series_template_in_the_private_bucket_and_records_it(monkeypatch):
    s, rec = service(monkeypatch), {}
    url = run(s.generate_and_upload_thumbnail("722 papers overnight: OpenAI's mathematics release", "a topic", "ever-math-260015", curated=True, record=rec))
    assert url == svc.media_store.public_url("thumbnails/ever-math-260015-thumb.png")
    assert set(FakeStorage.store) == {"thumbnails/ever-math-260015-thumb.png", "episode-images/ever-math-260015-artwork-3000.png"}
    assert all(ct == "image/png" for _, ct in FakeStorage.store.values())
    assert rec == {"thumbnail_source": "series_template", "artwork_url": svc.media_store.public_url("episode-images/ever-math-260015-artwork-3000.png")}


def test_a_failure_in_curated_mode_gives_the_default_artwork_and_says_so(monkeypatch):
    s, rec = service(monkeypatch), {}
    monkeypatch.setattr(st, "render_16x9", lambda t: (_ for _ in ()).throw(RuntimeError("boom")))
    url = run(s.generate_and_upload_thumbnail("A title", "t", "x-1", curated=True, record=rec))
    assert url == svc.DEFAULT_ARTWORK_URL and rec == {"thumbnail_source": "default_artwork", "thumbnail_error": "RuntimeError"} and FakeStorage.store == {}


def test_the_ordinary_mode_is_unchanged_and_still_uses_the_image_prompts(monkeypatch):
    s = service(monkeypatch)
    called = []
    monkeypatch.setattr(svc, "dalle_thumbnail_attempts", lambda *a: called.append(a) or [])

    async def no_key():
        return None
    monkeypatch.setattr(s, "get_openai_api_key_from_secret_manager", no_key)

    async def fallback(cf, topic):
        return "fallback-url"
    monkeypatch.setattr(s, "generate_fallback_thumbnail", fallback)
    assert run(s.generate_and_upload_thumbnail("t", "topic", "x-2")) == "fallback-url"          # no key: the ordinary fallback, as before
    assert FakeStorage.store == {}


def test_the_job_passes_curated_mode_and_stores_the_thumbnail_record():
    text = (ROOT / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert "curated=curated_run is not None," in text and "record=thumbnail_record," in text
    assert "**({'thumbnail': dict(thumbnail_record)} if curated_run is not None else {})" in text
    ep = (ROOT / "services" / "episode_service.py").read_text(encoding="utf-8")
    assert '"artwork_url"' in ep and '"artwork_blob"' in ep
