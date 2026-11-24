"""Two cover-art faults from 2026-11-23, and the images nothing reads.

The series template never cuts a word: a title it cannot set is refused, the episode falls back to the channel's cover, and nobody sees it
until the feed is read. It happened twice in two days and both were fixed by hand with the same two moves:

    ever-math-260018  "OpenAI's counterexample to Kaplansky's direct-finiteness conjecture"
                      -> "Kaplansky's direct-finiteness conjecture" / "OpenAI's counterexample"
    ever-math-260020  "OpenAI says it has proved the Mezard-Parisi formula for diluted spin glasses. Has it?"
                      -> "The Mezard-Parisi formula for diluted spin glasses" / "OpenAI says it has a proof"

Separately, the extra DALL-E "episode images" cost money per episode and nothing reads them: they are not the feed's artwork, not the
thumbnail, and no page or record points at them. Two were made for ever-math-260020 and changed nothing a listener sees, so the step is
switched off and the code kept.
"""
import re
from pathlib import Path

import pytest
import series_thumbnail as st
import thumbnail_title as tt

BACKEND = Path(__file__).resolve().parents[2]
SERVICE = (BACKEND / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
CONSTANTS = (BACKEND / "config" / "constants.py").read_text(encoding="utf-8")

T197 = "OpenAI's counterexample to Kaplansky's direct-finiteness conjecture"
T221 = "OpenAI says it has proved the Mézard–Parisi formula for diluted spin glasses. Has it?"


# --- the two real titles ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("title", [T197, T221])
def test_the_full_title_cannot_be_set(title):
    """The cause, held in place: if these ever fit, the derivation below is not what is protecting the cover."""
    with pytest.raises(st.TitleDoesNotFit):
        st.render_16x9(title)


@pytest.mark.parametrize("title", [T197, T221])
def test_a_form_of_each_real_title_is_found_and_renders(title):
    got = tt.derive(title)
    assert got is not None, title
    head, sub = got
    assert head and len(st.render_16x9(head, subtitle=sub)) > 1000
    assert len(st.render_square(head, subtitle=sub)) > 1000


def test_the_derived_form_uses_only_the_episodes_own_words():
    """Nothing is invented. Every word of the cover comes from the title, apart from the small joining words of a claim attribution."""
    for title in (T197, T221):
        head, sub = tt.derive(title)
        said = {w.lower().strip(".,;:’'“”\"") for w in (head + " " + sub).split()}
        source = {w.lower().strip(".,;:’'“”\"") for w in title.split()}
        allowed = {"it", "has", "a", "proof", "so", "the", "says", "said"}
        extra = said - source - allowed
        assert not extra, (title, extra)


def test_221_keeps_the_manuscript_name_on_the_cover():
    head, sub = tt.derive(T221)
    assert "zard" in head and "Parisi" in head, (head, sub)
    assert "OpenAI" in sub, "who claims it belongs underneath"


def test_197_keeps_the_conjecture_on_the_cover():
    head, sub = tt.derive(T197)
    assert "Kaplansky" in head, (head, sub)


# --- the order of the attempts ------------------------------------------------------------------------------------------------------
def test_a_title_that_already_fits_is_left_exactly_as_it_is():
    short = "Spin glasses"
    assert tt.derive(short) == (short, "")
    assert tt.candidates(short)[0] == (short, "")


def test_the_colon_split_is_tried_before_anything_is_moved():
    pairs = tt.candidates("A zero-free half-plane past 7/8: OpenAI's quasi-Riemann hypothesis")
    assert ("A zero-free half-plane past 7/8", "OpenAI's quasi-Riemann hypothesis") in pairs
    whole = [p for p in pairs if p[1] == ""]
    assert pairs.index(whole[0]) < pairs.index(("A zero-free half-plane past 7/8", "OpenAI's quasi-Riemann hypothesis"))


def test_a_trailing_aside_is_dropped_before_the_title_is_cut():
    pairs = tt.candidates("Can an AI write a working genome? Has it?")
    assert ("Can an AI write a working genome?", "") in pairs


def test_no_word_of_the_title_is_thrown_away_when_the_head_is_shortened():
    for head, sub in tt.candidates("one two three four five six seven eight nine ten"):
        if sub:
            assert len((head + " " + sub).split()) >= 9, (head, sub)


def test_nothing_that_fits_returns_none_rather_than_a_cut_word():
    assert tt.fits("anything", renders=lambda t, s: (_ for _ in ()).throw(st.TitleDoesNotFit("no"))) is None


# --- how the service uses it --------------------------------------------------------------------------------------------------------
def test_the_service_derives_a_title_before_falling_back():
    block = SERVICE.split("async def series_thumbnail_upload", 1)[1].split("async def generate_and_upload_thumbnail", 1)[0]
    assert "import thumbnail_title as tt" in block
    assert "asyncio.to_thread(tt.derive, title)" in block, "off the event loop: it renders images"
    assert "record.update({\"thumbnail_title\": derived[0], \"thumbnail_subtitle\": derived[1]})" in block, \
        "what was used is recorded on the episode"


def test_a_cover_that_cannot_be_drawn_is_an_error_naming_the_episode():
    # the LAST of the two handlers: the inner one re-raises, the outer one falls back and must say so
    block = SERVICE.rsplit("except series_thumbnail.TitleDoesNotFit", 1)[1][:900]
    assert "structured_logger.error" in block, "an error, not a warning"
    assert "canonical_filename=canonical_filename" in block and "episode_title=title" in block
    assert "DEFAULT_ARTWORK_URL" in block, "the episode is still made"


# --- the episode images ------------------------------------------------------------------------------------------------------------
def test_the_episode_images_are_off_by_default():
    assert 'EPISODE_IMAGES_ENABLED = os.getenv("EPISODE_IMAGES_ENABLED", "")' in CONSTANTS
    import config.constants as cc
    assert cc.EPISODE_IMAGES_ENABLED is False


def test_with_the_setting_off_no_image_request_is_made():
    """The guard returns before the key is fetched and before any request is built."""
    block = SERVICE.split("async def generate_episode_images", 1)[1].split("try:", 1)[0]
    assert "if not EPISODE_IMAGES_ENABLED:" in block and "return []" in block
    guard_at = SERVICE.index("if not EPISODE_IMAGES_ENABLED:")
    for later in ("get_openai_api_key_from_secret_manager()", "https://api.openai.com/v1/images/generations"):
        nxt = SERVICE.find(later, SERVICE.index("async def generate_episode_images"))
        assert nxt > guard_at, f"{later} must come after the guard"


def test_the_step_and_the_pinned_model_are_kept():
    assert "https://api.openai.com/v1/images/generations" in SERVICE, "the code stays"
    assert "EPISODE_IMAGE_MODEL" in SERVICE and "gpt-image-2-2026-04-21" in CONSTANTS, "and the pin with it"


def test_turning_it_on_needs_no_deploy():
    assert re.search(r'EPISODE_IMAGES_ENABLED = os\.getenv\([^)]*\)', CONSTANTS)
