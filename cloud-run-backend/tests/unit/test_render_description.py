"""Feed rendering of stored descriptions (presentation fix, 2026-10-14): references become links, the Further reading line points at the
episode's own page, and the stored text is not touched. Uses real episodes saved in tests/fixtures/episodes_render.json. Offline."""
import json
import pathlib

import reference_sections as rs

FX = json.loads((pathlib.Path(__file__).parents[1] / "fixtures" / "episodes_render.json").read_text(encoding="utf-8"))["episodes"]
PAGE = "https://copernicusai.fyi/episodes/ever-math-260010"


def test_reference_url_rules():
    assert rs.reference_url("- Li (2026). T. arXiv:2604.24797") == "https://arxiv.org/abs/2604.24797"
    assert rs.reference_url("- X (2011). T. arXiv:1107.4721v2") == "https://arxiv.org/abs/1107.4721v2"
    assert rs.reference_url("- X (2020). T. Nature. DOI: 10.1038/s41586-020-1234-5.") == "https://doi.org/10.1038/s41586-020-1234-5"
    assert rs.reference_url("- X (2020). T. PMID 12345678") == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert rs.reference_url("- X (2020). No identifier.") == ""


def test_new_episode_references_are_links_and_pointer_is_the_episode_page():
    stored = FX["ever-math-260010"]["description_markdown"]
    out = rs.render_for_feed(stored, PAGE)
    refs = out.split("## References")[1].split("*Further reading")[0].strip().split("\n")
    assert len(refs) == 5
    assert refs[1] == "- [The mathlib Community (2019). The Lean mathematical library. arXiv:1910.09336v2](https://arxiv.org/abs/1910.09336v2)"
    assert all(r.startswith("- [") and r.endswith(")") for r in refs)
    assert f"listed on [the episode page]({PAGE}).*" in out
    assert "www.copernicusai.fyi" not in out and ".*" not in out.replace(").*", "")
    assert "## Hashtags" in out                                   # the feed keeps its hashtags
    assert "www.copernicusai.fyi" in stored                       # the stored text is what it was; rendering returns a new string


def test_old_links_are_left_alone_and_unidentified_lines_stay_plain():
    old = FX["ever-phys-250044"]["description_markdown"]
    assert rs.render_for_feed(old, PAGE) == old                   # its lines already carry links
    text = "Intro\n\n## References\n\n- A (2020). No id.\n- B (2020). With id. DOI: 10.1038/x1\n\n## Hashtags\n#a\n"
    out = rs.render_for_feed(text, PAGE)
    assert "- A (2020). No id.\n" in out and "- [B (2020). With id. DOI: 10.1038/x1](https://doi.org/10.1038/x1)\n" in out
    assert rs.render_for_feed(text, PAGE) == out and rs.render_for_feed(out, PAGE) == out   # idempotent


def test_idempotent_on_the_new_episode_and_safe_on_empty():
    once = rs.render_for_feed(FX["ever-math-260010"]["description_markdown"], PAGE)
    assert rs.render_for_feed(once, PAGE) == once
    assert rs.render_for_feed("", PAGE) == "" and rs.render_for_feed(None, PAGE) == ""
