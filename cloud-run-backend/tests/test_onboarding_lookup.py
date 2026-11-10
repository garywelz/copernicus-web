"""Onboarding PR 4b-1: identifier lookups, adding a seed by identifier, and changing lookup consent (design 2.4, 2.8, 5.5; utils/onboarding_lookup.py,
utils/onboarding_ids.py). Offline: the one network function is replaced by a table of canned registry answers, so no test touches a registry, and the atomic
in-memory Firestore of tests/fakes_pr2.py stands in for the database. Every paper here is synthetic (the DOI prefix 10.9998 is not a real registrant).

The tests that must be able to fail are each run against the opposite case in the same test: no lookup without consent (and a lookup WITH it), the rate limit
(the 60th passes, the 61st is refused before any call), the size cap (at the cap passes, one byte over does not), and the "not found" wording."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from tests.test_onboarding_items import ADMIN, ADV, H, OTH, STRANGER, T0, X, Y, YMEM, env, events, snapshot, stored, strings  # noqa: F401  (env is a fixture)
from tests.test_onboarding_workspace import progress, row, section_doc, set_section
from utils import onboarding as ob
from utils import onboarding_form as form
from utils import onboarding_ids as ids
from utils import onboarding_lint as lint
from utils import onboarding_lookup as lookup
from utils import onboarding_render as render

BASE = f"/api/onboarding/engines/{X}"
DOI, DOI_KEY = "10.9998/synthetic.001", "doi:10.9998/synthetic.001"
CROSSREF_URL = "https://api.crossref.org/works/10.9998%2Fsynthetic.001"
OPENALEX_URL = "https://api.openalex.org/works/doi:10.9998/synthetic.001"
S2_URL = "https://api.semanticscholar.org/graph/v1/paper/DOI:10.9998/synthetic.001?fields=title%2Cyear%2Cauthors%2Cabstract%2CexternalIds"
ARXIV_URL = "https://export.arxiv.org/api/query?id_list=2401.00001&max_results=1"
FORBIDDEN_WORDING = ("no such paper", "does not exist.", "doesn't exist", "is not a real paper")


def crossref(title="A synthetic paper", abstract="<jats:p>The <b>abstract</b> text.</jats:p>", doi=DOI, authors=(("Ada", "Example"), ("Bo", "Sample"))):
    msg = {"DOI": doi, "title": [title], "author": [{"given": g, "family": f} for g, f in authors], "issued": {"date-parts": [[2021, 3, 4]]}}
    if abstract is not None:
        msg["abstract"] = abstract
    return json.dumps({"status": "ok", "message": msg}).encode()


def openalex(title="A synthetic paper", words=("An", "indexed", "abstract"), doi=DOI, pmid=None):
    return json.dumps({"title": title, "publication_year": 2021, "doi": f"https://doi.org/{doi}" if doi else None,
                       "authorships": [{"author": {"display_name": "Ada Example"}}], "ids": {"pmid": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else None},
                       "abstract_inverted_index": {w: [i] for i, w in enumerate(words)} if words else None}).encode()


def arxiv_feed(entry=True, doctype=False):
    body = ('<entry><id>http://arxiv.org/abs/2401.00001v3</id><title>A synthetic\n preprint</title><summary> Its summary. </summary><published>2024-01-02T00:00:00Z</published>'
            '<author><name>Ada Example</name></author></entry>') if entry else ""
    return ((b'<!DOCTYPE feed [<!ENTITY a "b">]>' if doctype else b"") + f'<feed xmlns="http://www.w3.org/2005/Atom">{body}</feed>'.encode())


class Web:
    """A table of canned answers: url -> (status, bytes) or an exception to raise. Every call is recorded."""

    def __init__(self):
        self.table, self.calls = {}, []

    def __call__(self, url, timeout):
        self.calls.append(url)
        got = self.table.get(url, (404, b"{}"))
        if isinstance(got, Exception):
            raise got
        return got


@pytest.fixture
def web(monkeypatch):
    w = Web()
    monkeypatch.setattr(lookup, "_http_get", w)
    return w


def consent(env, who, on=True, engine=X):
    env.db.data[ob.MEMBERS][ob.member_id(engine, who)]["consent"]["lookups"] = on


@pytest.fixture
def agreed(env, web):
    for who in (ADV, OTH):
        consent(env, who)
    consent(env, YMEM, engine=Y)
    env.web = web
    return env


def look(env, who, query, engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/lookup", json={"query": query}, headers=H[who] if who in H else ADMIN)


def add_seed(env, who, identifier=DOI, questions=("ex-q1",), engine=X):
    return env.client.post(f"/api/onboarding/engines/{engine}/seeds", json={"identifier": identifier, "question_ids": list(questions)}, headers=H[who] if who in H else ADMIN)


def set_consent(env, who, on, engine=X):
    return env.client.put(f"/api/onboarding/engines/{engine}/consent/lookups", json={"lookups": on}, headers=H[who] if who in H else ADMIN)


# ---- identifiers --------------------------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("typed,expected", [
    ("10.9998/Synthetic.001", ("doi", "doi:10.9998/synthetic.001")), ("doi: 10.9998/x", ("doi", "doi:10.9998/x")), ("https://doi.org/10.9998/x", ("doi", "doi:10.9998/x")),
    ("2401.00001v3", ("arxiv", "arxiv:2401.00001")), ("arXiv:2401.00001", ("arxiv", "arxiv:2401.00001")), ("https://arxiv.org/abs/math/0301001", ("arxiv", "arxiv:math/0301001")),
    ("pmid:12345", ("pmid", "pmid:12345")), ("12345", ("pmid", "pmid:12345")), ("https://pubmed.ncbi.nlm.nih.gov/12345/", ("pmid", "pmid:12345")),
    ("  A study of   synthetic things ", ("title", "A study of synthetic things")),
    ("10.99/not-a-doi", (None, None)), ("doi:nonsense", (None, None)), ("arxiv:nonsense", (None, None)), ("pmid:12ab", (None, None)), ("1234567890", (None, None)),
    ("Smith", (None, None)), ("", (None, None)), ("   ", (None, None)), ("12 34 56 78", (None, None)), ("x" * 401, (None, None)), ("a title with \x00 in it", (None, None)), (5, (None, None)),
])
def test_what_an_owner_types_is_an_identifier_a_title_or_refused(typed, expected):
    assert ids.classify(typed) == expected


def test_the_identifier_rules_and_the_seed_id_are_the_loaders():
    from tests.test_onboarding_loader import le
    assert (ids.DOI_RE.pattern, ids.ARXIV_RE.pattern, ids.PMID_RE.pattern) == (le.DOI_RE.pattern, le.ARXIV_RE.pattern, le.PMID_RE.pattern)
    for kind, raw in (("doi", "10.9998/ABC"), ("doi", "https://doi.org/10.9998/x"), ("doi", "`10.9998/x`"), ("doi", "nope"), ("arxiv", "2401.00001v2"), ("arxiv", "arXiv:math/0301001"),
                      ("arxiv", "nope"), ("pmid", "pmid: 123"), ("pmid", "12a"), ("other", "1")):
        assert ids.normalise_identifier(kind, raw) == le.normalise_identifier(kind, raw), (kind, raw)
    it = next(i for i in le.parse_seeds("doi,question_ids,title\n10.9998/abc,q1,T\n", "", {"q1"})[0])
    assert it["item_id"] == ids.seed_item_id("doi:10.9998/abc")


# ---- the lookup service -------------------------------------------------------------------------------------------------------------------------------
def test_a_doi_is_answered_by_crossref_alone_when_it_has_an_abstract_and_every_field_says_where_it_came_from(web):
    web.table[CROSSREF_URL] = (200, crossref())
    out = lookup.lookup(None, "doi", DOI_KEY)
    assert web.calls == [CROSSREF_URL] and out["state"] == "found" and out["message"] == "" and out["cached"] is False
    (rec,) = out["results"]
    assert rec == {"title": "A synthetic paper", "authors": ["Ada Example", "Bo Sample"], "year": 2021, "abstract": "The abstract text.", "identifiers": {"doi": DOI_KEY},
                   "sources": {"title": "crossref", "authors": "crossref", "year": "crossref", "abstract": "crossref"}}
    assert out["checked"] == [{"registry": "crossref", "name": "Crossref", "state": "found"}]


def test_a_missing_abstract_is_filled_from_the_next_registry_and_the_provenance_says_so(web):
    web.table[CROSSREF_URL] = (200, crossref(abstract=None))
    web.table[OPENALEX_URL] = (200, openalex(pmid="777"))
    out = lookup.lookup(None, "doi", DOI_KEY)
    rec = out["results"][0]
    assert web.calls == [CROSSREF_URL, OPENALEX_URL] and rec["abstract"] == "An indexed abstract"
    assert rec["sources"] == {"title": "crossref", "authors": "crossref", "year": "crossref", "abstract": "openalex"} and rec["title"] == "A synthetic paper"
    assert rec["identifiers"] == {"doi": DOI_KEY, "pmid": "pmid:777"}
    web.calls.clear()
    web.table[OPENALEX_URL] = (200, openalex(words=None))
    web.table[S2_URL] = (200, json.dumps({"title": "Another title", "year": 2020, "authors": [{"name": "Zed"}], "abstract": "From the third.", "externalIds": {"DOI": DOI.upper()}}).encode())
    rec = lookup.lookup(None, "doi", DOI_KEY)["results"][0]
    assert web.calls == [CROSSREF_URL, OPENALEX_URL, S2_URL] and rec["sources"]["abstract"] == "s2" and rec["abstract"] == "From the third." and rec["title"] == "A synthetic paper"


def test_an_empty_result_is_not_found_in_named_registries_just_now_and_never_a_statement_that_the_paper_does_not_exist(web):
    out = lookup.lookup(None, "doi", DOI_KEY)                                   # every registry answers 404
    assert out["state"] == "not_found" and out["results"] == [] and web.calls == [CROSSREF_URL, OPENALEX_URL, S2_URL]
    assert out["message"].startswith("Not found in Crossref, OpenAlex and Semantic Scholar just now.")
    assert "This does not mean the paper does not exist" in out["message"]
    stripped = out["message"].replace("This does not mean the paper does not exist", "")
    assert not [w for w in FORBIDDEN_WORDING if w in stripped.lower()]
    source = (Path(lookup.__file__).read_text(encoding="utf-8") + Path(form.__file__).read_text(encoding="utf-8")).lower()
    assert "no such paper" not in source.replace('never as "no such paper"', "")


@pytest.mark.parametrize("answer", [(429, b"{}"), (500, b"oops"), (301, b""), (403, b"{}"), TimeoutError("slow"), ConnectionError("down"), (200, b"not json"),
                                    (200, b'{"message": 5}')])
def test_a_registry_that_fails_is_unavailable_which_is_worded_differently_from_not_found_and_says_nothing_about_the_paper(web, answer):
    web.table[CROSSREF_URL] = answer
    out = lookup.lookup(None, "doi", DOI_KEY)
    if answer == (200, b'{"message": 5}'):
        assert out["state"] == "not_found"                                      # a readable answer with no record in it is an answer
        return
    assert out["state"] == "unavailable" and out["results"] == []
    assert out["message"].startswith("The lookup could not be completed just now (Crossref did not give a usable answer).") and "says nothing about the paper" in out["message"]
    assert "Not found" not in out["message"]
    assert [c["state"] for c in out["checked"]] == ["unavailable", "not_found", "not_found"]
    web.table[OPENALEX_URL] = (200, openalex())                                 # ...but another registry that has the paper still answers
    assert lookup.lookup(None, "doi", DOI_KEY)["state"] == "found"


def test_the_response_size_cap_is_exact_one_byte_over_is_no_answer(web, monkeypatch):
    monkeypatch.setattr(lookup, "MAX_BYTES", len(crossref()))
    web.table[CROSSREF_URL] = (200, crossref())
    assert lookup.lookup(None, "doi", DOI_KEY)["state"] == "found"              # exactly at the cap
    web.table[CROSSREF_URL] = (200, crossref() + b" ")
    out = lookup.lookup(None, "doi", DOI_KEY)
    assert out["state"] == "unavailable" and out["checked"][0] == {"registry": "crossref", "name": "Crossref", "state": "unavailable"}


def test_the_real_network_function_reads_no_more_than_the_cap_sends_no_credential_and_follows_no_redirect(monkeypatch):
    seen = {}

    class Raw:
        def read(self, n, decode_content=False):
            seen["read"] = n
            return b"x" * n

    class Resp:
        status_code, raw = 200, Raw()

        def close(self):
            seen["closed"] = True

    def get(url, **kw):
        seen.update(url=url, **kw)
        return Resp()
    monkeypatch.setattr(lookup.requests, "get", get)
    status, body = lookup._http_get("https://api.crossref.org/works/x", 3)
    assert status == 200 and len(body) == lookup.MAX_BYTES + 1 == seen["read"] and seen["closed"]
    assert seen["allow_redirects"] is False and seen["stream"] is True and seen["timeout"] == 3
    assert set(seen["headers"]) == {"User-Agent", "Accept"} and seen["headers"]["User-Agent"] == "onboarding-lookup/1.0"
    assert "@" not in json.dumps(seen["headers"]) and "mailto" not in json.dumps(seen["headers"]).lower()
    assert lookup.TIMEOUT_SECONDS == 8 and lookup.TOTAL_BUDGET_SECONDS == 15 and lookup.MAX_BYTES == 512_000


def test_the_timeout_is_passed_to_every_call_and_the_total_budget_stops_further_calls(web, monkeypatch):
    seen, clock = [], [100.0]

    def get(url, timeout):
        seen.append(timeout)
        clock[0] += 9                                                            # each registry takes nine seconds
        return 404, b"{}"
    monkeypatch.setattr(lookup, "_http_get", get)
    monkeypatch.setattr(lookup.time, "monotonic", lambda: clock[0])
    out = lookup.lookup(None, "doi", DOI_KEY)
    assert seen == [8, 6.0] and [c["state"] for c in out["checked"]] == ["not_found", "not_found", "unavailable"]       # the third was never asked: the budget was spent
    assert out["state"] == "unavailable"


def test_only_the_four_registries_are_ever_contacted_and_a_pubmed_id_never_goes_to_ncbi(web):
    web.table["https://api.openalex.org/works/pmid:12345"] = (200, openalex(words=None, pmid="12345"))
    web.table["https://api.semanticscholar.org/graph/v1/paper/PMID:12345?fields=title%2Cyear%2Cauthors%2Cabstract%2CexternalIds"] = (
        200, json.dumps({"title": "T", "abstract": "From S2.", "externalIds": {"PubMed": 12345}}).encode())
    rec = lookup.lookup(None, "pmid", "pmid:12345")["results"][0]
    assert rec["identifiers"] == {"doi": DOI_KEY, "pmid": "pmid:12345"} and rec["sources"]["abstract"] == "s2"
    lookup.lookup(None, "arxiv", "arxiv:2401.00001")
    lookup.lookup(None, "doi", DOI_KEY)
    lookup.lookup(None, "title", "A study of synthetic things")
    hosts = {u.split("/")[2] for u in web.calls}
    assert hosts == {"api.openalex.org", "api.semanticscholar.org", "export.arxiv.org", "api.crossref.org"} == {h.split("/")[2] for h in lookup.HOSTS.values()}
    assert all(u.startswith("https://") for u in web.calls) and not [u for u in web.calls if "ncbi" in u or "pubmed" in u.split("?")[0].replace("/works/pmid:", "")]


def test_arxiv_records_are_read_from_the_feed_and_an_empty_or_strange_feed_is_not_a_record(web):
    web.table[ARXIV_URL] = (200, arxiv_feed())
    out = lookup.lookup(None, "arxiv", "arxiv:2401.00001")
    assert out["results"] == [{"title": "A synthetic preprint", "authors": ["Ada Example"], "year": 2024, "abstract": "Its summary.", "identifiers": {"arxiv": "arxiv:2401.00001"},
                               "sources": {"title": "arxiv", "authors": "arxiv", "year": "arxiv", "abstract": "arxiv"}}]
    web.table[ARXIV_URL] = (200, arxiv_feed(entry=False))
    assert lookup.lookup(None, "arxiv", "arxiv:2401.00001")["state"] == "not_found"
    web.table[ARXIV_URL] = (200, arxiv_feed(doctype=True))
    assert lookup.lookup(None, "arxiv", "arxiv:2401.00001")["state"] == "unavailable"


def test_registry_text_is_stored_as_plain_text(web):
    web.table[CROSSREF_URL] = (200, crossref(title="<i>Hostile</i> <script>alert(1)</script>\x07 title &amp; more", abstract="<jats:p>a\x00b</jats:p>  c",
                                             authors=(("<b>Ada</b>", "Ex\nample"),)))
    rec = lookup.lookup(None, "doi", DOI_KEY)["results"][0]
    assert rec["title"] == "Hostile alert(1) title & more" and rec["abstract"] == "a b c" and rec["authors"] == ["Ada Ex ample"]
    assert not [s for s in strings(rec) if "<" in s or "\x00" in s]
    web.table[CROSSREF_URL] = (200, crossref(title="T" * 5000, abstract="A" * 50_000, authors=tuple(("G", "F") for _ in range(100))))
    rec = lookup.lookup(None, "doi", DOI_KEY)["results"][0]
    assert (len(rec["title"]), len(rec["abstract"]), len(rec["authors"])) == (600, 5000, 20)


def test_a_title_search_returns_at_most_five_possible_matches_each_with_a_doi_and_picks_none(web):
    cr = "https://api.crossref.org/works?query.bibliographic=A+study+of+synthetic+things&rows=5&select=DOI%2Ctitle%2Cauthor%2Cissued%2Cabstract"
    oa = "https://api.openalex.org/works?search=A+study+of+synthetic+things&per-page=5"
    items = [json.loads(crossref(title=f"Match {n}", doi=f"10.9998/m{n}"))["message"] for n in range(4)] + [{"title": ["No DOI"]}]
    web.table[cr] = (200, json.dumps({"message": {"items": items}}).encode())
    web.table[oa] = (200, json.dumps({"results": [json.loads(openalex(title="Match 0 again", doi="10.9998/m0")), json.loads(openalex(title="Match 9", doi="10.9998/m9")),
                                                  json.loads(openalex(title="Match 10", doi="10.9998/m10")), json.loads(openalex(title="Nothing", doi=None))]}).encode())
    out = lookup.lookup(None, "title", "A study of synthetic things")
    assert web.calls == [cr, oa] and out["state"] == "found"
    assert [r["title"] for r in out["results"]] == ["Match 0", "Match 1", "Match 2", "Match 3", "Match 9"]
    assert all(r["identifiers"].get("doi") for r in out["results"]) and out["results"][4]["sources"]["title"] == "openalex"
    web.table[cr], web.table[oa] = (200, b'{"message": {"items": []}}'), (200, b'{"results": []}')
    out = lookup.lookup(None, "title", "A study of synthetic things")
    assert out["state"] == "not_found" and out["message"].startswith("Not found in Crossref and OpenAlex just now.")
    web.table[oa] = (429, b"")
    assert lookup.lookup(None, "title", "A study of synthetic things")["state"] == "unavailable"


def test_a_found_record_is_cached_for_a_day_by_a_hash_of_the_query_and_failures_are_never_cached(env, web):
    web.table[CROSSREF_URL] = (200, crossref())
    first = lookup.lookup(env.db, "doi", DOI_KEY, now=T0)
    again = lookup.lookup(env.db, "doi", "doi:" + DOI.upper(), now=T0 + timedelta(hours=23, minutes=59))
    assert web.calls == [CROSSREF_URL] and again["cached"] is True and again["results"] == first["results"] and again["fetched_at"] == T0.isoformat()
    (key,) = env.db.data[lookup.CACHE]
    doc = env.db.data[lookup.CACHE][key]
    assert key == lookup.cache_key("doi", DOI) and set(doc) == {"query_sha256", "result", "fetched_at"} and DOI not in key
    lookup.lookup(env.db, "doi", DOI_KEY, now=T0 + timedelta(hours=24, seconds=1))
    assert web.calls == [CROSSREF_URL, CROSSREF_URL]                                                       # expired: asked again
    for answer in ((404, b"{}"), (429, b"")):
        other = "https://api.crossref.org/works/10.9998%2Fother"
        web.table[other] = answer
        lookup.lookup(env.db, "doi", "doi:10.9998/other", now=T0)
        lookup.lookup(env.db, "doi", "doi:10.9998/other", now=T0)
        assert web.calls.count(other) >= 2 and len(env.db.data[lookup.CACHE]) == 1                         # not found and unavailable are asked again every time
        web.calls.clear()
    lookup.lookup(env.db, "title", "A study of synthetic things", now=T0)
    assert not [s for d in env.db.data[lookup.CACHE].values() for s in strings(d) if "study of synthetic" in s.lower()]


def test_an_identifier_that_would_walk_the_path_is_refused_before_any_call(web):
    for bad in ("doi:10.9998/../x", "doi:10.9998/a/./b", "doi:10.9998/a\\b"):
        with pytest.raises(ValueError):
            lookup.lookup(None, "doi", bad)
    with pytest.raises(ValueError):
        lookup.lookup(None, "author", "author:someone")
    assert web.calls == []


# ---- the lookup route ---------------------------------------------------------------------------------------------------------------------------------
def test_no_lookup_runs_for_a_person_who_has_not_agreed_and_one_does_for_a_person_who_has(env, web):
    web.table[CROSSREF_URL] = (200, crossref())
    assert "lookups" not in env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["consent"]
    before = snapshot(env.db)
    for call in (lambda: look(env, ADV, DOI), lambda: add_seed(env, ADV)):
        r = call()
        assert r.status_code == 409 and r.json()["detail"]["reason"] == "lookup_consent" and "not agreed to lookups" in r.json()["detail"]["message"]
    consent(env, OTH, False)
    assert look(env, OTH, DOI).status_code == 409
    assert web.calls == [] and env.limited == [], "nothing left the server, and the refusal came before the rate limiter"
    consent(env, OTH, None)
    consent(env, ADV, "yes")                                                                              # only a real `true` counts
    assert look(env, OTH, DOI).status_code == 409 and look(env, ADV, DOI).status_code == 409 and web.calls == []
    del env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["consent"]["lookups"]
    env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["consent"].pop("lookups")
    assert snapshot(env.db) == before
    consent(env, ADV)                                                                                    # the same request, with consent: the call is made
    r = look(env, ADV, DOI)
    assert r.status_code == 200 and web.calls == [CROSSREF_URL] and r.json()["state"] == "found"


def test_the_lookup_answer_shows_the_registry_record_beside_what_was_typed_with_provenance_and_no_internal_names(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref(abstract=None))
    agreed.web.table[OPENALEX_URL] = (200, openalex())
    r = look(agreed, OTH, " https://doi.org/10.9998/SYNTHETIC.001 ")
    body = r.json()
    assert r.status_code == 200 and set(body) == {"query", "state", "message", "results", "checked", "fetched_at", "cached"}
    assert body["query"] == {"kind": "doi", "normalised": DOI_KEY} and body["state"] == "found" and body["cached"] is False
    rec = body["results"][0]
    assert (rec["title"], rec["authors"], rec["year"], rec["abstract"]) == ("A synthetic paper", ["Ada Example", "Bo Sample"], 2021, "An indexed abstract")
    assert rec["sources"] == {"title": "crossref", "authors": "crossref", "year": "crossref", "abstract": "openalex"}
    assert body["checked"] == [{"name": "Crossref", "state": "found"}, {"name": "OpenAlex", "state": "found"}]
    assert events(agreed.db) == [] and not [s for s in strings(body) if s in (ADV, OTH)]


def test_not_found_and_unavailable_reach_the_owner_in_their_own_words(agreed):
    r = look(agreed, ADV, DOI)
    assert r.status_code == 200 and r.json()["state"] == "not_found" and r.json()["results"] == []
    assert r.json()["message"].startswith("Not found in Crossref, OpenAlex and Semantic Scholar just now.") and "does not mean the paper does not exist" in r.json()["message"]
    agreed.web.table[CROSSREF_URL] = TimeoutError()
    r = look(agreed, ADV, DOI)
    assert r.json()["state"] == "unavailable" and r.json()["message"].startswith("The lookup could not be completed just now")
    for text in (r.text.lower(), look(agreed, ADV, "10.9998/other").text.lower()):
        assert "no such paper" not in text


@pytest.mark.parametrize("query", ["Smith", "doi:nonsense", "10.99/x", "arxiv:zzz", "x" * 401, "", "   ", "a title with \x00 in it"])
def test_a_query_that_is_neither_an_identifier_nor_a_title_is_refused_before_any_call(agreed, query):
    r = look(agreed, ADV, query)
    assert r.status_code in (400, 422) and agreed.web.calls == []
    if r.status_code == 400:
        assert "author's name is not accepted" in r.json()["detail"]


def test_the_lookup_is_rate_limited_per_person_and_per_engine_failing_closed_and_the_61st_makes_no_call(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    look(agreed, ADV, DOI)
    assert [(k, kw["limit"], kw["window_seconds"], kw.get("fail_closed")) for k, kw in agreed.limited] == [
        ((ADV, "onboarding_lookup"), 60, 3600, True), ((f"engine:{X}", "onboarding_lookup_engine"), 300, 3600, True)]
    counts = {}

    def limiter(db, key, route, limit, window_seconds, fail_closed=False):
        counts[(key, route)] = counts.get((key, route), 0) + 1
        if counts[(key, route)] > limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    agreed.mp.setattr(agreed.routes, "check_rate_limit", limiter)
    agreed.mp.setattr(lookup, "_cache_get", lambda *a: None)
    agreed.web.calls.clear()
    codes = [look(agreed, ADV, DOI).status_code for _ in range(61)]
    assert codes == [200] * 60 + [429] and len(agreed.web.calls) == 60, "the 60th is served and the 61st is refused before anything leaves the server"
    assert look(agreed, OTH, DOI).status_code == 200                                                       # the limit is per person
    agreed.mp.setattr(agreed.routes, "LOOKUP_ENGINE_LIMIT_PER_HOUR", 61)
    assert look(agreed, OTH, DOI).status_code == 429                                                       # ...and the engine's owners share a second one


def test_the_three_routes_are_for_owners_of_that_engine_only(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    before = snapshot(agreed.db)
    calls = [lambda who, engine: look(agreed, who, DOI, engine), lambda who, engine: add_seed(agreed, who, engine=engine), lambda who, engine: set_consent(agreed, who, True, engine)]
    for call in calls:
        for who, engine in (("admin", X), (STRANGER, X), (YMEM, X), (ADV, Y)):
            r = call(who, engine)
            assert (r.status_code, r.json()) == (404, {"detail": "Not found"}), (who, engine)
    for path, method in (("/lookup", "post"), ("/seeds", "post"), ("/consent/lookups", "put")):
        assert getattr(agreed.client, method)(BASE + path, json={"query": DOI, "identifier": DOI, "question_ids": ["ex-q1"], "lookups": True}).status_code == 404   # no session
    assert agreed.web.calls == [] and snapshot(agreed.db) == before


# ---- adding a seed ------------------------------------------------------------------------------------------------------------------------------------
def test_an_added_seed_holds_the_registry_record_starts_unanswered_like_a_loaded_one_and_is_audited(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    r = add_seed(agreed, OTH, "https://doi.org/10.9998/SYNTHETIC.001", ("ex-q1", "ex-q3"))
    item_id = ids.seed_item_id(DOI_KEY)
    assert r.status_code == 200 and r.json()["id"] == item_id
    it = stored(agreed, item_id, "seeds")
    assert (it["type"], it["revision"], it["choice"], it["author_subscriber_id"], it["value"], it["history"], it["comment_count"]) == ("seed_confirm", 0, None, None, {"comment": ""}, [], 0)
    ctx = it["context"]
    assert (ctx["identifier"], ctx["identifiers"], ctx["question_ids"], ctx["title"], ctx["citation"]) == (DOI_KEY, {"doi": DOI_KEY}, ["ex-q1", "ex-q3"], "A synthetic paper", "A synthetic paper")
    assert ctx["added"] is True and ctx["added_by"] == "owner" and ctx["status_in_repo"] is None and "loaded_by" not in ctx
    assert ctx["registry"]["authors"] == ["Ada Example", "Bo Sample"] and ctx["registry"]["year"] == 2021 and ctx["registry"]["sources"]["title"] == "crossref" and ctx["registry"]["fetched_at"]
    view = r.json()["item"]
    assert (view["answered"], view["author"], view["choice"], view["revision"]) == (False, None, None, 0)
    (e,) = events(agreed.db, "seed_add")
    assert (e["engine_id"], e["actor_subscriber_id"], e["actor_role"], e["target"], e["section"], e["identifier"], e["question_ids"]) == (X, OTH, "owner", item_id, "seeds", DOI_KEY, ["ex-q1", "ex-q3"])
    assert not [s for s in strings(e) if "@" in s or "Example" in s]
    seeds = row(progress(agreed), "seeds")
    assert (seeds["items"], seeds["open"], seeds["ready"]) == (3, 3, False)                                # one more item, and it is open
    assert not [s for s in strings(r.json()) if s in (ADV, OTH)]


def test_nothing_the_browser_says_about_the_paper_is_kept(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    r = agreed.client.post(f"{BASE}/seeds", json={"identifier": DOI, "question_ids": ["ex-q1"], "title": "A title from the browser", "authors": ["Mallory"]}, headers=H[ADV])
    assert r.status_code == 200 and not [s for s in strings(stored(agreed, r.json()["id"], "seeds")) if "browser" in s or "Mallory" in s]


def test_a_seed_is_added_by_identifier_never_by_title_and_needs_a_doi_or_an_arxiv_id(agreed):
    before = snapshot(agreed.db)
    r = add_seed(agreed, ADV, "A study of synthetic things")
    assert r.status_code == 400 and "DOI, arXiv id or PubMed id" in r.json()["detail"] and agreed.web.calls == []
    agreed.web.table["https://api.openalex.org/works/pmid:12345"] = (200, openalex(doi=None, pmid="12345"))
    r = add_seed(agreed, ADV, "pmid:12345")
    assert r.status_code == 409 and "neither a DOI nor an arXiv id" in r.json()["detail"]
    assert {k: v for k, v in json.loads(snapshot(agreed.db)).items() if k != lookup.CACHE} == {k: v for k, v in json.loads(before).items() if k != lookup.CACHE}
    agreed.web.table["https://api.openalex.org/works/pmid:678"] = (200, openalex(pmid="678"))            # a PubMed id whose record has a DOI is keyed by the DOI
    r = add_seed(agreed, ADV, "pmid:678")
    assert r.status_code == 200 and stored(agreed, r.json()["id"], "seeds")["context"]["identifiers"] == {"doi": DOI_KEY, "pmid": "pmid:678"}
    agreed.web.table[ARXIV_URL] = (200, arxiv_feed())
    r = add_seed(agreed, ADV, "arXiv:2401.00001v2")
    assert r.status_code == 200 and r.json()["id"] == ids.seed_item_id("arxiv:2401.00001")


def test_a_paper_not_found_or_a_registry_that_is_down_adds_nothing_and_says_which(agreed):
    before = snapshot(agreed.db)
    r = add_seed(agreed, ADV)
    assert r.status_code == 409 and r.json()["detail"]["reason"] == "lookup_not_found" and r.json()["detail"]["message"].startswith("Not found in")
    agreed.web.table[CROSSREF_URL] = (503, b"")
    r = add_seed(agreed, ADV)
    assert r.status_code == 503 and r.json()["detail"]["reason"] == "lookup_unavailable" and "could not be completed" in r.json()["detail"]["message"]
    assert snapshot(agreed.db) == before


def test_a_paper_already_a_seed_or_in_the_review_queue_is_refused_and_so_is_a_question_that_is_not_live(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    assert add_seed(agreed, ADV).status_code == 200
    before = snapshot(agreed.db)
    r = add_seed(agreed, OTH)
    assert r.status_code == 409 and "already a seed" in r.json()["detail"]
    other = "https://api.crossref.org/works/10.9998%2Fheld.001"
    agreed.web.table[other] = (200, crossref(doi="10.9998/held.001"))
    agreed.db.data["onboarding_candidates"] = {"c1": {"engine_id": X, "origin": "hold_list", "identifier": "doi:10.9998/held.001", "identifiers": {"doi": "doi:10.9998/held.001"}},
                                               "c2": {"engine_id": Y, "origin": "hold_list", "identifier": "doi:10.9998/third", "identifiers": {}}}
    before = snapshot(agreed.db)
    r = add_seed(agreed, OTH, "10.9998/held.001")
    assert r.status_code == 409 and "review queue" in r.json()["detail"]
    third = "https://api.crossref.org/works/10.9998%2Fthird"
    agreed.web.table[third] = (200, crossref(doi="10.9998/third"))
    stored(agreed, "ex-q2").update({"choice": "drop", "revision": 1})
    before = snapshot(agreed.db)
    for questions in ([], ["ex-q2"], ["ey-q1"], ["nope"], ["ex-q1", "ex-q1"], ["seed-1"]):
        assert add_seed(agreed, OTH, "10.9998/third", questions).status_code == 400, questions
    agreed.mp.setattr(form, "MAX_SEEDS", 3)
    assert add_seed(agreed, OTH, "10.9998/third").status_code == 409
    agreed.db.data[ob.ENGINES][X]["state"] = "closed"
    assert add_seed(agreed, OTH, "10.9998/third").status_code == 409
    assert {k: v for k, v in json.loads(snapshot(agreed.db)).items() if k not in (lookup.CACHE, ob.ENGINES)} == {
        k: v for k, v in json.loads(before).items() if k not in (lookup.CACHE, ob.ENGINES)}
    agreed.db.data[ob.ENGINES][X]["state"] = "open"
    agreed.mp.setattr(form, "MAX_SEEDS", 200)
    assert add_seed(agreed, OTH, "10.9998/third").status_code == 200                                       # the same paper belongs to another engine's queue: no clash here


def test_adding_a_seed_reopens_a_final_section_tells_the_holder_and_is_audited_in_the_same_transaction_or_not_at_all(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    for i in ("seed-1", "seed-2"):
        stored(agreed, i, "seeds").update({"revision": 1, "choice": "yes", "value": {"comment": ""}})
    set_section(agreed, "seeds", "final", final_by=ADV)
    before = snapshot(agreed.db)
    agreed.db.fail_writes_to = {ob.EVENTS}
    with pytest.raises(RuntimeError):
        form.add_seed(agreed.db, engine_id=X, subscriber_id=OTH, record=lookup.lookup(None, "doi", DOI_KEY)["results"][0], question_ids=["ex-q1"])
    agreed.db.fail_writes_to = set()
    assert snapshot(agreed.db) == before                                                                   # no item, no section change
    assert add_seed(agreed, OTH).status_code == 200
    assert section_doc(agreed, "seeds")["status"] == "draft" and section_doc(agreed, "seeds")["reopened_by"] == OTH
    assert [e["from_status"] for e in events(agreed.db, "reopen")] == ["final"] and [m["kind"] for m in agreed.mail.sent] == ["reopened"]


def test_an_added_seed_once_confirmed_reaches_the_seed_files_with_its_identifier_and_title_and_no_author(agreed):
    agreed.web.table[CROSSREF_URL] = (200, crossref())
    item_id = add_seed(agreed, ADV).json()["id"]
    it = stored(agreed, item_id, "seeds")
    base = "doi,question_ids,title,arxiv_id,admit_policy,status\n10.0/x,ex-q1,\"Old\",,cited,confirmed\n"
    assert render.render_seeds_csv(base, [it])[0] == base                                                  # unanswered: not exported
    it.update({"choice": "yes", "revision": 1})
    text, _ = render.render_seeds_csv(base, [it])
    assert text.splitlines()[-1] == '10.9998/synthetic.001,ex-q1,"A synthetic paper",,,confirmed' and lint._check_seeds_csv("docs/seeds.csv", text, base) == []
    block = render.seeds_block([it])
    assert "- A synthetic paper (`doi:10.9998/synthetic.001`): confirmed" in block and "Example" not in block and "Sample" not in block


# ---- changing lookup consent --------------------------------------------------------------------------------------------------------------------------
def test_an_owner_can_turn_lookup_consent_on_and_off_and_each_change_is_one_versioned_consent_event(env, web):
    web.table[CROSSREF_URL] = (200, crossref())
    member = lambda: env.db.data[ob.MEMBERS][ob.member_id(X, ADV)]["consent"]            # noqa: E731
    assert env.client.get(BASE, headers=H[ADV]).json()["lookups_consent"] is False and look(env, ADV, DOI).status_code == 409
    r = set_consent(env, ADV, True)
    assert r.status_code == 200 and r.json() == {"lookups": True, "revision": 2}
    assert member()["lookups"] is True and member()["revision"] == 2 and member()["version"] == "1" and member()["naming"] == "role" and member()["at"] != T0.isoformat()
    (e,) = events(env.db, "consent")
    assert (e["engine_id"], e["actor_subscriber_id"], e["actor_role"], e["target"], e["field"], e["lookups"], e["consent_revision"], e["consent_version"]) == (
        X, ADV, "owner", ob.member_id(X, ADV), "lookups", True, 2, "1")
    assert e["before_sha256"] != e["after_sha256"] and e["ts"] and "ip_hash" in e
    assert env.client.get(BASE, headers=H[ADV]).json()["lookups_consent"] is True and look(env, ADV, DOI).status_code == 200
    before = snapshot(env.db)
    assert set_consent(env, ADV, True).json() == {"lookups": True, "revision": 2} and snapshot(env.db) == before          # the same answer again: nothing written
    assert set_consent(env, ADV, False).json() == {"lookups": False, "revision": 3}
    assert [(e["lookups"], e["consent_revision"]) for e in sorted(events(env.db, "consent"), key=lambda e: e["consent_revision"])] == [(True, 2), (False, 3)]
    web.calls.clear()
    assert look(env, ADV, "10.9998/other").status_code == 409 and web.calls == []                          # off again: no lookup, not even of something new
    assert "lookups" not in env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["consent"]                       # one person's switch never touches another's
    assert env.client.get(BASE, headers=ADMIN).json()["lookups_consent"] is None


def test_the_consent_change_is_strict_rate_limited_and_audited_or_not_made(env):
    for body in ({"lookups": "yes"}, {"lookups": 1}, {}, {"lookups": None}):
        assert env.client.put(f"{BASE}/consent/lookups", json=body, headers=H[ADV]).status_code == 422
    set_consent(env, ADV, True)
    assert [(k, kw["limit"]) for k, kw in env.limited] == [((ADV, "onboarding_consent"), 30)]
    before = snapshot(env.db)
    env.db.fail_writes_to = {ob.EVENTS}
    with pytest.raises(RuntimeError):
        ob.set_lookup_consent(env.db, engine_id=X, subscriber_id=ADV, lookups=False)
    env.db.fail_writes_to = set()
    assert snapshot(env.db) == before
    del env.db.data[ob.MEMBERS][ob.member_id(X, OTH)]["consent"]
    assert set_consent(env, OTH, True).status_code == 409                                                  # the consent step comes first
    assert ob.set_lookup_consent(env.db, engine_id=X, subscriber_id=OTH, lookups=True) is None
    with pytest.raises(ValueError):
        ob.set_lookup_consent(env.db, engine_id=X, subscriber_id=ADV, lookups="yes")
