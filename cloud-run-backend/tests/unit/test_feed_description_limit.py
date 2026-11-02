"""The feed's description: the 4,000-character limit is applied to the final text exactly as it is written into the feed (description, itunes:summary and
the HTML), reference URLs are bare text (no Markdown or HTML link markup), and no older item's text gets shorter.

Background: the builder used to add link markup to the references and only then apply the limit. For episode 1 (3,939 characters stored, about 4,389 with
the links) the limit kept the References whole and cut the narrative to "OpenAI post...". The item count (feed 39, public list 40) is not a builder
matter: ever-bio-260010 is a website-only episode by decision (entry 029 and earlier), so it is on the website and not in the feed."""
import json
import re
from pathlib import Path
from xml.etree.ElementTree import QName

import pytest

from content_fixes import limit_description_length
from reference_sections import render_for_feed
from services.rss_service import RSS_NAMESPACES, RSSService

FIX = Path(__file__).resolve().parents[1] / "fixtures"
EP1 = (FIX / "ever_math_260015_description.md").read_text(encoding="utf-8")
EP1_LINKED = (FIX / "ever_math_260015_description_linked.md").read_text(encoding="utf-8")
CORPUS = json.loads((FIX / "episodes_render.json").read_text(encoding="utf-8"))["episodes"]
SUMMARY_START = "OpenAI posted 722 AI-generated mathematics manuscripts at once."


def item(description, canonical="ever-math-260015"):
    pd = {"result": {"description": description, "canonical_filename": canonical, "audio_url": "https://x/a.mp3", "title": "T", "thumbnail_url": "https://x/t.png"},
          "request": {"category": "Mathematics"}}
    data = RSSService._build_rss_item_data(pd, None, None)
    return data, RSSService._create_rss_item_element(data, 1234)


def visible(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def ref_lines(text):
    section = text[text.index("## References"):text.index("## Hashtags")] if "## Hashtags" in text else text[text.index("## References"):]
    return [l for l in section.splitlines() if l.startswith("- ")]


# --- episode 1 ---------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("stored", [EP1, EP1_LINKED], ids=["stored 3,939 version", "stored link-wrapped 4,389 version"])
def test_episode_1s_feed_description_has_the_full_summary_and_every_reference_line_within_the_limit(stored):
    data, _ = item(stored)
    plain = data["description_plain"]
    assert len(plain) <= 4000
    assert plain.startswith(SUMMARY_START) and "that has not been peer reviewed." in plain.split("\n\n")[0]          # the whole summary paragraph
    assert plain.split("\n\n")[0] == EP1.split("\n\n")[0].replace("’", "'")
    expected = ref_lines(EP1)
    assert len(expected) == 13                                                                                  # 4 releases + 8 commentary + 1 withdrawn
    for line in ref_lines(plain):
        assert line.startswith("- ")
    assert len(ref_lines(plain)) == 13
    assert plain.count("commentary: reported, not a source for any claim that a result is true") == 8
    for url in re.findall(r"https://\S+", EP1):
        assert url in plain


def test_episode_1s_text_is_the_same_in_the_description_the_summary_and_the_html():
    data, el = item(EP1)
    assert data["summary"].startswith(SUMMARY_START) and "post..." not in data["summary"]
    assert SUMMARY_START in visible(data["description_html"]) and len(visible(data["description_html"])) <= 4000 + 200      # transcript line excluded below
    html_text = visible(re.sub(r"<p><a href=.*?</a></p>", "", data["description_html"], flags=re.S))
    assert len(html_text) <= 4000
    desc = el.find("description").text
    assert SUMMARY_START in desc and "OpenAI post..." not in desc


def test_reference_urls_are_bare_text_in_every_form_of_the_feed_text():
    data, el = item(EP1_LINKED)
    assert "](" not in data["description_plain"] and "<a href" not in data["description_html"].replace('<a href="https://x', "")
    assert data["description_plain"].count("https://zenodo.org/records/22737751") == 1                 # once, not "url (url)"
    assert "[https://" not in data["description_plain"]


def test_the_limit_is_applied_to_the_text_after_formatting_never_before():
    """A description whose References are short as stored but longer once each line is given its address: the narrative must not be cut to nothing."""
    body = "A narrative paragraph that goes on for a while. " * 30
    refs = "\n".join(f"- Author {n} (2020). Title number {n}. arXiv:2604.{24000 + n}" for n in range(12))
    description = f"{body.strip()}\n\n## References\n\n{refs}\n\n## Hashtags\n#a"
    data, _ = item(description, "ever-math-260010")
    assert len(data["description_plain"]) <= 4000 and data["description_plain"].startswith("A narrative paragraph")
    assert len(ref_lines(data["description_plain"])) == 12


# --- every older item: no text gets shorter -------------------------------------------------------------------------------------------------------------
def legacy_plain(description, canonical):
    """The feed text as the builder produced it before this change (links added first, the limit applied after)."""
    from content_fixes import limit_description_length as limit
    md = RSSService._strip_legacy_tagline(description)
    from services.rss_service import EPISODE_BASE_URL
    md = render_for_feed(md, f"{EPISODE_BASE_URL}/{canonical}")
    md = RSSService._make_reference_links_clickable(md)
    md = RSSService._clean_description_for_spotify(md)
    md = limit(md, 4000)
    plain = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 (\2)", md)
    return re.sub(r"<[^>]+>", "", plain).strip()


def narrative(text):
    return text.split("## References")[0].strip()


def dedup(text):
    """`url (url)` -> `url`: the one change this fix makes to an older item's plain text (a reference whose label already holds its address)."""
    return re.sub(r"(https?://\S+) \(\1\)", r"\1", text)


def test_no_older_items_feed_text_gets_shorter_and_any_that_change_are_listed():
    changed = []
    for canonical, ep in CORPUS.items():
        old = legacy_plain(ep["description_markdown"], canonical)
        new = item(ep["description_markdown"], canonical)[0]["description_plain"]
        assert len(narrative(new)) >= len(narrative(old)), (canonical, "the narrative got shorter")
        assert len(ref_lines(new)) >= len(ref_lines(old)), (canonical, "a reference line was lost")
        assert "](" not in new and "<a href" not in new
        if new != old:
            changed.append((canonical, len(old), len(new)))
            # the only allowed differences: duplicated addresses removed, or more of the narrative kept because the limit now sees the shorter text
            assert new == dedup(old) or len(narrative(new)) > len(narrative(old)), (canonical, "changed in some other way")
    print("changed items:", changed)


def test_the_stored_old_style_items_have_no_link_markup_in_the_feed():
    for canonical, ep in CORPUS.items():
        new, _ = item(ep["description_markdown"], canonical)
        assert "](" not in new["description_plain"] and "<a href" not in re.sub(r'<a href="https://x[^>]*>', "", new["description_html"])
