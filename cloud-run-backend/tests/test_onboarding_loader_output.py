"""Onboarding PR 4b-1, BULLETIN 042 finding F1: scripts/onboarding/load_engine.py writes UTF-8 whatever the console's code page is.

On Windows, with its output redirected to a file, the loader wrote in the code page: the dash in each skipped hold-list line came out as the single byte 0x97,
which is not UTF-8, and a character outside the code page would have stopped the run. These tests RUN THE SCRIPT as a separate process under three console
encodings, offline, against the synthetic fixture (no Firestore, no network), and read its output as bytes. The last test is the control: the same text printed
without the fix does fail in both ways."""
import os
import subprocess
import sys

import pytest

from tests.test_onboarding_loader import ENGINE, REPO, ROOT, SHA, tree

SCRIPT = ROOT / "scripts" / "onboarding" / "load_engine.py"
DASH, FOR_ALL, ALPHA = "—", "∀", "α"          # the dash is in cp1252 (as byte 0x97); the other two are in neither cp1252 nor ASCII


def _env(encoding):
    return {**os.environ, "PYTHONIOENCODING": encoding, "PYTHONUTF8": "0"}


def _run_script(files_dir, encoding):
    return subprocess.run([sys.executable, str(SCRIPT), "--engine-id", ENGINE, "--repo", REPO, "--commit", SHA, "--files-dir", str(files_dir), "--offline"],
                          capture_output=True, env=_env(encoding), timeout=120)


@pytest.mark.parametrize("encoding", ["cp1252", "ascii", "utf-8"])
def test_the_script_output_is_utf8_under_any_console_code_page_and_a_character_outside_it_does_not_stop_the_run(tmp_path, encoding):
    d = tree(tmp_path)
    hold = d / "docs" / "hold_list.md"
    before = hold.read_text(encoding="utf-8")
    legend = f"- `cited_by=N` {DASH} synthetic legend line"
    assert legend in before
    hold.write_text(before.replace(legend, f"- `cited_by=N` {DASH} for all {FOR_ALL} and {ALPHA}"), encoding="utf-8")
    r = _run_script(d, encoding)
    out = r.stdout.decode("utf-8")                              # raises if a single byte is not UTF-8
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert f"{DASH} synthetic legend line" in out and f"{DASH} for all {FOR_ALL} and {ALPHA}" in out and "65 hold-list candidates (4 likely keep)" in out
    assert bytes([0x97]) not in r.stdout and "\\u2014" not in out and "\\u2200" not in out, "written as the characters themselves, not as bytes of a code page or as escapes"


def test_an_error_message_is_utf8_too(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--engine-id", ENGINE, "--repo", REPO, "--commit", "short"], capture_output=True, env=_env("cp1252"), timeout=120)
    assert r.returncode == 2 and "full 40-character sha" in r.stderr.decode("utf-8")


def test_without_the_fix_the_same_text_fails_in_both_ways_which_is_what_the_tests_above_would_catch():
    dash = subprocess.run([sys.executable, "-c", f"print('a {DASH} b')"], capture_output=True, env=_env("cp1252"), timeout=60)
    assert dash.returncode == 0 and bytes([0x97]) in dash.stdout
    with pytest.raises(UnicodeDecodeError):
        dash.stdout.decode("utf-8")
    assert subprocess.run([sys.executable, "-c", f"print('{FOR_ALL}')"], capture_output=True, env=_env("cp1252"), timeout=60).returncode != 0
    source = SCRIPT.read_text(encoding="utf-8")
    head, _, tail = source.partition('if __name__ == "__main__":')
    assert 'stream.reconfigure(encoding="utf-8", errors="backslashreplace")' in head and tail.strip().startswith("utf8_output()")
