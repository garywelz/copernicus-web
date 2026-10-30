"""Result status from the pinned repository (design §4, reduced C3): per manuscript, from the manuscript map, the Lean catalogue, the withdrawal
notices and history.md; and the publish-day re-check. Offline: the repository is the fixtures' copy of the repository's own files."""
import asyncio
import copy
import json
import os

import pytest

import curated_sources as cs
import openai_math_index as omi
import openai_math_status as oms
from safe_fetch import FetchResult
from tests.unit.repo_fake import (CH, ETH, FakeRepo, HADWIGER, OLD_EDITION, QRH_OCT, QRH_SEPT, WEIL, fixture, standard_trees)

PIN = omi.DEFAULT_COMMIT
HEAD = "9" * 40


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def _clear():
    for c in (omi._INDEX_CACHE, oms._LEAN_CACHE, oms._HISTORY_CACHE):
        c.clear()
    yield
    for c in (omi._INDEX_CACHE, oms._LEAN_CACHE, oms._HISTORY_CACHE):
        c.clear()


def repo(**kw):
    return FakeRepo(trees=standard_trees(), **kw)


# --- the Lean catalogue ---------------------------------------------------------------------------------------------------------------
def test_the_lean_catalogue_lists_the_directories_of_its_sources_only():
    got = oms.parse_lean_sources(fixture("openai_math_formalization_excerpt.yaml"))
    assert got == {ETH, HADWIGER, CH, QRH_SEPT}


def test_ids_after_the_sources_section_are_not_sources():
    text = fixture("openai_math_formalization_excerpt.yaml") + "\nextra:\n  id: ../preprints/Not-A-Source-October-1-2026/paper.pdf\n"
    text = text.replace("related_formalizations:", "related_formalizations:\n  - id: ../preprints/Also-Not-A-Source-October-1-2026/x.pdf", 1)
    assert "Also-Not-A-Source-October-1-2026" not in oms.parse_lean_sources(text)
    assert "Not-A-Source-October-1-2026" not in oms.parse_lean_sources(text)


def test_an_unreadable_or_empty_catalogue_is_unavailable_not_an_empty_set():
    with pytest.raises(omi.RepoUnavailable):
        run(oms.load_lean_sources(PIN, FakeRepo(files={"lean/formalization.yaml": "version: 1\n"}), use_cache=False))
    with pytest.raises(omi.RepoUnavailable):
        run(oms.load_lean_sources(PIN, FakeRepo(raw_status={"lean/formalization.yaml": 503}), use_cache=False))
    with pytest.raises(omi.RepoUnavailable):
        run(oms.load_lean_sources("main", repo(), use_cache=False))


# --- withdrawal notices ------------------------------------------------------------------------------------------------------------------
def test_the_real_withdrawal_notice_is_read_in_full():
    n = oms.parse_notice(fixture("openai_math_withdrawn_readme.md"))
    assert n["title"] == "Algebraicity of Weil classes on split abelian eightfolds" and n["withdrawn_on"] == "October 6, 2026"
    assert n["explanation"].startswith("The proof contains a sign error in the stabilization-trace argument")
    assert n["archived_revision"] == "adc7f1241b42e322a6451854ab7e4b4c146bf78a"
    assert n["scope"].startswith("This withdrawal concerns the proof") and "false" in n["scope"]


def test_a_standing_readme_or_nothing_is_not_a_notice():
    assert oms.parse_notice(fixture("openai_math_standing_readme.md")) is None
    assert oms.parse_notice(None) is None and oms.parse_notice("") is None and oms.parse_notice("   \n") is None


def test_only_a_readme_that_starts_as_a_notice_counts():
    text = "# A normal manuscript\n\nSome text that mentions a Withdrawal notice: Something and Withdrawn on May 1, 2026.\n"
    assert oms.parse_notice(text) is None
    later = "# A normal manuscript\n\nText.\n\n# Withdrawal notice: Quoted from elsewhere\n\n**Withdrawn on May 1, 2026.**\n"
    assert oms.parse_notice(later) is None                          # a notice heading further down is not this manuscript's notice
    assert oms.parse_notice("# Withdrawal notice: A title\n\nOpenAI\n")["title"] == "A title"


# --- history.md -----------------------------------------------------------------------------------------------------------------------------
def test_the_changelogs_withdrawals_are_listed_with_their_dates():
    h = oms.parse_history(fixture("openai_math_history.md"))
    assert h == [{"date": "October 7, 2026", "titles": ["Algebraicity of Weil classes on split abelian eightfolds",
                                                          "Algebraicity of Kuga–Satake Correspondences for K3 Surfaces",
                                                          "The rational Hodge conjecture for products of K3 surfaces"]}]
    assert oms.history_dates_for("algebraicity of Weil classes on split abelian eightfolds", h) == ["October 7, 2026"]
    assert oms.history_dates_for("Something else", h) == [] and oms.parse_history("") == []


# --- the status of one manuscript ------------------------------------------------------------------------------------------------------------
def status_of(d, **kw):
    return run(oms.compute_status(PIN, d, kw.pop("fetch", None) or repo(**kw), use_cache=False))


def test_a_manuscript_in_the_catalogue_has_a_lean_formalization_and_one_that_is_not_is_unverified():
    assert status_of(ETH)["status"] == "has_lean_formalization"
    b = status_of(ETH)["basis"]
    assert b["in_lean_catalogue"] is True and b["lean_catalogue_entries"] == 4 and b["withdrawal_notice"] is False and b["commit"] == PIN
    assert status_of("Some-Other-Manuscript-October-1-2026")["status"] == "unverified"


def test_status_is_per_manuscript_inside_one_family():
    # family 003: the September 30 manuscript has a catalogue entry, the October 5 'alternate proof' does not
    assert status_of(QRH_SEPT)["status"] == "has_lean_formalization"
    assert status_of(QRH_OCT)["status"] == "unverified"


def test_a_withdrawn_manuscript_is_withdrawn_with_both_dates_recorded():
    s = status_of(WEIL)
    assert s["status"] == "withdrawn" and s["basis"]["withdrawal_notice"] is True
    w = s["basis"]["withdrawal"]
    assert w["withdrawn_on"] == "October 6, 2026" and w["history_dates"] == ["October 7, 2026"]      # the repository's own two dates differ


def test_withdrawn_beats_a_lean_entry():
    yaml = fixture("openai_math_formalization_excerpt.yaml").replace("sources:\n", f"sources:\n  - title: \"x\"\n    id: ../preprints/{WEIL}/paper.pdf\n    type: article\n\n", 1)
    assert status_of(WEIL, files={"lean/formalization.yaml": yaml})["status"] == "withdrawn"


def test_nothing_unreadable_is_guessed_as_unverified():
    with pytest.raises(omi.RepoUnavailable):
        status_of(ETH, raw_status={f"preprints/{ETH}/README.md": 503})
    with pytest.raises(omi.RepoUnavailable):
        status_of(ETH, raw_status={"lean/formalization.yaml": 500})


def test_a_missing_readme_is_recorded_not_invented():
    s = status_of("Directory-With-No-Readme-October-1-2026")
    assert s["status"] == "unverified" and s["basis"]["readme_present"] is False


# --- a withdrawn manuscript as content --------------------------------------------------------------------------------------------------------
def test_a_withdrawn_manuscript_outside_the_map_can_be_confirmed_as_content():
    conf, why = run(oms.withdrawn_manuscript(PIN, WEIL, repo()))
    assert why is None and conf["status"] == "confirmed" and conf["family"] is None and conf["file"] == "paper.pdf"
    assert conf["title"] == "Algebraicity of Weil classes on split abelian eightfolds" and conf["blob_sha"] == "9" * 40
    assert conf["abstract"].startswith("Withdrawn by OpenAI on October 6, 2026. The proof contains a sign error")
    assert conf["withdrawal"]["history_dates"] == ["October 7, 2026"] and conf["year"] == 2026


def test_an_older_edition_or_an_unknown_directory_is_not_content():
    conf, why = run(oms.withdrawn_manuscript(PIN, OLD_EDITION, repo()))
    assert conf is None and why.reason == "not_a_standing_manuscript"
    conf, why = run(oms.withdrawn_manuscript(PIN, ETH, repo()))                        # exists, standing README, but we only reach here if it is not in the map
    assert conf is None and "not a withdrawn manuscript" in why.detail
    with pytest.raises(omi.RepoUnavailable):
        run(oms.withdrawn_manuscript(PIN, WEIL, FakeRepo(trees=standard_trees(), tree_status={WEIL: 403})))


def test_pasting_a_withdrawn_directory_makes_a_company_release_item_with_status_withdrawn():
    items = run(cs.confirm_pasted(f"preprints/{WEIL}", PIN, fetch=repo()))
    assert len(items) == 1
    it = items[0]
    assert it["class"] == "company_release" and it["result_status"] == "withdrawn" and it["confirmation"]["status"] == "confirmed"
    assert it["identifiers"]["family"] is None and it["status_basis"]["withdrawal"]["withdrawn_on"] == "October 6, 2026"
    assert it["evidence_text"].startswith("Withdrawn by OpenAI on October 6, 2026")


def test_an_old_edition_pasted_is_still_refused():
    it = run(cs.confirm_pasted(f"preprints/{OLD_EDITION}", PIN, fetch=repo()))[0]
    assert it["confirmation"]["status"] == "refused" and it["confirmation"]["reason"] == "not_a_standing_manuscript"


def test_pasting_a_standing_manuscript_records_its_status_and_the_basis():
    it = run(cs.confirm_pasted(f"preprints/{QRH_OCT}", PIN, fetch=repo()))[0]
    assert it["result_status"] == "unverified" and it["status_basis"]["in_lean_catalogue"] is False
    it = run(cs.confirm_pasted(f"preprints/{QRH_SEPT}", PIN, fetch=repo()))[0]
    assert it["result_status"] == "has_lean_formalization"


# --- the rules the list applies ----------------------------------------------------------------------------------------------------------------
def make(cls, n, status=None):
    ids = {"doi": f"10.1000/{cls}{n}"}
    it = {"item_id": cs.item_id(ids), "class": cls, "identifiers": ids, "title": f"T{n}", "evidence_text": "e", "confirmation": {"status": "confirmed"},
          "approved": True}
    if status:
        it["result_status"] = status
    return it


def test_a_withdrawn_manuscript_never_counts_toward_the_three_sources():
    two = [make("preprint", 1), make("peer_reviewed", 2)]
    ok, counts = cs.minimum_check(two + [make("company_release", 3, "withdrawn")])
    assert not ok and counts["non_commentary"] == 2 and counts["withdrawn"] == 1
    ok, counts = cs.minimum_check(two + [make("company_release", 3, "withdrawn"), make("company_release", 4, "unverified")])
    assert ok and counts["non_commentary"] == 3


def test_the_list_hash_changes_when_a_status_changes():
    pin = {"repo": "openai/math", "commit": PIN}
    a = [make("company_release", 1, "unverified")]
    b = [make("company_release", 1, "has_lean_formalization")]
    assert cs.list_hash(pin, a) != cs.list_hash(pin, b)
    assert cs.list_hash(pin, a) == cs.list_hash(pin, copy.deepcopy(a))


# --- the publish-day re-check ---------------------------------------------------------------------------------------------------------------------
def list_items(fetch=None):
    fetch = fetch or repo()
    paths = [ETH, HADWIGER, WEIL]
    return [run(cs.confirm_pasted(f"preprints/{p}", PIN, fetch=repo()))[0] for p in paths]


def recheck(items, head_repo):
    omi._INDEX_CACHE.clear()
    return {r["path"].split("/")[-1]: r for r in run(oms.recheck_items(items, HEAD, head_repo))}


def test_nothing_changed_means_no_row_changed():
    rows = recheck(list_items(), repo())
    assert len(rows) == 3 and not any(r["changed"] for r in rows.values())
    assert rows[WEIL]["recorded"] == "withdrawn" and rows[WEIL]["current"] == "withdrawn" and rows[ETH]["current"] == "has_lean_formalization"


def test_a_new_withdrawal_at_the_head_is_a_change():
    items = list_items()
    readme = "# Withdrawal notice: The Exponential Time Hypothesis is False\n\nOpenAI  \n**Withdrawn on November 3, 2026.**\n\nA gap was found.\n"
    rows = recheck(items, repo(files={f"preprints/{ETH}/README.md": readme}))
    assert rows[ETH]["changed"] and rows[ETH]["recorded"] == "has_lean_formalization" and rows[ETH]["current"] == "withdrawn"
    assert not rows[HADWIGER]["changed"]


def test_a_lean_entry_removed_at_the_head_is_a_change():
    y = fixture("openai_math_formalization_excerpt.yaml")
    y = y.replace(f"id: ../preprints/{HADWIGER}/paper.pdf", f"id: ../elsewhere/{HADWIGER}/paper.pdf")
    rows = recheck(list_items(), repo(files={"lean/formalization.yaml": y}))
    assert rows[HADWIGER]["changed"] and rows[HADWIGER]["current"] == "unverified"


def test_a_manuscript_file_that_changed_since_the_pin_is_flagged():
    trees = standard_trees()
    trees[ETH] = [("paper.pdf", "z"), ("README.md", "b")]
    rows = recheck(list_items(), FakeRepo(trees=trees))
    assert rows[ETH]["changed"] and any("file has changed" in n for n in rows[ETH]["notes"])


def test_a_manuscript_no_longer_in_the_map_is_flagged():
    stripped = fixture("openai_math_contents_excerpt.md")
    start = stripped.index("&emsp;[The Exponential Time Hypothesis is False]")
    end = stripped.index("</td>", start)
    stripped = stripped[:start] + stripped[end:]
    rows = recheck(list_items(), repo(files={"CONTENTS.md": stripped}))
    assert rows[ETH]["changed"] and rows[ETH]["current"] == "not_standing" and any("no longer in the manuscript map" in n for n in rows[ETH]["notes"])


def test_a_withdrawn_manuscript_that_is_back_in_the_map_is_flagged():
    contents = fixture("openai_math_contents_excerpt.md").replace(
        "&emsp;[The Exponential Time Hypothesis is False]", f"&emsp;[Back](preprints/{WEIL}/paper.pdf)\n\nAbstract.\n\n</td>\n\n&emsp;[The Exponential Time Hypothesis is False]", 1)
    rows = recheck(list_items(), repo(files={"CONTENTS.md": contents}))
    assert rows[WEIL]["changed"] and any("back in the manuscript map" in n for n in rows[WEIL]["notes"])


def test_an_unreadable_head_is_reported_as_unreadable_not_as_unchanged():
    rows = recheck(list_items(), repo(raw_status={f"preprints/{ETH}/README.md": 503}))
    assert rows[ETH]["current"] == "unreadable" and rows[ETH]["changed"]


def test_only_company_releases_are_rechecked():
    rows = run(oms.recheck_items([make("preprint", 1), make("peer_reviewed", 2)], HEAD, repo()))
    assert rows == []


# --- finding the head ---------------------------------------------------------------------------------------------------------------------------------
class ApiFake:
    def __init__(self, branch="main", sha=HEAD, status=200):
        self.branch, self.sha, self.status, self.urls = branch, sha, status, []

    async def __call__(self, url, **kw):
        self.urls.append(url)
        if url.endswith("/repos/openai/math"):
            return FetchResult(self.status, {}, json.dumps({"default_branch": self.branch}).encode(), url)
        return FetchResult(self.status, {}, json.dumps({"sha": self.sha}).encode(), url)


def test_the_head_is_the_tip_of_the_default_branch():
    f = ApiFake(branch="release/1")
    assert run(oms.resolve_head(f)) == HEAD and f.urls[1].endswith("/commits/release%2F1")


@pytest.mark.parametrize("fake", [ApiFake(status=403), ApiFake(sha="not-a-sha"), ApiFake(branch=None)])
def test_a_head_that_cannot_be_found_is_unavailable(fake):
    with pytest.raises(omi.RepoUnavailable):
        run(oms.resolve_head(fake))


def test_a_checked_by_item_is_compared_with_the_status_the_repository_gave_it_before_experts_were_cited():
    items = list_items()
    eth = next(i for i in items if i["confirmation"]["path"].endswith(ETH))
    assert eth["result_status"] == "has_lean_formalization"
    eth["status_basis"] = dict(eth.get("status_basis") or {}, checked_by={"commentary_item_id": "c1", "quote": "x" * 30, "previous_status": "has_lean_formalization"})
    eth["result_status"] = "checked_by_experts"
    assert oms.repository_baseline(eth) == "has_lean_formalization"
    rows = recheck(items, repo())
    row = rows[ETH]
    assert row["recorded"] == "checked_by_experts" and row["baseline"] == "has_lean_formalization" and row["current"] == "has_lean_formalization"
    assert row["changed"] is False
    assert oms.repository_baseline({"result_status": "withdrawn"}) == "withdrawn" and oms.repository_baseline({"result_status": "checked_by_experts"}) == "unverified"
