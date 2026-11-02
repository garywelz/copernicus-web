"""Publishing never rewrites a stored description with link markup (it lengthened episode 1's from 3,939 to about 4,389 characters, past the 4,000-character
limit). Links are added only when the page renders the description; the feed carries bare addresses (#170)."""
from pathlib import Path

from services.episode_service import EpisodeService
from tests.unit.test_feed_description_limit import EP1, EP1_LINKED, SUMMARY_START, item

NL = chr(10)
FIX = Path(__file__).resolve().parents[1] / "fixtures"
FEED_TEXT = (FIX / "ever_math_260015_feed_description.txt").read_text(encoding="utf-8")


def prepare(description):
    result = {"title": "722 papers overnight: OpenAI's mathematics release", "description": description, "canonical_filename": "ever-math-260015",
              "audio_url": "https://x/a.mp3", "thumbnail_url": "https://x/t.png"}
    return EpisodeService._prepare_episode_document("job-1", "sub-1", {"topic": "t", "category": "Mathematics"}, result, {}, {})


def test_publishing_episode_1s_record_leaves_its_stored_description_byte_identical():
    doc = prepare(EP1)
    assert doc["description_markdown"] == EP1 and len(doc["description_markdown"]) == 3939
    assert "](" not in doc["description_markdown"] and "<a href" not in doc["description_html"]


def test_publishing_twice_changes_nothing():
    once = prepare(EP1)["description_markdown"]
    assert prepare(once)["description_markdown"] == once == EP1


def test_a_short_description_with_references_and_a_link_is_stored_exactly_as_given():
    text = "Intro."+NL*2+"## References"+NL*2+"- A (2020). T. arXiv:2604.24797"+NL+"- B (2021). U. [https://example.org/b](https://example.org/b)"+NL*2+"## Hashtags"+NL+"#a"
    assert prepare(text)["description_markdown"] == text           # no identifier is turned into a link, no link is wrapped again


def test_the_feed_text_for_episode_1_equals_the_text_fixed_in_170():
    data, _ = item(EP1)
    assert data["description_plain"] == FEED_TEXT and len(FEED_TEXT) <= 4000 and FEED_TEXT.startswith(SUMMARY_START)
    assert prepare(EP1)["description_markdown"] == EP1          # the record is what the feed builder started from
