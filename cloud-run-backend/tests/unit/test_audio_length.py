"""The feed's itunes:duration is the real audio length (fallback to the old rule only if the audio cannot be read). Offline: a short MP3
is generated with ffmpeg-free means by repeating one valid frame."""
import pytest

from audio_length import format_itunes_duration, mp3_seconds
from services.rss_service import RSSService

# one MPEG-1 Layer III frame, 128 kbps, 44.1 kHz, no padding: header FFFB9000, 417 bytes, 1152 samples = 0.026122 s
FRAME = bytes([0xFF, 0xFB, 0x90, 0x00]) + b"\x00" * 413


def mp3(frames):
    return FRAME * frames


def test_format_uses_the_feeds_existing_forms():
    assert format_itunes_duration(413.4) == "6:53"
    assert format_itunes_duration(275) == "4:35"
    assert format_itunes_duration(59.6) == "1:00"
    assert format_itunes_duration(1302) == "21:42"
    assert format_itunes_duration(3725) == "1:02:05"
    assert format_itunes_duration(0) is None and format_itunes_duration(None) is None and format_itunes_duration(-3) is None


def test_mp3_seconds_reads_the_length():
    assert mp3_seconds(mp3(3829)) == pytest.approx(100.0, abs=0.5)      # 3829 frames x 0.026122 s


@pytest.mark.parametrize("bad", [None, b"", b"not an mp3 at all" * 50, b"\x00" * 1000])
def test_mp3_seconds_is_none_when_unreadable(bad):
    assert mp3_seconds(bad) is None


def test_item_duration_is_the_real_length_not_the_requested_range():
    assert RSSService._format_duration("5-10 minutes", 413.4) == "6:53"
    assert RSSService._format_duration("5-10 minutes", None) == "10:00"          # old rule, only when the audio could not be read
    assert RSSService._format_duration("5-10 minutes", 0) == "10:00"
    assert RSSService._format_duration(None, None) == "10:00"
    assert RSSService._format_duration("7 minutes") == "07:00"


def test_build_item_data_passes_the_length_through():
    pd = {"result": {"description": "Text.", "canonical_filename": "ever-math-260010", "audio_url": "https://x/a.mp3", "title": "T", "duration": "5-10 minutes"},
          "request": {"category": "Mathematics"}}
    assert RSSService._build_rss_item_data(pd, None, None, 413.4)["duration_display"] == "6:53"
    assert RSSService._build_rss_item_data(pd, None, None)["duration_display"] == "10:00"


def test_markdown_renders_in_the_item_html():
    """The package is now a requirement: the HTML description must be real HTML, not the paragraph fallback."""
    pd = {"result": {"description": "Intro.\n\n## References\n\n- A (2020). T. arXiv:2604.24797\n\n## Hashtags\n#a", "canonical_filename": "ever-math-260010",
                     "audio_url": "https://x/a.mp3", "title": "T"}, "request": {"category": "Mathematics"}}
    html = RSSService._build_rss_item_data(pd, None, None)["description_html"]
    assert "<ul" in html and 'href="https://arxiv.org/abs/2604.24797"' in html and "## References" not in html
