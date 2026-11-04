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
# name (and channel.py itself, whose docstring says why the name changed), the 2025 archive (excluded above), and this test
HISTORICAL = ("governance/BULLETIN.md", "cloud-run-backend/tests/fixtures/episodes_render.json", "cloud-run-backend/tests/unit/test_script_style.py",
              "cloud-run-backend/tests/unit/test_channel_name.py", "docs/design/SERIES_THUMBNAIL.md", "docs/design/CURATED_SOURCES_MODE.md", "cloud-run-backend/channel.py")


def test_the_channel_name_is_copernicusai_fyi_and_every_user_of_it_reads_it_from_one_place():
    assert channel.CHANNEL_NAME == "CopernicusAI.fyi" and channel.CHANNEL_NAME_SPOKEN == "CopernicusAI"
    assert channel.CHANNEL_NAME == channel.CHANNEL_NAME_SPOKEN + ".fyi"
    assert st.SERIES_MARK == channel.CHANNEL_NAME                        # what is written keeps the full name
    assert cm.CHANNEL == channel.CHANNEL_NAME_SPOKEN                      # what the curated prompt tells the model to speak


def test_the_documentation_copy_of_the_thumbnail_generator_carries_the_same_name():
    src = open(os.path.join(ROOT, "docs", "design", "series-thumbnail", "make_thumbnail.py"), encoding="utf-8").read()
    assert re.search(r'^SERIES_MARK = "([^"]+)"', src, re.M).group(1) == channel.CHANNEL_NAME


def test_the_old_name_occurs_nowhere_in_live_files():
    out = subprocess.run(["git", "grep", "-l", "-I", "-i", OLD, "--", ".", ":!archive", ":!*venv*", ":!*test_env*"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode not in (0, 1):               # not a git checkout (an exported tree): nothing to scan
        return
    hits = [h for h in out.stdout.split() if h not in HISTORICAL]
    assert hits == [], f"the old channel name is still in: {hits}"


# --- spoken and written -----------------------------------------------------------------------------------------------------------------------
def test_the_curated_mode_gives_the_model_the_spoken_name_only():
    assert 'for the show "CopernicusAI".' in cscript.SHOW_RULES.replace('\\"', '"') and ".fyi" not in cscript.SHOW_RULES
    from tests.unit.test_curated_mode import base_items, run_of
    block = run_of(base_items()).prompt_block()
    assert "**CURATED SOURCES MODE: CopernicusAI**" in block and ".fyi" not in block


def test_the_ordinary_mode_prompt_built_by_the_research_integrator_speaks_the_short_name():
    import podcast_research_integrator as pri
    from tests.unit.test_curated_generation import context
    it = pri.PodcastResearchIntegrator("fake-key")
    for neutral in (False, True):
        prompt = it.build_2_speaker_research_prompt(context(), "15-20 minutes", "interview", neutral_labels=neutral)
        assert "Welcome to CopernicusAI." in prompt and ".fyi" not in prompt and "Frontiers" not in prompt


def _joined_strings(path):
    """Every f-string of a source file as (its literal text, the names it interpolates)."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            text = "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
            names = {n.id for v in node.values if isinstance(v, ast.FormattedValue) for n in ast.walk(v.value) if isinstance(n, ast.Name)}
            out.append((text, names))
    return out


def test_both_modes_speak_the_short_name_and_write_the_full_name():
    for path in ("cloud-run-backend/main.py", "cloud-run-backend/services/podcast_generation_service.py"):
        strings = _joined_strings(path)
        spoken = [(t, n) for t, n in strings if "The show name is ALWAYS" in t]        # the prompt that states the show name (a fallback script elsewhere names no show)
        assert spoken, f"{path}: the show-name prompt was not found"
        for text, names in spoken:
            assert "CHANNEL_NAME_SPOKEN" in names and "CHANNEL_NAME" not in names, f"{path}: a prompt that speaks the show's name must use the spoken name"
        written = [(t, n) for t, n in strings if "**Show:**" in t]
        assert written, f"{path}: the transcript header was not found"
        for text, names in written:
            assert "CHANNEL_NAME" in names and "CHANNEL_NAME_SPOKEN" not in names, f"{path}: the written transcript header must use the full name"
