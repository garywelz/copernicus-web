"""One public channel name, set in one place (cloud-run-backend/channel.py), and the old name "Frontiers of Science" gone from live code, prompts and docs."""
import os
import re
import subprocess

import channel
import curated_mode as cm
import curated_script as cscript
import series_thumbnail as st

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OLD = "Frontiers of Science"
# kept on purpose: append-only history, verbatim data of published episodes, one verbatim sample of a rejected script, two design docs that record the former
# name, the 2025 archive (excluded above), and this test
HISTORICAL = ("governance/BULLETIN.md", "cloud-run-backend/tests/fixtures/episodes_render.json", "cloud-run-backend/tests/unit/test_script_style.py",
              "cloud-run-backend/tests/unit/test_channel_name.py", "docs/design/SERIES_THUMBNAIL.md", "docs/design/CURATED_SOURCES_MODE.md")


def test_the_channel_name_is_copernicusai_fyi_and_every_user_of_it_reads_it_from_one_place():
    assert channel.CHANNEL_NAME == "CopernicusAI.fyi"
    assert cm.CHANNEL == channel.CHANNEL_NAME and st.SERIES_MARK == channel.CHANNEL_NAME
    assert f'\\"{channel.CHANNEL_NAME}\\"' in open(cscript.__file__, encoding="utf-8").read() or channel.CHANNEL_NAME in cscript.SHOW_RULES
    assert f'show "{channel.CHANNEL_NAME}"' in cscript.SHOW_RULES.replace('\\"', '"')


def test_the_documentation_copy_of_the_thumbnail_generator_carries_the_same_name():
    src = open(os.path.join(ROOT, "docs", "design", "series-thumbnail", "make_thumbnail.py"), encoding="utf-8").read()
    assert re.search(r'^SERIES_MARK = "([^"]+)"', src, re.M).group(1) == channel.CHANNEL_NAME


def test_the_old_name_occurs_nowhere_in_live_files():
    out = subprocess.run(["git", "grep", "-l", "-I", "-i", OLD, "--", ".", ":!archive", ":!*venv*", ":!*test_env*"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode not in (0, 1):               # not a git checkout (an exported tree): nothing to scan
        return
    hits = [h for h in out.stdout.split() if h not in HISTORICAL]
    assert hits == [], f"the old channel name is still in: {hits}"
