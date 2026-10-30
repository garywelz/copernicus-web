"""Company-release confirmation for openai/math at a pin (curated-sources design §3.4). Offline: the fetch is faked.

The fixture is an excerpt of the repository's own manuscript map at the pinned commit (families 003, 157 and 378: three manuscripts
in 003 that share a directory name, a family with a Lean entry, and a one-manuscript family)."""
import asyncio
import json
import os

import pytest

import openai_math_index as omi
from safe_fetch import FetchRefused, FetchResult

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures", "openai_math_contents_excerpt.md")
PIN = omi.DEFAULT_COMMIT


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def text():
    return open(FIXTURE, encoding="utf-8").read()


class FakeFetch:
    """Serves the map from the fixture and git tree listings from a dict {directory: [(name, type, sha)]}."""

    def __init__(self, trees=None, map_status=200, tree_status=None, refuse=None):
        self.trees = trees if trees is not None else {}
        self.map_status, self.tree_status, self.refuse = map_status, tree_status or {}, refuse
        self.urls = []

    async def __call__(self, url, **kw):
        self.urls.append((url, kw))
        if self.refuse:
            raise FetchRefused(self.refuse)
        if url.endswith("/CONTENTS.md"):
            return FetchResult(self.map_status, {}, text().encode(), url)
        if "/git/trees/" in url:
            from urllib.parse import unquote
            d = unquote(url.split("%2F", 1)[1])
            if d in self.tree_status:
                return FetchResult(self.tree_status[d], {}, b"{}", url)
            if d not in self.trees:
                return FetchResult(404, {}, b'{"message":"Not Found"}', url)
            return FetchResult(200, {}, json.dumps({"tree": [{"path": n, "type": t, "sha": s} for n, t, s in self.trees[d]]}).encode(), url)
        raise AssertionError(url)


@pytest.fixture(autouse=True)
def _no_cache():
    omi._INDEX_CACHE.clear()
    yield
    omi._INDEX_CACHE.clear()


def index():
    return omi.parse_contents(text(), PIN)


# --- parsing the real map format -----------------------------------------------------------------------------------------------
def test_the_excerpt_parses_into_the_families_and_manuscripts_it_contains():
    ix = index()
    assert sorted(ix.families) == ["003", "157", "378"]
    assert [m.dir for m in ix.families["003"].manuscripts] == [
        "The-Quasi-Riemann-Hypothesis-September-30-2026", "The-Quasi-Riemann-Hypothesis-October-5-2026",
        "Uniform-exclusion-of-Landau-Siegel-zeros-October-1-2026"]
    assert len(ix.families["157"].manuscripts) == 3 and len(ix.families["378"].manuscripts) == 1
    assert ix.families["378"].title == "Disproof of the Exponential Time Hypothesis"


def test_a_manuscript_carries_its_title_file_abstract_and_year_from_the_map():
    m = index().by_dir["The-Exponential-Time-Hypothesis-is-False-October-25-2026"]
    assert m.title == "The Exponential Time Hypothesis is False" and m.file == "paper.pdf" and m.year == 2026 and m.family == "378"
    assert len(m.abstract) > 100 and "<" not in m.abstract


def test_a_file_name_that_is_not_paper_pdf_is_kept():
    m = index().by_dir["The-Quasi-Riemann-Hypothesis-October-5-2026"]
    assert m.file == "paper2.pdf" and "alternate 11/12 proof" in m.title


def test_the_directory_stem_drops_only_the_date():
    ix = index()
    assert ix.by_dir["The-Quasi-Riemann-Hypothesis-September-30-2026"].stem == "The-Quasi-Riemann-Hypothesis"
    assert ix.by_dir["The-Quasi-Riemann-Hypothesis-October-5-2026"].stem == "The-Quasi-Riemann-Hypothesis"


def test_a_map_with_nothing_in_it_is_not_an_index():
    async def go():
        class Empty(FakeFetch):
            async def __call__(self, url, **kw):
                return FetchResult(200, {}, b"# nothing here", url)
        return await omi.load_index(PIN, fetch=Empty(), use_cache=False)
    with pytest.raises(omi.RepoUnavailable):
        run(go())


# --- loading the map -------------------------------------------------------------------------------------------------------------
def test_the_map_is_fetched_from_the_raw_host_at_the_pinned_commit_only():
    f = FakeFetch()
    run(omi.load_index(PIN, fetch=f))
    url, kw = f.urls[0]
    assert url == f"https://raw.githubusercontent.com/openai/math/{PIN}/CONTENTS.md" and kw["allowed_hosts"] == ["raw.githubusercontent.com"]


def test_the_map_is_cached_per_commit():
    f = FakeFetch()
    run(omi.load_index(PIN, fetch=f))
    run(omi.load_index(PIN, fetch=f))
    assert len(f.urls) == 1


@pytest.mark.parametrize("bad", ["main", "HEAD", "7ef5c0cc5", PIN.upper(), PIN + "0", "", None, "../../etc"])
def test_a_commit_that_is_not_a_full_lowercase_id_is_refused(bad):
    with pytest.raises(omi.RepoUnavailable):
        run(omi.load_index(bad, fetch=FakeFetch()))


def test_a_failed_or_refused_fetch_is_unavailable_not_a_refusal_of_the_manuscript():
    with pytest.raises(omi.RepoUnavailable):
        run(omi.load_index(PIN, fetch=FakeFetch(map_status=503)))
    with pytest.raises(omi.RepoUnavailable):
        run(omi.load_index(PIN, fetch=FakeFetch(refuse="dns_failed")))


# --- naming a manuscript ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expect", [
    ("family 378", ("family", "378")), ("Family 003", ("family", "003")), ("openai/math family 157", ("family", "157")),
    ("family#378", ("family", "378")),
    ("preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026", ("path", "The-Exponential-Time-Hypothesis-is-False-October-25-2026")),
    ("https://github.com/openai/math/tree/7ef5c0cc5/preprints/A-counterexample-to-Hadwigers-conjecture-September-23-2026",
     ("path", "A-counterexample-to-Hadwigers-conjecture-September-23-2026")),
    ("https://github.com/openai/math/blob/main/preprints/Foo-September-23-2026/paper.pdf", ("path", "Foo-September-23-2026")),
    ("https://raw.githubusercontent.com/openai/math/abc/preprints/Foo%20Bar-October-1-2026/paper.pdf", ("path", "Foo Bar-October-1-2026"))])
def test_references_are_understood(raw, expect):
    assert omi.is_repo_reference(raw) and omi.parse_reference(raw) == expect


@pytest.mark.parametrize("raw", ["378", "family 37", "family 3789", "https://github.com/other/repo/tree/x/preprints/A",
                                 "https://example.org/preprints/A", "arXiv:2501.01234", "10.1000/xyz"])
def test_other_text_is_not_a_repository_reference(raw):
    assert not omi.is_repo_reference(raw)


def test_the_repository_address_that_names_no_manuscript_is_refused():
    with pytest.raises(ValueError):
        omi.parse_reference("https://github.com/openai/math")


def test_a_lookalike_repository_is_refused_not_treated_as_this_one():
    for url in ("https://github.com/openai/math-other/tree/x/preprints/Foo-October-1-2026",
                "https://github.com/openai/mathematics/blob/x/preprints/Foo-October-1-2026/paper.pdf"):
        assert omi.is_repo_reference(url)           # it mentions the repository's name, so it is looked at ...
        with pytest.raises(ValueError):             # ... and refused
            omi.parse_reference(url)


# --- resolving against the map --------------------------------------------------------------------------------------------------------
def test_a_family_with_distinct_manuscripts_expands_to_all_of_them():
    ms, why = omi.resolve(index(), "family", "157")
    assert why is None and len(ms) == 3
    ms, why = omi.resolve(index(), "family", "378")
    assert why is None and [m.dir for m in ms] == ["The-Exponential-Time-Hypothesis-is-False-October-25-2026"]


def test_a_family_whose_manuscripts_share_a_directory_name_is_refused_and_the_directories_are_listed():
    ms, why = omi.resolve(index(), "family", "003")
    assert ms == [] and why.reason == "ambiguous_family"
    assert "The-Quasi-Riemann-Hypothesis-September-30-2026" in why.directories and "The-Quasi-Riemann-Hypothesis-October-5-2026" in why.directories
    assert "Uniform-exclusion-of-Landau-Siegel-zeros-October-1-2026" not in why.directories


def test_naming_the_directory_resolves_an_otherwise_ambiguous_manuscript():
    ms, why = omi.resolve(index(), "path", "The-Quasi-Riemann-Hypothesis-September-30-2026")
    assert why is None and ms[0].family == "003" and ms[0].file == "paper.pdf"


def test_two_manuscripts_with_the_same_map_title_are_also_ambiguous():
    ix = index()
    fam = ix.families["157"]
    fam.manuscripts[1].title = fam.manuscripts[0].title
    ms, why = omi.resolve(ix, "family", "157")
    assert why.reason == "ambiguous_family"


def test_an_unknown_family_and_an_unknown_directory_are_refused_with_their_reasons():
    assert omi.resolve(index(), "family", "999")[1].reason == "unknown_family"
    for d in ("Algebraicity-of-Weil-classes-on-split-abelian-eightfolds-September-18-2026",     # a withdrawn manuscript: not in the map
              "The-Quasi-Riemann-Hypothesis-September-1-2026",                                   # an older edition: not in the map
              "../etc", ""):
        ms, why = omi.resolve(index(), "path", d)
        assert ms == [] and why.reason == "not_a_standing_manuscript"


# --- confirming existence at the commit -------------------------------------------------------------------------------------------------
ETH = "The-Exponential-Time-Hypothesis-is-False-October-25-2026"
TREES = {ETH: [("README.md", "blob", "4fed0453" + "0" * 32), ("build", "tree", "03fa5602" + "0" * 32), ("paper.pdf", "blob", "0503566e" + "0" * 32)]}


def test_a_manuscript_that_exists_is_confirmed_with_its_blob_ids_and_the_repository_text():
    m = index().by_dir[ETH]
    f = FakeFetch(trees=TREES)
    conf, why = run(omi.confirm_manuscript(m, PIN, fetch=f))
    assert why is None
    assert conf["status"] == "confirmed" and conf["source_class"] == "company_release" and conf["repo"] == "openai/math"
    assert conf["commit"] == PIN and conf["path"] == f"preprints/{ETH}" and conf["family"] == "378"
    assert conf["blob_sha"].startswith("0503566e") and conf["readme_blob_sha"].startswith("4fed0453")
    assert conf["title"] == m.title and conf["abstract"] == m.abstract and conf["authors"] == ["OpenAI"] and conf["year"] == 2026
    assert conf["url"].startswith(f"https://github.com/openai/math/tree/{PIN}/preprints/")
    url, kw = f.urls[0]
    assert url.startswith("https://api.github.com/repos/openai/math/git/trees/") and kw["allowed_hosts"] == ["api.github.com"]


def test_a_missing_directory_or_file_at_the_commit_is_a_refusal():
    m = index().by_dir[ETH]
    conf, why = run(omi.confirm_manuscript(m, PIN, fetch=FakeFetch(trees={})))
    assert conf is None and why.reason == "file_missing_at_commit"
    conf, why = run(omi.confirm_manuscript(m, PIN, fetch=FakeFetch(trees={ETH: [("README.md", "blob", "a" * 40)]})))
    assert conf is None and why.reason == "file_missing_at_commit"
    conf, why = run(omi.confirm_manuscript(m, PIN, fetch=FakeFetch(trees={ETH: [("paper.pdf", "tree", "a" * 40)]})))
    assert why.reason == "file_missing_at_commit"


def test_a_rate_limit_or_error_from_the_repository_is_unavailable_not_a_refusal():
    m = index().by_dir[ETH]
    for status in (403, 429, 500, 502):
        with pytest.raises(omi.RepoUnavailable):
            run(omi.confirm_manuscript(m, PIN, fetch=FakeFetch(trees=TREES, tree_status={ETH: status})))
    with pytest.raises(omi.RepoUnavailable):
        run(omi.confirm_manuscript(m, PIN, fetch=FakeFetch(refuse="address_not_public")))


# --- map formats seen in the real file that the excerpt does not contain ----------------------------------------------------------
SYNTHETIC = """
**901. A family with odd entries.** Description of the family.

&emsp;[Sharp integral fillings in CAT(0) spaces](preprints/Sharp-integral-fillings-in-CAT(0)-spaces-September-23-2026/paper.pdf)

An abstract with <i>markup</i> and $`math`$ in it.

</td>

&emsp;[A secondary item](preprints/A-secondary-item-September-24-2026/A-secondary-item-September-24-2026.pdf) - secondary writeup

Another abstract.

</td>
"""


def test_a_directory_name_with_parentheses_and_a_note_after_the_link_both_parse():
    ix = omi.parse_contents(SYNTHETIC, PIN)
    fam = ix.families["901"]
    assert [m.dir for m in fam.manuscripts] == ["Sharp-integral-fillings-in-CAT(0)-spaces-September-23-2026", "A-secondary-item-September-24-2026"]
    assert fam.manuscripts[0].file == "paper.pdf" and fam.manuscripts[0].note == ""
    assert fam.manuscripts[1].file == "A-secondary-item-September-24-2026.pdf" and fam.manuscripts[1].note == "secondary writeup"
    assert fam.manuscripts[0].abstract == "An abstract with markup and $`math`$ in it."


def test_a_manuscript_before_any_family_header_is_ignored_not_misfiled():
    ix = omi.parse_contents("&emsp;[Orphan](preprints/Orphan-October-1-2026/paper.pdf)\n\nText.\n\n", PIN)
    assert ix.by_dir == {} and ix.families == {}
