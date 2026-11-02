"""An item's image in the feed is the square artwork when the episode has one, otherwise the thumbnail, as before."""
from xml.etree.ElementTree import QName

from services.rss_service import RSSService, RSS_NAMESPACES

THUMB = "https://storage.googleapis.com/b/thumbnails/ever-math-260010-thumb.jpg"
ART = "https://storage.googleapis.com/b/episode-images/ever-math-260015-artwork-3000.png"


def item(result_extra=None):
    result = {"description": "Text.", "canonical_filename": "ever-math-260010", "audio_url": "https://x/a.mp3", "title": "T", "thumbnail_url": THUMB}
    result.update(result_extra or {})
    data = RSSService._build_rss_item_data({"result": result, "request": {"category": "Mathematics"}}, None, None)
    return data, RSSService._create_rss_item_element(data, 1234)


def images(el):
    it, md = RSS_NAMESPACES["itunes"], RSS_NAMESPACES["media"]
    return (el.find(f"{{{it}}}image").get("href"), el.find(f"{{{md}}}thumbnail").get("url"), el.find(f"{{{md}}}content").get("url"))


def test_an_item_with_square_artwork_uses_it_in_every_image_tag():
    data, el = item({"artwork_url": ART})
    assert data["thumbnail_url"] == THUMB and data["image_url"] == ART
    assert images(el) == (ART, ART, ART)


def test_an_item_without_artwork_is_exactly_as_before():
    data, el = item()
    assert data["image_url"] == THUMB and images(el) == (THUMB, THUMB, THUMB)
    data2, el2 = item({"artwork_url": None})
    assert images(el2) == (THUMB, THUMB, THUMB) and data2["thumbnail_url"] == THUMB


def test_an_item_with_neither_uses_the_default_artwork():
    from config.constants import DEFAULT_ARTWORK_URL
    data, el = item({"thumbnail_url": None})
    assert images(el) == (DEFAULT_ARTWORK_URL,) * 3
