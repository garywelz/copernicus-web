"""Tests for governance/check_citations.py: what it must still report as DEAD, and the two new, carefully scoped ways a citation can resolve.
Each test builds a tiny git repository in a temporary folder (the checker reads `git ls-files` and the working directory).

Run from the repo root:  python -m pytest governance/tests -q
"""
import importlib.util
import pathlib
import subprocess

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "check_citations.py"


def load():
    spec = importlib.util.spec_from_file_location("check_citations_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway repo: files are written and `git add`-ed; the governance doc is written by each test."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q"], check=True)

    def build(files, doc_lines, untracked=()):
        for rel in files:
            f = tmp_path / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], check=True)
        for rel in untracked:
            f = tmp_path / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x\n", encoding="utf-8")
        doc = tmp_path / "governance" / "doc.md"
        doc.parent.mkdir(exist_ok=True)
        doc.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "governance/doc.md"], check=True)
        return load()

    return build


def run(mod):
    return mod.check(["governance/doc.md"])


# ---------------------------------------------------------------- still DEAD (the negative tests)
def test_a_made_up_path_is_dead(repo):
    mod = repo(["cloud-run-backend/main.py"], ["See `does/not/exist.py` for the proof."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert [e[2] for e in errors] == ["does/not/exist.py"] and not warnings and not sibling and ok == 0


def test_a_prefixless_path_that_exists_under_neither_base_is_dead(repo):
    mod = repo(["cloud-run-backend/endpoints/papers/routes.py", "docs/x.md"], ["`endpoints/nothing/here.py` and `routes/papers/routes.py`"])
    errors, warnings, *_ = run(mod)
    assert sorted(e[2] for e in errors) == ["endpoints/nothing/here.py", "routes/papers/routes.py"] and not warnings


def test_a_bare_filename_not_on_the_allowlist_is_dead(repo):
    mod = repo(["cloud-run-backend/main.py"], ["The helper `stray_script.py` does it."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert [e[2] for e in errors] == ["stray_script.py"] and not sibling


def test_a_sibling_name_without_the_sibling_repo_on_its_line_is_dead(repo):
    mod = repo(["cloud-run-backend/main.py"], ["`run_batch.py` writes the output.", "Per atap PR 9, `select_batch.py` reads it."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert sorted(e[2] for e in errors) == ["run_batch.py", "select_batch.py"] and not sibling       # only glmp on the same line counts


# ---------------------------------------------------------------- the two new, scoped resolutions
def test_a_sibling_name_is_accepted_only_with_glmp_on_the_line_and_is_listed(repo):
    mod = repo(["cloud-run-backend/main.py"], ["`glmp` PR #22 (`run_batch.py` writes the circuits; `select_batch.py` reads them)"])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert not errors and len(sibling) == 2
    where = {s[2]: s[3] for s in sibling}
    assert where["run_batch.py"] == "glmp:collaborations/krampis-virtual-cell/dna-decoder/scripts/run_batch.py"
    assert "f601fa2" in sibling[0][4]
    assert mod.main() in (0, 1)   # printing works


def test_the_backend_prefix_fallback_is_imprecise_never_ok(repo, capsys):
    mod = repo(["cloud-run-backend/endpoints/papers/routes.py"], ["Minted at `endpoints/papers/routes.py:77`."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert not errors and ok == 0                                                   # not counted as resolved
    assert len(warnings) == 1
    doc, line, cited, found, note = warnings[0]
    assert cited == "endpoints/papers/routes.py" and found == "cloud-run-backend/endpoints/papers/routes.py" and note == "resolved via cloud-run-backend/ prefix"
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "IMPRECISE" in out and "resolved via cloud-run-backend/ prefix" in out


def test_a_path_that_resolves_both_ways_to_different_files_is_ambiguous_and_fails(repo, capsys):
    mod = repo(["shared/foo.py", "cloud-run-backend/shared/foo.py"], ["Look at `shared/foo.py`."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert not errors and ok == 0 and len(ambiguous) == 1 and ambiguous[0][2] == "shared/foo.py"
    assert mod.main() == 1
    assert "AMBIGUOUS" in capsys.readouterr().out


# ---------------------------------------------------------------- unchanged behaviour
def test_an_exact_tracked_path_is_ok(repo):
    mod = repo(["cloud-run-backend/main.py"], ["`cloud-run-backend/main.py:85`"])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert ok == 1 and not errors and not warnings and not ambiguous


def test_an_untracked_file_still_fails(repo):
    mod = repo(["cloud-run-backend/main.py"], ["`notes/local_only.md`"], untracked=["notes/local_only.md"])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert [u[2] for u in untracked] == ["notes/local_only.md"] and not errors


def test_the_archived_marker_still_skips(repo):
    mod = repo(["cloud-run-backend/main.py"], ["`gone/old.py` (archived) was moved."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert skipped == 1 and not errors


def test_bare_filenames_that_exist_elsewhere_stay_imprecise(repo):
    mod = repo(["cloud-run-backend/main.py"], ["The entry point `main.py`."])
    errors, warnings, untracked, skipped, ok, ambiguous, sibling = run(mod)
    assert ok == 1 and len(warnings) == 1 and warnings[0][4] == "bare filename, resolves elsewhere in tree" and not errors
