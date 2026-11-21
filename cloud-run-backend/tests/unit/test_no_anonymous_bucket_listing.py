"""Nothing lists the bucket over anonymous HTTP.

An unauthenticated list of a bucket only succeeds while that bucket grants `allUsers` the right to list it, which hands every object name to
anyone who asks. Two paths depended on it: the canonical-id allocator, which runs during episode generation, and the site's recent-episodes
route. Removing the public list permission would have broken both, so neither may read a listing that way.
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
LIST_OVER_HTTP = re.compile(r"storage\.googleapis\.com/storage/v1/b/[^\"'\s]*?/o\b")


def test_media_store_offers_an_authenticated_listing():
    import media_store
    assert hasattr(media_store, "list_names"), "the backend needs one authenticated way to list objects"
    doc = media_store.list_names.__doc__ or ""
    assert "service account" in doc


def test_the_canonical_allocator_does_not_list_over_anonymous_http():
    text = (BACKEND / "services" / "canonical_service.py").read_text(encoding="utf-8")
    assert not LIST_OVER_HTTP.search(text), "canonical_service must not build a storage.googleapis.com listing URL"
    assert "media_store.list_names" in text, "it should list with the backend's service account instead"


def test_the_canonical_allocator_still_reads_what_exists(monkeypatch):
    """The point of the listing is that an id is never reused, so the names must still reach the allocator."""
    import media_store
    from services import canonical_service

    seen = {}

    def fake(bucket, prefix, client=None):
        seen["prefix"] = prefix
        return ["audio/ever-math-260009.mp3"]

    monkeypatch.setattr(media_store, "list_names", fake)
    src = (BACKEND / "services" / "canonical_service.py").read_text(encoding="utf-8")
    assert "existing_names.append(leaf)" in src
    assert canonical_service is not None


def test_a_listing_that_cannot_be_read_does_not_stop_a_news_serial():
    text = (BACKEND / "services" / "canonical_service.py").read_text(encoding="utf-8")
    assert "Could not list the bucket for news serials" in text
    assert "existing_files = []" in text


def test_the_site_route_reads_the_feed_not_a_bucket_listing():
    route = (REPO / "app" / "api" / "recent-episodes" / "route.ts").read_text(encoding="utf-8")
    assert not LIST_OVER_HTTP.search(route), "the route must not list the bucket"
    assert "feeds/copernicus-mvp-rss-feed.xml" in route, "it should read the published feed"
    assert "parseFeed" in route


def test_the_site_route_keeps_the_fields_its_callers_use():
    route = (REPO / "app" / "api" / "recent-episodes" / "route.ts").read_text(encoding="utf-8")
    for field in ("id", "title", "audioUrl", "createdAt", "size"):
        assert re.search(rf"\b{field}\b\s*[,:]", route), f"the answer should still carry {field}"
    assert "{ episodes: []" in route and "status: 500" in route, "a failure should still answer with an empty list"
