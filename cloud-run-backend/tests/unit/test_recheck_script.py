"""The publish-day re-check command (design §4.3): `scripts/recheck_curated_statuses.py`. Offline: the list is a fake database row and the repository is the
fixtures' copy. The command reads and writes nothing else."""
import asyncio
import importlib.util
import json
import os

import pytest

import curated_sources as cs
import openai_math_index as omi
import openai_math_status as oms
from tests.unit.repo_fake import ETH, HADWIGER, WEIL, FakeRepo, fixture, standard_trees

BACKEND = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("recheck_curated_statuses", os.path.join(BACKEND, "scripts", "recheck_curated_statuses.py"))
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)

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


class ReadOnlyDB:
    """A one-document database that fails the test if anything is written."""

    def __init__(self, doc, private=None):
        self.doc, self.private, self.reads, self._name = doc, private or {}, [], None

    def collection(self, name):
        assert name in (script.COLLECTION, script.PRIVATE_COLLECTION)
        self._name = name
        return self

    def document(self, doc_id):
        self.reads.append(doc_id)
        db, name = self, self._name

        class Ref:
            def get(self_r):
                class Snap:
                    exists = (db.doc is not None) if name == script.COLLECTION else doc_id in db.private

                    def to_dict(s):
                        return db.doc if name == script.COLLECTION else {"text": db.private[doc_id]}
                return Snap()

            def set(self_r, *a, **k):
                raise AssertionError("the re-check must not write")
            update = delete = create = set
        return Ref()


def approved_doc():
    items = [run(cs.confirm_pasted(f"preprints/{p}", PIN, fetch=FakeRepo(trees=standard_trees())))[0] for p in (ETH, HADWIGER, WEIL)]
    return {"list_id": "L1", "status": "approved", "list_hash": "h" * 64, "pin": {"repo": "openai/math", "commit": PIN}, "items": items}


class Repo(FakeRepo):
    """FakeRepo plus the two API answers that find the head."""

    async def __call__(self, url, **kw):
        if url.endswith("/repos/openai/math"):
            from safe_fetch import FetchResult
            return FetchResult(200, {}, json.dumps({"default_branch": "main"}).encode(), url)
        if "/commits/" in url:
            from safe_fetch import FetchResult
            return FetchResult(200, {}, json.dumps({"sha": HEAD}).encode(), url)
        return await super().__call__(url, **kw)


def go(args, doc=None, repo=None, capsys=None, private=None):
    db = ReadOnlyDB(approved_doc() if doc is None else doc, private)
    code = script.main(args, db=db, fetch=repo or Repo(trees=standard_trees()))
    return code, db


def test_nothing_changed_exits_zero_and_says_publication_may_go_ahead(capsys):
    code, db = go(["L1"])
    out = capsys.readouterr().out
    assert code == 0 and "publication may go ahead" in out and "DO NOT PUBLISH" not in out and db.reads == ["L1"]
    assert "pinned commit 7ef5c0cc5" in out and "head now 999999999" in out and "the repository has moved" in out


def test_a_change_exits_two_and_says_do_not_publish(capsys):
    readme = "# Withdrawal notice: The Exponential Time Hypothesis is False\n\nOpenAI  \n**Withdrawn on November 3, 2026.**\n\nA gap was found.\n"
    code, _ = go(["L1"], repo=Repo(trees=standard_trees(), files={f"preprints/{ETH}/README.md": readme}))
    out = capsys.readouterr().out
    assert code == 2 and "DO NOT PUBLISH: 1 item(s) changed" in out and "CHANGED" in out and "has_lean_formalization" in out and "withdrawn" in out


def test_the_head_can_be_given_and_must_be_a_full_commit_id(capsys):
    assert go(["L1", "--head", "main"])[0] == 1
    assert go(["L1", "--head", ("a" * 40).upper()])[0] == 1
    assert go(["L1", "--head", "8" * 40])[0] == 0
    assert go([])[0] == 1                                          # no list id: usage error, not a crash


def test_an_unknown_list_or_an_unreadable_repository_exits_three_and_checks_nothing(capsys):
    db = ReadOnlyDB(None)
    assert script.main(["nope"], db=db, fetch=Repo(trees=standard_trees())) == 3
    assert "no source list" in capsys.readouterr().err
    code, _ = go(["L1"], repo=Repo(trees=standard_trees(), raw_status={"CONTENTS.md": 503}, map_status=503))
    assert code == 3 and "could not check" in capsys.readouterr().err
    code, _ = go(["L1"], repo=Repo(trees=standard_trees(), raw_status={f"preprints/{ETH}/README.md": 503}))
    assert code == 3                                              # one manuscript unreadable: not "unchanged"


def test_json_output_has_the_rows(capsys):
    code, _ = go(["L1", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0 and data["head"] == HEAD and len(data["rows"]) == 3 and {r["recorded"] for r in data["rows"]} == {"has_lean_formalization", "withdrawn"}


def test_a_list_without_company_releases_has_nothing_to_check(capsys):
    doc = approved_doc()
    doc["items"] = [i for i in doc["items"] if False]
    code, _ = go(["L1"], doc=doc)
    assert code == 0 and "nothing to re-check" in capsys.readouterr().out


def test_the_command_never_writes(capsys):
    go(["L1"])                                                     # ReadOnlyDB raises on any set, update, delete or create
    go(["L1", "--json"])


def test_the_runbook_names_the_command_and_its_exit_codes():
    text = open(os.path.join(os.path.dirname(BACKEND), "docs", "runbooks", "CURATED_STATUS_RECHECK.md"), encoding="utf-8").read()
    assert "scripts/recheck_curated_statuses.py" in text and "DO NOT PUBLISH" in text and "| 2 |" in text and "Exit code" in text and "rule 16" in text


# --- an item marked `checked by experts` -------------------------------------------------------------------------------------------------
TEXT = ("Mathematicians have been studying the paper intensely. These experts largely agree that the result is correct, and that its novelty lies "
        "in the way it brings together ideas from number theory that have been around for some time. " * 2)
QUOTE = "These experts largely agree that the result is correct"


def checked_doc(text=TEXT, quote=QUOTE):
    doc = approved_doc()
    src, stored = cs.build_commentary_item("A report", "Quanta Magazine", ["A Writer"], "2026-10-19", text, url="https://example.org/a")
    src["item_id"] = "c1"
    target = next(i for i in doc["items"] if i.get("result_status") == "has_lean_formalization")
    target["status_basis"] = dict(target.get("status_basis") or {}, checked_by={"commentary_item_id": "c1", "quote": quote,
                                                                              "previous_status": target["result_status"]})
    target["result_status"], target["checked_by"] = "checked_by_experts", "Quanta Magazine"
    doc["items"].append(src)
    return doc, stored


def test_a_checked_by_item_on_an_unchanged_repository_exits_zero_and_prints_both_results(capsys):
    doc, stored = checked_doc()
    code, db = go(["L1"], doc=doc, private={"L1__c1": stored})
    out = capsys.readouterr().out
    assert code == 0 and "publication may go ahead" in out
    assert "has_lean_formalization (+experts)" in out and "quoted sentence found" in out and "text hash matches" in out
    assert stored[:40] not in out                                         # the private text is never printed


def test_a_repository_change_under_a_checked_by_item_exits_two(capsys):
    doc, stored = checked_doc()
    target = next(i for i in doc["items"] if i.get("result_status") == "checked_by_experts")
    path_dir = target["confirmation"]["path"].split("preprints/", 1)[-1]
    notice = "\n".join(["# Withdrawal notice: " + target["title"], "", "OpenAI  ", "**Withdrawn on November 3, 2026.**", "", "A gap was found.", ""])
    code, _ = go(["L1"], doc=doc, repo=Repo(trees=standard_trees(), files={f"preprints/{path_dir}/README.md": notice}), private={"L1__c1": stored})
    out = capsys.readouterr().out
    assert code == 2 and "DO NOT PUBLISH" in out and "CHANGED" in out and "withdrawn" in out



def test_a_quotation_missing_from_the_text_exits_two(capsys):
    doc, stored = checked_doc(quote="Every expert agrees the result is wrong")
    code, _ = go(["L1"], doc=doc, private={"L1__c1": stored})
    out = capsys.readouterr().out
    assert code == 2 and "NOT found" in out and "no longer occurs" in out and "checked-by item(s) no longer match" in out


def test_a_text_that_no_longer_matches_its_hash_exits_two(capsys):
    doc, stored = checked_doc()
    code, _ = go(["L1"], doc=doc, private={"L1__c1": stored + " An edit."})
    out = capsys.readouterr().out
    assert code == 2 and "DOES NOT match" in out


def test_a_missing_private_text_exits_two_and_the_json_has_the_rows(capsys):
    doc, stored = checked_doc()
    code, _ = go(["L1", "--json"], doc=doc, private={})
    data = json.loads(capsys.readouterr().out)
    assert code == 2 and data["checked_by"][0]["ok"] is False and "could not be found" in data["checked_by"][0]["notes"][0]
    assert all("baseline" in r for r in data["rows"])
