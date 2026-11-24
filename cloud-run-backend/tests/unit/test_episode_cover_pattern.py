"""A cover of its own for each episode, drawn from its canonical id.

Every episode carried the same series artwork: the same ink panel, the same eight gold nodes in the same places. In a podcast app's
grid, and in the site's own grid, one episode looked exactly like the next.

The panel now takes the colour of the episode's field - the same six colours the site uses - and the motif's grid and nodes are chosen
from a number fixed by the canonical id. No model and no API: the cover is drawn by the same Pillow code as before, so it costs nothing
and cannot fail on a network.

The title is not touched. It keeps its panel, its colours, its sizes and its refusal to cut a word, and the tests below hold the title
area identical across two episodes whose covers differ.
"""
import hashlib

import pytest
import series_thumbnail as st
from PIL import Image
import io

TITLE = "Kaplansky's direct-finiteness conjecture"
SUB = "OpenAI's counterexample"


def png(data):
    return Image.open(io.BytesIO(data)).convert("RGB")


# --- a cover of its own -------------------------------------------------------------------------------------------------------------
def test_two_episodes_get_different_covers():
    a = st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260018")
    b = st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260020")
    assert a != b, "the same title in the same field must still give two different covers"


def test_two_fields_get_different_covers():
    a = st.render_square(TITLE, subtitle=SUB, episode_id="ever-bio-260013")
    b = st.render_square(TITLE, subtitle=SUB, episode_id="ever-phys-250044")
    assert a != b


def test_one_episodes_cover_is_identical_across_renders():
    """Drawn again tomorrow, in another process, it must be the same image: a cover that moved would change the feed on every rebuild."""
    first = st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260018")
    for _ in range(4):
        assert st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260018") == first
    assert st.render_square(TITLE, subtitle=SUB, episode_id="ever-math-260018") == \
        st.render_square(TITLE, subtitle=SUB, episode_id="ever-math-260018")


def test_the_seed_does_not_depend_on_this_process():
    """Python's own hash() is salted per process, which would give an episode a new cover every time the service restarted."""
    want = int(hashlib.sha256(b"ever-math-260018").hexdigest()[:16], 16)
    assert st._seed("ever-math-260018") == want
    assert st._seed(None) is None


# --- the field's colour -------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("episode_id,expected", [
    ("ever-bio-260013", (0x14, 0x53, 0x2D)),
    ("ever-chem-250019", (0x5B, 0x21, 0x75)),
    ("ever-phys-250044", (0x0F, 0x3F, 0x73)),
    ("ever-math-260018", (0x8C, 0x1D, 0x18)),
    ("ever-compsci-250033", (0x33, 0x41, 0x55)),
    ("news-bio-28032025", (0x14, 0x53, 0x2D)),
])
def test_the_panel_takes_the_field_colour(episode_id, expected):
    assert st.field_colour(episode_id) == expected
    img = png(st.render_16x9(TITLE, subtitle=SUB, episode_id=episode_id))
    assert img.getpixel((1270, 700)) == expected, "the motif panel's own corner carries the field colour"


def test_an_id_of_another_shape_keeps_the_series_ink():
    for odd in ("", None, "something", "ever"):
        assert st.field_colour(odd) == st.INK


# --- the title is untouched ---------------------------------------------------------------------------------------------------------
def test_the_title_area_is_identical_for_two_different_covers():
    """Legibility cannot have changed if not one pixel of the title panel moved."""
    a = png(st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260018")).crop((0, 0, 800, 720))
    b = png(st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-bio-260013")).crop((0, 0, 800, 720))
    assert a.tobytes() == b.tobytes()


def test_the_square_title_area_is_identical_too():
    a = png(st.render_square(TITLE, subtitle=SUB, episode_id="ever-math-260018")).crop((0, 0, 3000, 1830))
    b = png(st.render_square(TITLE, subtitle=SUB, episode_id="ever-compsci-250033")).crop((0, 0, 3000, 1830))
    assert a.tobytes() == b.tobytes()


def test_a_title_that_does_not_fit_is_still_refused():
    with pytest.raises(st.TitleDoesNotFit):
        st.render_16x9("A very long and rambling title that goes on and on about the hypothesis and its many consequences for everyone",
                       episode_id="ever-math-260018")


def test_an_episode_without_an_id_draws_exactly_what_it_drew_before():
    """Every existing caller and every existing test passes no id, and must get the original artwork unchanged."""
    before = st.render_16x9(TITLE, subtitle=SUB)
    assert before == st.render_16x9(TITLE, subtitle=SUB, episode_id=None)
    assert before != st.render_16x9(TITLE, subtitle=SUB, episode_id="ever-math-260018")


# --- nothing is bought --------------------------------------------------------------------------------------------------------------
def test_the_cover_costs_nothing_and_needs_no_network():
    from pathlib import Path
    source = Path(st.__file__).read_text(encoding="utf-8")
    for forbidden in ("requests", "http", "openai", "api_key", "urllib"):
        assert forbidden not in source.lower().replace("https://", ""), forbidden


def test_the_service_passes_the_canonical_id_to_both_renders():
    from pathlib import Path
    service = (Path(st.__file__).resolve().parent / "services" / "podcast_generation_service.py").read_text(encoding="utf-8")
    block = service.split("async def series_thumbnail_upload", 1)[1].split("async def generate_and_upload_thumbnail", 1)[0]
    assert 'cover = {"episode_id": canonical_filename}' in block
    assert block.count("**cover") + block.count("dict(cover)") >= 3, "the given, derived and plain paths all carry it"
