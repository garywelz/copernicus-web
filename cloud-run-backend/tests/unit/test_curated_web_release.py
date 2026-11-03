"""A company release at a stable web address (curated_web_release): confirmed by a guarded fetch, pinned by the SHA-256 of the bytes and the fetch date,
re-checked by hash on publish day. Offline: the fetch is faked, so every guard and refusal is exercised without a network."""
import asyncio
import hashlib
import importlib.util
import json
import os

import pytest

import curated_mode as cm
import curated_sources as cs
import curated_web_release as cwr
from safe_fetch import FetchRefused, FetchResult
from tests.unit.test_curated_mode import approved_doc, base_items, registry_item, release_item

URL = "https://www.anthropic.com/research/exponential-time-hypothesis.pdf"
TITLE = "The Exponential Time Hypothesis Revisited"
BODY_TEXT = (f"{TITLE}. Anthropic. We report a computer-assisted analysis of the exponential time hypothesis and describe what was and was not "
             "checked. The analysis relies on a formalization of the key lemma and on an independent review of the counting argument.")
PDF = b"%PDF-1.7\n" + BODY_TEXT.encode() + b"\n%%EOF"
HTML = f"<html><head><title>x</title><style>p{{color:red}}</style><script>var a=1;</script></head><body><h1>{TITLE}</h1><p>{BODY_TEXT}</p></body></html>".encode()


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def reader(body):                 # stands in for the PDF reader: the 'PDF' bytes above carry their text after the header
    return body.decode("latin-1").split("\n", 1)[1].rsplit("\n", 1)[0]


class Web:
    """A fake guarded fetch: one answer per URL (a FetchResult, or an exception to raise). Records every call."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    async def __call__(self, url, **kw):
        self.calls.append((url, kw))
        a = self.answers[url]
        if isinstance(a, Exception):
            raise a
        return a


def ok(body=PDF, ctype="application/pdf", status=200, url=URL):
    return FetchResult(status, {"content-type": ctype}, body, url)


def confirm(web=None, **kw):
    args = dict(url=URL, title=TITLE, company="Anthropic", date="2026-10-31", authors=())
    args.update(kw)
    return run(cwr.confirm_web_release(fetch=web or Web({URL: ok()}), pdf_reader=reader, **args))


# --- confirming ----------------------------------------------------------------------------------------------------------------
def test_a_pdf_is_confirmed_and_pinned_by_the_hash_of_its_bytes_and_the_fetch_date():
    web = Web({URL: ok()})
    item = confirm(web)
    c = item["confirmation"]
    assert item["class"] == cs.COMPANY_RELEASE and c["status"] == cs.CONFIRMED and c["registry"] == "web_release" and item["approved"] is True
    assert c["sha256"] == hashlib.sha256(PDF).hexdigest() and c["bytes"] == len(PDF) and c["fetched_at"].endswith("Z") and c["content_type"] == "application/pdf"
    assert item["title"] == TITLE and item["authors"] == ["Anthropic"] and item["year"] == 2026 and item["date"] == "2026-10-31" and item["company"] == "Anthropic"
    assert item["result_status"] == "unverified" and item["status_basis"]["sha256"] == c["sha256"] and item["identifiers"] == {"release_url": URL}
    assert item["evidence_text"].startswith(TITLE) and len(item["evidence_text"]) <= cwr.EVIDENCE_CHARS
    assert web.calls[0][0] == URL and web.calls[0][1]["max_bytes"] == cwr.MAX_RELEASE_BYTES          # a PDF needs a larger cap than commentary pages


def test_a_web_page_is_confirmed_from_its_visible_text_not_its_scripts_or_styles():
    item = confirm(Web({URL: ok(HTML, "text/html; charset=utf-8")}))
    assert item["confirmation"]["status"] == cs.CONFIRMED and item["confirmation"]["content_type"] == "text/html"
    assert "var a=1" not in item["evidence_text"] and "color:red" not in item["evidence_text"] and TITLE in item["evidence_text"]


def test_the_item_id_is_stable_and_depends_on_the_address_only():
    a, b = confirm(), confirm(Web({URL: ok(PDF + b" ")}))
    assert a["item_id"] == b["item_id"] == cs.item_id({"release_url": URL}) and cs.item_key({"release_url": URL}) == f"release_url:{URL}"
    assert a["confirmation"]["sha256"] != b["confirmation"]["sha256"]


def test_the_company_may_be_found_in_the_address_instead_of_the_text():
    text = BODY_TEXT.replace("Anthropic", "The lab")
    item = confirm(Web({URL: ok(b"%PDF-1.7\n" + text.encode() + b"\n%%EOF")}))
    assert item["confirmation"]["status"] == cs.CONFIRMED
    other = "https://example.org/paper.pdf"
    r = confirm(Web({other: ok(b"%PDF-1.7\n" + text.encode() + b"\n%%EOF", url=other)}), url=other)
    assert r["confirmation"]["reason"] == "company_not_found" and r["item_id"] is None


@pytest.mark.parametrize("kw,answer,reason", [
    (dict(url="http://www.anthropic.com/x.pdf"), None, "not_https"),
    (dict(url="https://user:pw@www.anthropic.com/x.pdf"), None, "bad_address"),
    (dict(url="https://127.0.0.1/x.pdf"), None, "bad_address"),
    (dict(title=""), None, "bad_title"), (dict(title="x" * 301), None, "bad_title"),
    (dict(company=""), None, "bad_company"), (dict(company="x" * 61), None, "bad_company"),
    (dict(date="yesterday"), None, "bad_date"), (dict(date="2026-02-30"), None, "bad_date"),
    (dict(authors=["a"] * 6), None, "bad_authors"),
    ({}, ok(status=404), "http_404"), ({}, ok(status=503), "http_503"), ({}, ok(b""), "empty"),
    ({}, ok(b"x" * 500, "image/png"), "unsupported_content_type:image/png"),
    ({}, ok(b"not a pdf at all" * 40, "application/pdf"), "text_not_readable"),
    ({}, ok(b"%PDF-1.7\nshort\n%%EOF"), "no_readable_text"),
    (dict(title="A Different Paper Entirely"), None, "title_not_in_document"),
    (dict(company="DeepMind"), None, "company_not_found"),
])
def test_a_release_that_does_not_check_out_is_refused_with_its_reason(kw, answer, reason):
    r = confirm(Web({URL: answer or ok(), **({kw["url"]: answer or ok()} if "url" in kw else {})}), **kw)
    assert r["item_id"] is None and r["approved"] is False and r["confirmation"]["status"] == cs.REFUSED and r["confirmation"]["reason"] == reason


def test_a_guard_refusal_is_a_refusal_but_a_network_failure_is_unknown():
    r = confirm(Web({URL: FetchRefused("address_not_public", "host")}))
    assert r["confirmation"]["reason"] == "fetch_refused:address_not_public"
    r = confirm(Web({URL: FetchRefused("too_large", ">15000000")}))
    assert r["confirmation"]["reason"] == "fetch_refused:too_large"
    with pytest.raises(cwr.WebReleaseUnavailable):
        confirm(Web({URL: TimeoutError()}))
    with pytest.raises(cwr.WebReleaseUnavailable):
        confirm(Web({URL: OSError("connection reset")}))


def test_a_redirect_to_another_host_is_judged_by_the_final_address():
    final = "https://cdn.example.net/files/paper.pdf"
    item = confirm(Web({URL: ok(url=final)}))
    assert item["confirmation"]["final_url"] == final and item["confirmation"]["url"] == URL and item["url"] == URL


# --- the title as a PDF's text layer reads it ---------------------------------------------------------------------------------------
REAL_TITLE = "A 2^{o(n)} Time Algorithm for 3-SAT"
# what the text layer of the actual paper gives for its title (anthropics/formal-math, eth/paper.pdf at 16a5ce41): spacing and superscript lost
REAL_TEXT = ("A2 o(n) TIME ALGORITHM FOR 3-SAT CLAUDE ANTHROPIC Abstract. We refute the Exponential Time Hypothesis (ETH) by presenting a deterministic "
             "algorithm for 3-SAT onn variables that runs in2o(n) time. Our algorithm in fact solves the harder problem #3-SAT, providing a count of the "
             "number of satisfying assignments. The result was discovered by an internal research Claude model and has been formalized in Lean 4.")


def PDFOF(text):
    return b"%PDF-1.7" + bytes([10]) + text.encode() + bytes([10]) + b"%%EOF"


def test_a_title_is_found_in_a_text_layer_that_lost_its_spacing_and_superscripts():
    assert cwr.title_in_text(REAL_TITLE, REAL_TEXT)
    assert cwr.title_in_text("A 2o(n) Time Algorithm for 3-SAT", REAL_TEXT) and cwr.title_in_text("a 2^o(n) time algorithm for 3-sat", REAL_TEXT)
    item = confirm(Web({URL: ok(PDFOF(REAL_TEXT))}), title=REAL_TITLE, date="2026-10-27")
    assert item["confirmation"]["status"] == cs.CONFIRMED and item["title"] == REAL_TITLE          # the title you gave is what is stored and printed


def test_the_looser_comparison_still_refuses_a_different_or_a_too_short_title():
    assert not cwr.title_in_text("A 2^{o(n)} Time Algorithm for 4-SAT", REAL_TEXT)
    assert not cwr.title_in_text("SAT", REAL_TEXT) and not cwr.title_in_text("Time", REAL_TEXT) and not cwr.title_in_text("", REAL_TEXT)
    assert not cwr.title_in_text("Algorithm for 3-SAT", "unrelated text " * 50)
    r = confirm(Web({URL: ok(PDFOF(REAL_TEXT))}), title="A 2^{o(n)} Time Algorithm for 4-SAT")
    assert r["confirmation"]["reason"] == "title_not_in_document"


# --- the list ------------------------------------------------------------------------------------------------------------------
def test_the_list_hash_changes_when_the_pinned_bytes_change_and_not_otherwise():
    a, b, same = confirm(), confirm(Web({URL: ok(PDF + b" ")})), confirm()
    base = [registry_item(cs.PEER_REVIEWED, 1), registry_item(cs.PREPRINT, 2, registry="arxiv")]
    pin = {"repo": "openai/math", "commit": "7" * 40}
    # the evidence text is the same for a and b; only the pinned bytes differ
    assert a["evidence_text"] == b["evidence_text"]
    assert cs.list_hash(pin, base + [a]) != cs.list_hash(pin, base + [b])
    a2 = dict(same, confirmation=dict(same["confirmation"], fetched_at="2030-01-01T00:00:00Z"))
    assert cs.list_hash(pin, base + [a]) == cs.list_hash(pin, base + [a2])          # the fetch date alone is not part of the hash


def test_a_web_release_counts_toward_the_minimum_and_is_not_a_repository_manuscript():
    items = [registry_item(cs.PEER_REVIEWED, 1), confirm(), release_item()]
    ok_, counts = cs.minimum_check(items)
    assert ok_ and counts["company_release"] == 2 and counts["non_commentary"] == 3


# --- the run: prompt wording, references, status ---------------------------------------------------------------------------------
def anthropic_run():
    items = [registry_item(cs.PEER_REVIEWED, 1), release_item(), confirm()]
    return cm.CuratedRun.from_list_doc(approved_doc(items), private_texts={})


def test_the_prompt_names_each_company_and_gives_a_non_openai_release_its_own_unverified_wording():
    run_ = anthropic_run()
    assert run_.companies() == ["OpenAI", "Anthropic"]
    block = run_.prompt_block()
    assert "\"OpenAI says\"" in block and "\"Anthropic says\"" in block and "Anthropic's own paper, not independently checked." in block
    assert "OpenAI's own manuscript, not independently checked." in block
    assert "You may report that OpenAI or Anthropic or a cited source says so" in block
    assert {cm.company_of(i) for i in run_.items if i["class"] == cs.COMPANY_RELEASE} == {"OpenAI", "Anthropic"}


def test_a_list_of_openai_manuscripts_alone_is_worded_exactly_as_before():
    run_ = cm.CuratedRun.from_list_doc(approved_doc(base_items()), private_texts={})
    assert run_.companies() == ["OpenAI"]
    block = run_.prompt_block()
    assert '("OpenAI says", "OpenAI\'s manuscript argues").' in block and "You may report that OpenAI or a cited source says so, attributed" in block


def test_the_reference_line_gives_the_address_the_fetch_date_and_the_start_of_the_hash():
    run_ = anthropic_run()
    web = next(i for i in run_.items if i["identifiers"].get("release_url"))
    c = cm.confirmed_from_item(web, "P3")
    line = cm.source_line(c, cs.COMPANY_RELEASE, "unverified")
    sha = web["confirmation"]["sha256"]
    assert line.startswith("- Anthropic (2026). " + TITLE) and URL in line and f"sha256 {sha[:12]}" in line and "fetched " in line
    assert "company release, not peer reviewed; status: unverified" in line and "commit" not in line
    assert c.pin["sha256"] == sha and c.registry == "web_release" and c.source_class == cs.COMPANY_RELEASE


def test_an_openai_manuscript_line_is_unchanged():
    c = cm.confirmed_from_item(release_item(), "P2")
    assert "commit 7ef5c0cc5" in cm.source_line(c, cs.COMPANY_RELEASE, "unverified") and "sha256" not in cm.source_line(c, cs.COMPANY_RELEASE, "unverified")


# --- the publish-day re-check --------------------------------------------------------------------------------------------------------
def test_the_same_bytes_are_unchanged():
    item = confirm()
    rows = run(cwr.recheck_web_releases([item, release_item()], Web({URL: ok()})))
    assert len(rows) == 1 and rows[0]["changed"] is False and rows[0]["current"] == rows[0]["recorded"] and rows[0]["notes"] == []


def test_different_bytes_are_a_change_and_the_reason_is_given():
    rows = run(cwr.recheck_web_releases([confirm()], Web({URL: ok(PDF + b"\n")})))
    assert rows[0]["changed"] is True and rows[0]["current"] != rows[0]["recorded"] and "differ from the pinned" in rows[0]["notes"][0]


@pytest.mark.parametrize("status", [404, 410])
def test_a_release_that_has_gone_is_a_change(status):
    rows = run(cwr.recheck_web_releases([confirm()], Web({URL: ok(b"", status=status)})))
    assert rows[0]["changed"] is True and rows[0]["current"] == f"HTTP {status}" and "no longer at its address" in rows[0]["notes"][0]


@pytest.mark.parametrize("answer", [ok(b"", status=503), FetchRefused("address_not_public", "h"), TimeoutError(), OSError("reset")])
def test_an_address_that_cannot_be_read_means_nothing_is_known(answer):
    rows = run(cwr.recheck_web_releases([confirm()], Web({URL: answer})))
    assert rows[0]["current"] == "unreadable" and rows[0]["changed"] is False and rows[0]["notes"]


def test_the_recheck_fetches_the_recorded_address_not_the_final_one():
    final = "https://cdn.example.net/files/paper.pdf"
    item = confirm(Web({URL: ok(url=final)}))
    web = Web({URL: ok()})
    run(cwr.recheck_web_releases([item], web))
    assert [c[0] for c in web.calls] == [URL]


# --- the command ----------------------------------------------------------------------------------------------------------------------
BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("recheck_curated_statuses", os.path.join(BACKEND, "scripts", "recheck_curated_statuses.py"))
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


class OneDocDB:
    def __init__(self, doc):
        self.doc = doc

    def collection(self, name):
        return self

    def document(self, doc_id):
        db = self

        class Ref:
            def get(self_r):
                class Snap:
                    exists = True

                    def to_dict(s):
                        return db.doc
                return Snap()
        return Ref()


def command(web, doc=None, capsys=None):
    from tests.unit.test_recheck_script import Repo, standard_trees
    doc = doc or {"list_id": "L1", "status": "approved", "list_hash": "h" * 64, "pin": {"repo": "openai/math", "commit": "7" * 40}, "items": [confirm()]}
    return script.main(["L1"], db=OneDocDB(doc), fetch=Repo(trees=standard_trees()), web_fetch=web)


def test_the_command_exits_zero_when_the_bytes_match(capsys):
    assert command(Web({URL: ok()})) == 0
    out = capsys.readouterr().out
    assert "publication may go ahead" in out and TITLE in out and "sha256 " in out


def test_the_command_says_do_not_publish_when_the_bytes_differ(capsys):
    assert command(Web({URL: ok(PDF + b"x")})) == 2
    assert "DO NOT PUBLISH: 1 item(s) changed" in capsys.readouterr().out


def test_the_command_exits_three_when_the_address_cannot_be_read(capsys):
    assert command(Web({URL: ok(b"", status=503)})) == 3
