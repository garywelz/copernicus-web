"""PR 4c-2 (finding 3 of the attended look at tdap, 2026-11-18): the loader reads the scope from the engine's README.md by the SAME rule the bundle writes it
by, so loading and exporting cannot disagree. With a Scope heading, the statement and the out-of-scope list are pre-filled from it; with none (the real tdap
at b384da6), the statement starts empty and the README's opening paragraph is offered as read-only reference (Gary, 2026-11-18). Synthetic text only."""
import pytest

from tests.test_onboarding_loader import ENGINE, LINE, SHA, engine_db, le, run, snapshot, tree, web  # noqa: F401  (web is a fixture)
from utils import onboarding_render as render

TITLE = "# A Synthetic Engine (SYN)\n\n"
OPENING = "SYN studies synthetic structure in synthetic data, and where that structure can be found in domains not built for it."
CONTACT = "*A maintainer · A Lab · [owner@example.org](mailto:owner@example.org)*"


def readme(body):
    return TITLE + body


def scope_items(plan):
    return {i["item_id"]: i for i in plan["items"] if i["section"] == "scope"}


# ---- read_scope: the renderer's own rule, read back --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("statement,out_of_scope", [
    ("What the engine is for.", []),
    ("What the engine is for.\n\nAnd a second paragraph about who uses it.", ["clinical advice", "anything before 1950"]),
    ("", ["only an out-of-scope list"]),
])
@pytest.mark.parametrize("base", [
    readme(OPENING + "\n\n## Scope\n\nAn older scope.\n\n## Background\n\nText.\n"),        # an existing Scope heading, followed by another section
    readme(OPENING + "\n\n## What lives here\n\nFiles.\n"),                                  # no Scope heading: the renderer appends one
    None,                                                                                     # no README: the paragraph is the whole file
])
def test_what_the_bundle_writes_the_loader_reads_back_exactly(base, statement, out_of_scope):
    items = [{"item_id": "scope-statement", "value": statement}, {"item_id": "out-of-scope", "value": out_of_scope}]
    paragraph = render.scope_paragraph(items)
    written, _ = render.render_readme(base, paragraph)
    if not paragraph:
        return
    got = render.read_scope(written)
    assert (got["statement"], got["out_of_scope"]) == (statement, out_of_scope)
    assert got["heading"] and render.SCOPE_HEADING_RE.match(got["heading"])


def test_with_no_scope_heading_the_statement_is_empty_and_the_opening_paragraph_is_reference_only():
    got = render.read_scope(readme(OPENING + "\n\n" + CONTACT + "\n\n---\n\n## What lives here\n\nFiles.\n"))
    assert got == {"heading": None, "statement": "", "out_of_scope": [], "opening": OPENING}
    assert render.read_scope(None) == {"heading": None, "statement": "", "out_of_scope": [], "opening": ""}
    for not_a_paragraph in ("---\n\nText.", "- a list item", "| a | table |", "## A heading", "<div>html</div>"):
        assert render.read_scope(readme(not_a_paragraph + "\n"))["opening"] == ""


def test_the_scope_body_stops_at_the_next_heading_of_the_same_or_a_higher_level():
    text = readme("## Scope and use case\n\nThe statement.\n\n### A detail inside the scope\n\nMore of it.\n\n## Licence\n\nCC0.\n")
    assert render.read_scope(text)["statement"] == "The statement.\n\n### A detail inside the scope\n\nMore of it."


# ---- the loader's plan -------------------------------------------------------------------------------------------------------------------------------------
def test_every_load_plans_the_three_scope_items_unanswered_in_order(tmp_path):
    root = tree(tmp_path)
    (root / "README.md").write_text(readme(OPENING + "\n\n## Scope\n\nWhat SYN is for.\n\nOut of scope: weather; markets.\n"), encoding="utf-8")
    texts = le.fetch(None, SHA, files_dir=root)
    items = scope_items(le.build_plan(ENGINE, texts))
    assert list(items) == ["scope-statement", "use-case", "out-of-scope"] and [items[k]["order"] for k in items] == [0, 1, 2]
    assert (items["scope-statement"]["type"], items["scope-statement"]["value"]) == ("scope_statement", "What SYN is for.")
    assert (items["out-of-scope"]["type"], items["out-of-scope"]["value"]) == ("out_of_scope", ["weather", "markets"])
    assert (items["use-case"]["type"], items["use-case"]["value"]) == ("use_case", "")                     # never a repository file: it starts empty
    assert items["scope-statement"]["context"]["source"] == "README.md, under '## Scope'" and "reference" not in items["scope-statement"]["context"]
    assert le.counts(le.build_plan(ENGINE, texts))["scope_items"] == 3


def test_a_readme_without_a_scope_heading_gives_an_empty_statement_and_the_opening_paragraph_as_reference(tmp_path):
    root = tree(tmp_path)
    (root / "README.md").write_text(readme(OPENING + "\n\n" + CONTACT + "\n\n## What lives here\n\nFiles.\n"), encoding="utf-8")
    items = scope_items(le.build_plan(ENGINE, le.fetch(None, SHA, files_dir=root)))       # the contact line's address is not read, so it refuses nothing
    s = items["scope-statement"]
    assert s["value"] == "" and items["out-of-scope"]["value"] == []
    assert s["context"]["reference"] == OPENING and "no Scope heading" in s["context"]["source"]
    assert "example.org" not in repr(items)


def test_with_no_readme_the_three_items_still_exist_and_are_empty(tmp_path):
    items = scope_items(le.build_plan(ENGINE, le.fetch(None, SHA, files_dir=tree(tmp_path))))
    assert [items[k]["value"] for k in ("scope-statement", "use-case", "out-of-scope")] == ["", "", []]
    assert "absent" in items["scope-statement"]["context"]["source"]


@pytest.mark.parametrize("bad", ["Write to owner@example.org for more.", "A <script>alert(1)</script> statement.", "x" * 2001])
def test_hostile_or_over_cap_text_under_the_scope_heading_refuses_the_load(tmp_path, bad):
    root = tree(tmp_path)
    (root / "README.md").write_text(readme("## Scope\n\n" + bad + "\n"), encoding="utf-8")
    with pytest.raises(le.Refused):
        le.build_plan(ENGINE, le.fetch(None, SHA, files_dir=root))


def test_an_opening_paragraph_the_checks_would_refuse_is_left_out_with_a_note_and_the_load_goes_on(tmp_path):
    root = tree(tmp_path)
    (root / "README.md").write_text(readme("SYN, written up by owner@example.org, studies things.\n\n## Files\n\nFiles.\n"), encoding="utf-8")
    plan = le.build_plan(ENGINE, le.fetch(None, SHA, files_dir=root))
    assert "reference" not in scope_items(plan)["scope-statement"]["context"]
    assert any("opening paragraph is not shown as reference" in n for n in plan["notes"])


# ---- applied, and loaded again ------------------------------------------------------------------------------------------------------------------------------
def test_a_load_writes_the_scope_items_and_a_second_load_at_the_same_commit_writes_nothing(web, tmp_path, capsys):
    root = tree(tmp_path)
    (root / "README.md").write_text(readme(OPENING + "\n\n## Files\n\nFiles.\n"), encoding="utf-8")
    web.set(SHA, root)
    db = engine_db()
    code, out, _ = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 0 and "3 scope items, " in out and "README.md" in out
    stored = {d["item_id"]: d for d in db.data[le.ITEMS].values() if d["section"] == "scope"}
    assert set(stored) == {"scope-statement", "use-case", "out-of-scope"}
    assert all(d["revision"] == 0 and d["choice"] is None and not d.get("author_subscriber_id") for d in stored.values())      # unanswered, like every loaded item
    assert stored["scope-statement"]["context"]["reference"] == OPENING
    before = snapshot(db)
    code, out, _ = run(["--apply", "--approval", LINE], db, capsys)
    assert code == 0 and snapshot(db) == before                                                                                # nothing at all the second time


def test_an_engine_loaded_before_4c2_gains_only_the_three_scope_items_and_nothing_else_changes(web, tmp_path, capsys, monkeypatch):
    """What the planned re-load of tdap at the same commit will do: create three items and leave every existing item exactly as it is."""
    root = tree(tmp_path)
    web.set(SHA, root)
    db = engine_db()
    real = le.parse_scope
    monkeypatch.setattr(le, "parse_scope", lambda text: ([], []))                     # the loader as it was before 4c-2: no scope items
    assert run(["--apply", "--approval", LINE], db, capsys)[0] == 0
    first = snapshot(db)
    monkeypatch.setattr(le, "parse_scope", real)
    code, out, _ = run([], db, capsys)
    assert code == 0 and "3 create, 0 update" in out and "0 conflict" in out
    assert run(["--apply", "--approval", LINE], db, capsys)[0] == 0
    after = db.data[le.ITEMS]
    assert {k for k in after if k not in first[le.ITEMS]} == {f"{ENGINE}__scope__scope-statement", f"{ENGINE}__scope__use-case", f"{ENGINE}__scope__out-of-scope"}
    assert all(after[k] == v for k, v in first[le.ITEMS].items())
