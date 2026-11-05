"""The series thumbnail never cuts a word (series_thumbnail.py): a title is shrunk and wrapped to fit, or the thumbnail step is refused with a plain message
(the episode still generates, with the default artwork and nothing written). A producer may also give the words to draw (`thumbnail_title`,
`thumbnail_subtitle`) on a curated generate or check-script request. Offline: storage is faked."""
import io
from pathlib import Path

import pytest
from PIL import Image

import series_thumbnail as st
from tests.unit.test_series_thumbnail import FakeStorage, run, service, svc

ROOT = Path(__file__).resolve().parents[2]
ETH_TITLE = "The Exponential Time Hypothesis is false?"
OVER_LONG = "A very long and rambling title that goes on and on about the hypothesis and its many consequences for everyone"


def px(png):
    return Image.open(io.BytesIO(png)).convert("RGB")


# --- the layout --------------------------------------------------------------------------------------------------------------------------------------
def test_an_explicit_subtitle_leaves_the_title_whole_and_a_colon_in_it_alone():
    assert st.title_parts("Is ETH false?", "The Exponential Time Hypothesis") == (["Is", "ETH", "false?"], "The Exponential Time Hypothesis")
    lines, sub = st.title_parts("Part 1: the claim", "A subtitle")
    assert " ".join(lines).split() == ["Part", "1:", "the", "claim"] and sub == "A subtitle"
    assert st.title_parts("Is ETH false?", "") == (["Is", "ETH", "false?"], "")


@pytest.mark.parametrize("kind", ["16x9", "square"])
def test_the_eth_title_is_wrapped_and_shrunk_to_fit_with_every_word_kept(kind):
    placed = st._title_lines(st.title_parts(ETH_TITLE)[0], kind, 1)
    assert " ".join(t for t, _, _ in placed).split() == ETH_TITLE.split()                                  # six words, in order, none cut
    scale = 3000 / 1280 if kind == "square" else 1.0
    assert len(placed) <= 4 and all(size >= st.MIN_TITLE_SIZE * scale for _, size, _ in placed)           # legible
    assert len({round(size) for _, size, _ in placed}) == 1                                              # one size for a wrapped title
    _, size, baseline = placed[-1]
    assert baseline + 0.25 * size <= (600 if kind == "16x9" else 1620)                                    # clear of the subtitle


def test_the_eth_title_draws_on_both_images_with_the_template_intact():
    thumb = px(st.render_16x9(ETH_TITLE, subtitle="The Exponential Time Hypothesis"))
    assert thumb.size == (1280, 720) and set(thumb.crop((775, 100, 796, 700)).getdata()) == {st.WHITE}      # nothing runs into the gap before the dark panel
    assert set(thumb.crop((1060, 630, 1280, 720)).getdata()) == {st.INK}                                   # the timestamp corner stays clear
    assert sum(1 for p in thumb.crop((0, 100, 800, 600)).getdata() if p == st.INK) > 15_000                # the title is drawn, large
    sq = px(st.render_square(ETH_TITLE, subtitle="The Exponential Time Hypothesis"))
    assert sq.size == (3000, 3000) and sq.getpixel((10, 10)) == st.WHITE and sq.getpixel((10, 2990)) == st.INK


def test_a_short_title_keeps_the_classic_layout_unchanged():
    placed = st._title_lines(st.title_parts("722 papers overnight")[0], "16x9", 1)
    assert [round(size) for _, size, _ in placed] == [176, 116, 116] and [round(b) for _, _, b in placed] == [300, 440, 560]


def test_fewer_lines_are_preferred_when_the_font_is_nearly_as_large():
    placed = st._title_lines(st.title_parts(ETH_TITLE)[0], "16x9", 1)
    assert [t for t, _, _ in placed] == ["The Exponential", "Time Hypothesis", "is false?"]                   # not four lines with "Time" and "Hypothesis" apart


# --- refusals ------------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("draw", [st.render_16x9, st.render_square])
def test_a_title_that_cannot_be_set_legibly_is_refused_not_cut(draw):
    for title in ("Electroencephalographically" * 2, " ".join(["Hypothesis"] * 40)):
        with pytest.raises(st.TitleDoesNotFit) as e:
            draw(title)
        assert "without cutting words" in str(e.value) and "thumbnail_title" in str(e.value)


def test_the_over_long_title_is_refused_on_the_thumbnail():
    with pytest.raises(st.TitleDoesNotFit) as e:
        st.render_16x9(OVER_LONG)
    assert OVER_LONG in str(e.value) and "20 words" in str(e.value)


def test_a_subtitle_too_long_to_read_is_refused_too():
    with pytest.raises(st.TitleDoesNotFit) as e:
        st.render_16x9("Is ETH false?", subtitle="word " * 80)
    assert "subtitle" in str(e.value) and "without cutting words" in str(e.value)


# --- the job and the requests ------------------------------------------------------------------------------------------------------------------------
def test_an_over_long_title_fails_the_thumbnail_step_with_a_clear_message_and_writes_nothing(monkeypatch):
    s, rec = service(monkeypatch), {}
    url = run(s.generate_and_upload_thumbnail(OVER_LONG, "t", "x-3", curated=True, record=rec))
    assert url == svc.DEFAULT_ARTWORK_URL and FakeStorage.store == {}                                      # the episode goes on with the default artwork; no file written
    assert rec["thumbnail_source"] == "default_artwork" and rec["thumbnail_error"] == "TitleDoesNotFit"
    assert "too long to set legibly" in rec["thumbnail_error_message"] and "thumbnail_title" in rec["thumbnail_error_message"]


def spy(monkeypatch):
    seen = []
    real16, realsq = st.render_16x9, st.render_square
    monkeypatch.setattr(st, "render_16x9", lambda *a, **k: seen.append((a, k)) or real16(*a, **k))
    monkeypatch.setattr(st, "render_square", lambda *a, **k: realsq(*a, **k))
    return seen


def test_a_given_thumbnail_title_and_subtitle_are_drawn_instead_of_a_title_that_would_not_fit(monkeypatch):
    s, rec = service(monkeypatch), {}
    seen = spy(monkeypatch)
    url = run(s.generate_and_upload_thumbnail(OVER_LONG, "t", "x-4", curated=True, record=rec,
                                              thumbnail_title="Is ETH false?", thumbnail_subtitle="The Exponential Time Hypothesis"))
    assert url == svc.media_store.public_url("thumbnails/x-4-thumb.png")
    assert set(FakeStorage.store) == {"thumbnails/x-4-thumb.png", "episode-images/x-4-artwork-3000.png"}
    assert seen == [(("Is ETH false?",), {"subtitle": "The Exponential Time Hypothesis"})] and rec["thumbnail_source"] == "series_template"
    assert "thumbnail_error_message" not in rec


def test_a_given_thumbnail_title_alone_is_drawn_whole_with_no_subtitle(monkeypatch):
    s, rec = service(monkeypatch), {}
    seen = spy(monkeypatch)
    run(s.generate_and_upload_thumbnail("Episode title: with a colon", "t", "x-5", curated=True, record=rec, thumbnail_title="Is ETH false?"))
    assert seen == [(("Is ETH false?",), {"subtitle": ""})]


def test_without_a_given_title_the_episode_title_is_drawn_exactly_as_before(monkeypatch):
    s, rec = service(monkeypatch), {}
    seen = spy(monkeypatch)
    run(s.generate_and_upload_thumbnail("722 papers overnight: OpenAI's mathematics release", "t", "x-6", curated=True, record=rec))
    assert seen == [(("722 papers overnight: OpenAI's mathematics release",), {})]


def test_the_two_fields_are_optional_on_both_curated_requests_and_ride_on_the_podcast_request():
    from models.curated import CheckSuppliedScript, GenerateCuratedEpisode
    from models.podcast import PodcastRequest
    g = GenerateCuratedEpisode(list_id="l")
    c = CheckSuppliedScript(list_id="l", script="HOST: x", title="t")
    assert g.thumbnail_title is None and g.thumbnail_subtitle is None and c.thumbnail_title is None and c.thumbnail_subtitle is None
    g2 = GenerateCuratedEpisode(list_id="l", thumbnail_title="Is ETH false?", thumbnail_subtitle="The Exponential Time Hypothesis")
    r = PodcastRequest(topic="t", thumbnail_title=g2.thumbnail_title, thumbnail_subtitle=g2.thumbnail_subtitle)
    assert r.model_dump()["thumbnail_title"] == "Is ETH false?" and PodcastRequest(topic="t").thumbnail_title is None


def test_both_curated_routes_pass_the_fields_and_report_a_thumbnail_warning():
    text = (ROOT / "endpoints" / "curated" / "routes.py").read_text(encoding="utf-8")
    assert text.count("thumbnail_title=body.thumbnail_title, thumbnail_subtitle=body.thumbnail_subtitle") == 2        # generate and check-script, not the dry run
    assert text.count('["thumbnail_warning"] =') == 2 and text.count('out["thumbnail_warning"] =') == 1 and text.count('answer["thumbnail_warning"] =') == 1
    job = (ROOT / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    assert 'thumbnail_title=getattr(request, "thumbnail_title", None),' in job and 'thumbnail_subtitle=getattr(request, "thumbnail_subtitle", None),' in job
