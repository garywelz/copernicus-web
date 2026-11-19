"""The podcast feed's episode text must reach podcast apps as text they render, never as markup they show to the listener.

Found on 2026-11-19 in the live feed: 8 of the 40 items carried their HTML escaped inside CDATA, so Spotify showed "<p style=...>", "<h2>References</h2>"
and "<h3>Peer-reviewed papers</h3>" as text, and episode 1's plain description showed "Re s &gt; 7/8". Cause: the writer put the literal string
"<![CDATA[...]]>" into each field, the XML library escaped all of it, and a string replacement restored only the CDATA markers.

These tests run the real writer (`RSSService.update_rss_feed`) against a fake bucket, parse the feed it uploads the way a podcast app does, and look
at what the app gets. They also cover the one-time rebuild of the items already in the feed, and that the website keeps its own styled HTML."""
import asyncio
import re
import xml.etree.ElementTree as ET

import pytest

from feed_text import ALLOWED_TAGS, feed_html, feed_plain, sanitize_html
from services import rss_service as rs
from services.rss_service import RSS_NAMESPACES, RSSService, rebuild_feed_text, text_kind

NS = {"itunes": RSS_NAMESPACES["itunes"], "content": RSS_NAMESPACES["content"]}
CURATED = ("OpenAI posted a proof that every Dirichlet L-function is zero-free for Re s > 7/8, & more.\n\n"
           "## References\n\n### Peer-reviewed papers\n\n- **Author A** (2001). *A paper title*. https://doi.org/10.1/abc\n"
           "- [A preprint](https://arxiv.org/abs/2601.00001) [preprint, not peer reviewed]\n\n"
           "### Company releases\n\n- OpenAI (2026). The Quasi-Riemann Hypothesis. https://github.com/openai/math [company release, not peer reviewed]\n\n"
           "## Hashtags\n#math #ai")
FEED = ('<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:itunes="{itunes}" xmlns:content="{content}" xmlns:podcast="{podcast}" '
        'xmlns:media="{media}"><channel><title>CopernicusAI</title>{items}</channel></rss>')


def feed_xml(items=""):
    return FEED.format(items=items, **RSS_NAMESPACES).encode("utf-8")


class Blob:
    def __init__(self, store, name):
        self.store, self.name, self.generation, self.size = store, name, 1, 10

    def exists(self):
        return self.name in self.store

    def reload(self):
        pass

    def download_as_bytes(self):
        return self.store[self.name]

    def upload_from_string(self, data, content_type=None, if_generation_match=None):
        self.store[self.name] = data


class Client:
    store = {}

    def bucket(self, name):
        return type("Bucket", (), {"blob": lambda _s, n: Blob(Client.store, n)})()


@pytest.fixture
def feed(monkeypatch):
    Client.store = {rs.RSS_FEED_BLOB_NAME: feed_xml()}
    monkeypatch.setattr(rs.storage, "Client", Client)
    return Client.store


def publish(description, canonical="ever-math-260099", title="Is the quasi-Riemann hypothesis true? A & B"):
    job = {"result": {"description": description, "canonical_filename": canonical, "audio_url": "https://x/a.mp3", "title": title,
                      "thumbnail_url": "https://x/t.png", "transcript_url": "https://x/t.txt", "generated_at": "2026-11-19T12:00:00"},
           "request": {"category": "Mathematics"}}
    loop = asyncio.new_event_loop()          # its own loop: asyncio.run() would leave the thread with no current loop, which later tests rely on
    try:
        loop.run_until_complete(RSSService.update_rss_feed(job, None, True, "GW"))
    finally:
        loop.close()
    root = ET.fromstring(Client.store[rs.RSS_FEED_BLOB_NAME])
    return root.find("./channel/item")


def tags_in(html):
    return {t.lower() for t in re.findall(r"<\s*([a-zA-Z][a-zA-Z0-9]*)", html)}


# ---- what a podcast app gets from a newly published item ---------------------------------------------------------------------------------------------------
def test_a_published_items_html_reaches_the_app_as_real_markup_never_escaped(feed):
    item = publish(CURATED)
    html = item.find("content:encoded", NS).text
    assert text_kind(html, html=True) == "html", html[:200]                                     # decoded once, it is markup the app renders
    assert not re.search(r"&lt;\s*/?\s*[a-zA-Z]", html) and "<![CDATA[" not in Client.store[rs.RSS_FEED_BLOB_NAME].decode()   # no escaped tag
    assert "Re s &gt; 7/8, &amp; more." in html                                       # HTML's own escaping of > and &, which the app decodes
    assert "<p>" in html and "<li>" in html


def test_the_html_carries_only_the_tags_podcast_apps_accept_and_no_styles(feed):
    html = publish(CURATED).find("content:encoded", NS).text
    assert tags_in(html) <= set(ALLOWED_TAGS), tags_in(html) - set(ALLOWED_TAGS)
    assert not re.search(r"<h[1-6]", html) and "style=" not in html
    assert "<p><strong>References</strong></p>" in html and "<p><strong>Peer-reviewed papers</strong></p>" in html     # headings as bold paragraphs


def test_the_description_and_summary_are_plain_text_with_every_character_as_written(feed):
    item = publish(CURATED)
    desc, summary = item.findtext("description"), item.find("itunes:summary", NS).text
    for text in (desc, summary):
        assert text_kind(text) == "plain", text[:200]
        assert "##" not in text and "**" not in text and "<" not in text and "&gt;" not in text and "&amp;" not in text
    assert "Re s > 7/8, & more." in desc                                                # not "&gt;" or "&amp;"
    assert "\nReferences\n" in desc and "\n- Author A (2001). A paper title. https://doi.org/10.1/abc" in desc
    assert "A preprint (https://arxiv.org/abs/2601.00001) [preprint, not peer reviewed]" in desc


def test_a_title_with_an_ampersand_reaches_the_app_as_written(feed):
    assert publish(CURATED).findtext("title") == "Is the quasi-Riemann hypothesis true? A & B"


def test_republishing_leaves_every_other_item_readable(feed):
    publish(CURATED, "ever-math-260098")
    publish(CURATED, "ever-math-260099")                                             # the writer re-serializes the whole feed each time
    for item in ET.fromstring(Client.store[rs.RSS_FEED_BLOB_NAME]).findall("./channel/item"):
        assert text_kind(item.find("content:encoded", NS).text, html=True) == "html" and text_kind(item.findtext("description")) == "plain"


# ---- the one-time rebuild of the items already in the feed -------------------------------------------------------------------------------------------------
BROKEN = ('<item><title><![CDATA[Old episode]]></title><link>https://www.copernicusai.fyi/episodes/ever-bio-250001</link>'
          '<description><![CDATA[Narrative &gt; text.]]></description><itunes:summary><![CDATA[Narrative]]></itunes:summary>'
          '<content:encoded><![CDATA[&lt;h2&gt;Episode Overview&lt;/h2&gt; &lt;p style="margin-bottom: 1rem;"&gt;Narrative&lt;/p&gt;]]></content:encoded>'
          '<enclosure url="https://x/old.mp3" type="audio/mpeg" length="1234" /><guid isPermaLink="false">ever-bio-250001</guid>'
          '<pubDate>Mon, 06 Oct 2025 12:00:00 +0000</pubDate><itunes:image href="https://x/old.png" /><itunes:duration>10:21</itunes:duration>'
          '<podcast:person role="contributor">GW</podcast:person></item>')
GOOD = ('<item><title>Untouched</title><guid isPermaLink="false">ever-bio-250002</guid><description>Plain.</description>'
        '<content:encoded>&lt;p&gt;Plain.&lt;/p&gt;</content:encoded><pubDate>Sun, 05 Oct 2025 12:00:00 +0000</pubDate></item>')
JOB = {"result": {"description": "Narrative > text.\n\n## References\n\n- A source. https://e.org/1", "canonical_filename": "ever-bio-250001",
                  "audio_url": "https://x/old.mp3", "title": "Old episode", "thumbnail_url": "https://x/old.png"}, "request": {"category": "Biology"}}


def fields(item):
    return {k: (item.find(k, NS).attrib if item.find(k, NS) is not None and item.find(k, NS).attrib else item.findtext(k, namespaces=NS))
            for k in ("link", "enclosure", "guid", "pubDate", "itunes:image", "itunes:duration", "itunes:summary")}


def test_the_rebuild_turns_an_escaped_item_into_markup_and_plain_text_and_touches_nothing_else():
    before = ET.fromstring(feed_xml(BROKEN + GOOD))
    assert text_kind(before.find("./channel/item/content:encoded", NS).text, html=True) == "escaped"            # what is live today
    assert text_kind(before.find("./channel/item/description").text) == "escaped"
    new, report = rebuild_feed_text(feed_xml(BROKEN + GOOD), lambda g, title: JOB if g == "ever-bio-250001" else None)
    item, good = ET.fromstring(new).findall("./channel/item")
    assert text_kind(item.find("content:encoded", NS).text, html=True) == "html" and "style=" not in item.find("content:encoded", NS).text
    assert item.findtext("description").startswith("Narrative > text.") and text_kind(item.findtext("description")) == "plain"
    old_item = before.findall("./channel/item")[0]
    for k in ("link", "enclosure", "guid", "pubDate", "itunes:image", "itunes:duration"):
        assert fields(item)[k] == fields(old_item)[k], k
    assert item.find("{%s}person" % RSS_NAMESPACES["podcast"]).text == "GW" and "Creator: GW" in item.find("content:encoded", NS).text
    assert ET.tostring(good) == ET.tostring(ET.fromstring(feed_xml(BROKEN + GOOD)).findall("./channel/item")[1])     # no job: unchanged
    assert [r["guid"] for r in report if r["rebuilt"]] == ["ever-bio-250001"] and report[1]["reason"] == "no job record"
    assert report[0]["before"]["encoded"] == "escaped" and report[0]["after"] == {"description": "plain", "summary": "plain", "encoded": "html"}


def test_an_item_the_pre_publish_check_refuses_is_left_as_it_is_and_reported_and_the_others_are_rebuilt(monkeypatch):
    real = rs.validate_description_before_publish

    def refuse_one(text):
        if "Narrative > text." in text:
            raise ValueError("malformed PubMed URL")
        return real(text)
    monkeypatch.setattr(rs, "validate_description_before_publish", refuse_one)
    other = BROKEN.replace("ever-bio-250001", "ever-bio-250003")
    job3 = {**JOB, "result": {**JOB["result"], "description": "Another narrative.", "canonical_filename": "ever-bio-250003"}}
    new, report = rebuild_feed_text(feed_xml(BROKEN + other), lambda g, title: JOB if g == "ever-bio-250001" else job3)
    first, second = ET.fromstring(new).findall("./channel/item")
    assert ET.tostring(first) == ET.tostring(ET.fromstring(feed_xml(BROKEN)).find("./channel/item"))           # refused: byte for byte as it was
    assert report[0]["rebuilt"] is False and "malformed PubMed URL" in report[0]["reason"]
    assert report[1]["rebuilt"] is True and text_kind(second.find("content:encoded", NS).text, html=True) == "html"


def test_an_item_whose_job_cannot_be_chosen_by_title_is_left_as_it_is():
    """Two episodes can share a file name (ever-phys-250032, 2026-11-19): the lookup is given the item's title, and its reason is reported."""
    seen = []

    def lookup(guid, title):
        seen.append((guid, title))
        return "2 job(s) with this file name, 0 with this item's title: not chosen"
    new, report = rebuild_feed_text(feed_xml(BROKEN), lookup)
    assert seen == [("ever-bio-250001", "Old episode")]
    assert ET.tostring(ET.fromstring(new).find("./channel/item")) == ET.tostring(ET.fromstring(feed_xml(BROKEN)).find("./channel/item"))
    assert report[0]["rebuilt"] is False and "not chosen" in report[0]["reason"]


# ---- the pieces ---------------------------------------------------------------------------------------------------------------------------------------------
def test_the_sanitizer_keeps_only_safe_markup():
    out = sanitize_html('<h2 style="x">Refs</h2><p style="a">One <b>two</b> <i>three</i> <span>four</span></p>'
                        '<a href="javascript:alert(1)">bad</a><a href="https://e.org" onclick="x()">good</a><script>alert(1)</script><br/>')
    assert out == ('<p><strong>Refs</strong></p><p>One <strong>two</strong> <em>three</em> four</p>bad<a href="https://e.org">good</a><br>')


def test_plain_text_has_no_markup_left():
    md = "# Title\n\nSome **bold**, *italic* and `code`; [link](https://e.org) and [https://e.org/x](https://e.org/x).\n\n* item one\n+ item two"
    assert feed_plain(md) == "Title\n\nSome bold, italic and code; link (https://e.org) and https://e.org/x.\n\n- item one\n- item two"


def test_feed_html_of_markdown_with_raw_html_in_it_is_still_safe():
    html = feed_html('Text <img src=x onerror=alert(1)> <div style="color:red">styled</div>')
    assert "<img" not in html and "<div" not in html and "style=" not in html and "styled" in html


# ---- the website is not changed --------------------------------------------------------------------------------------------------------------------------
def test_the_website_keeps_its_own_styled_rendering():
    from services.episode_service import EpisodeService
    page = EpisodeService._markdown_to_html("Intro.\n\n## References\n\n- a [x](https://e.org)")
    assert '<p style="margin-bottom: 1rem; line-height: 1.7;">' in page and "<h2>References</h2>" in page
