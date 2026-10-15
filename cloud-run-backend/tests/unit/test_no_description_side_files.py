"""The description side files (descriptions/<id>.md in the public bucket) are no longer written, linked or returned (decision 2026-10-15:
nothing reads them, and 53 of 122 held a placeholder DOI or stock line). Offline."""
import asyncio
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVE = [p for d in ("services", "endpoints", "mcp_server", "utils") for p in (ROOT / d).rglob("*.py")] + [ROOT / "main.py"]


def test_no_live_code_writes_or_links_description_files():
    offenders = []
    for p in LIVE:
        if p.name == "routes.py" and p.parent.name == "public":
            continue                      # the one place that strips the old fields from what the API returns (tested below)
        src = p.read_text(encoding="utf-8")
        for m in re.finditer(r"upload_description_to_gcs|bucket\.blob\(f?[\"']descriptions/|[\"']description_url[\"']\s*:|description_blob", src):
            line = src[:m.start()].count("\n") + 1
            offenders.append(f"{p.relative_to(ROOT)}:{line}: {m.group(0)}")
    assert not offenders, offenders


def test_the_dashboard_has_no_description_link():
    html = (ROOT.parent / "public" / "subscriber-dashboard.html").read_text(encoding="utf-8")
    assert "description_url" not in html and "📄 Description" not in html


def test_episode_record_endpoint_does_not_return_the_old_url(monkeypatch):
    from endpoints.public import routes

    class Doc:
        exists = True
        id = "ever-bio-250050"

        def to_dict(self):
            return {"title": "T", "description_url": "https://x/descriptions/ever-bio-250050.md",
                    "assets": {"audio_blob": "audio/a.mp3", "description_blob": "descriptions/ever-bio-250050.md"}}

    class Coll:
        def document(self, _):
            return type("R", (), {"get": staticmethod(lambda: Doc())})()

    monkeypatch.setattr(routes, "db", type("D", (), {"collection": staticmethod(lambda _: Coll())})())
    loop = asyncio.new_event_loop()      # not asyncio.run: it unsets the thread's event loop, which other tests in this suite rely on
    try:
        out = loop.run_until_complete(routes.get_episode_record("ever-bio-250050"))
    finally:
        loop.close()
    assert "description_url" not in out and out["assets"] == {"audio_blob": "audio/a.mp3"} and out["title"] == "T"
