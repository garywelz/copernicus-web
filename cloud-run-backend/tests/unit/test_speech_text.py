"""Paper-label markers must never be spoken or published (gap 3 fix 1)."""
import sys
from unittest.mock import MagicMock

import pytest

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

from speech_text import strip_pn_markers, strip_pn_markers_counted


@pytest.mark.parametrize("raw,clean", [
    ("works well [P3]. Next sentence.", "works well. Next sentence."),
    ("Lovelace showed this [P1] and Turing [P2] agreed.", "Lovelace showed this and Turing agreed."),
    ("both found it [P3, P5] in 2025", "both found it in 2025"),
    ("both found it [P3][P5] in 2025", "both found it in 2025"),
    ("range [P3-P5] noted", "range noted"),
    ("pair [P3 and P5] noted", "pair noted"),
    ("see (P4) for details", "see for details"),
    ("[P12] opens the sentence", " opens the sentence"),
    ("no markers here", "no markers here"),
    ("array[0] and a (parenthetical) and P3 plain text", "array[0] and a (parenthetical) and P3 plain text"),
])
def test_markers_are_removed_with_their_leading_space(raw, clean):
    assert strip_pn_markers(raw) == clean


def test_count_and_empty_input():
    assert strip_pn_markers_counted("a [P1] b [P22] c") == ("a b c", 2)
    assert strip_pn_markers_counted("") == ("", 0) and strip_pn_markers(None) is None


def test_the_speech_cleanup_no_longer_leaves_p_numbers_to_be_read_aloud():
    from elevenlabs_voice_service import ElevenLabsVoiceService
    out = ElevenLabsVoiceService._preprocess_text_for_natural_speech(None, "Hopper and Dijkstra [P7] found it, and Curie [P11, P12] agreed.")
    assert "P7" not in out and "P11" not in out and "[" not in out
    assert out.startswith("Hopper and Dijkstra found it")


def test_finalize_removes_markers_from_script_and_description_and_reports_counts():
    pytest.importorskip("services.podcast_generation_service")
    import services.podcast_generation_service as svc
    import paper_confirmation as pc
    import podcast_research_integrator as pri
    from models.podcast import PodcastRequest
    from named_work_check import NamingResult
    conf = [pc.ConfirmedPaper(pid="P1", title="T", authors=["Ada Lovelace"], year=2025, venue=None,
                              ids={"arxiv": None, "arxiv_version": None, "pmid": None, "doi": "10.1/x"}, url="https://doi.org/10.1/x",
                              abstract="a", registry="crossref", confirmed_at="t", title_match=1.0)]
    ctx = pri.PodcastResearchContext(topic="t", research_sources=[], paper_analyses=[], paradigm_shifts=[], interdisciplinary_connections=[],
                                     key_findings=[], real_citations=[], research_quality_score=1.0, recommended_expertise_level="x",
                                     confirmed_papers=conf, dropped_candidates=[], requested_pid=None)
    content = {"title": "T", "script": "ADAM: Lovelace [P1] showed it. MATILDA: Indeed [P1].", "description": "Body about Lovelace [P1].\n\n## Hashtags\n#a\n"}
    metrics = svc.PodcastGenerationService()._finalize_content(content, PodcastRequest(topic="t"), ctx, NamingResult(named_pids=["P1"]))
    assert "[P1]" not in content["script"] and "[P1]" not in content["description"].split("## References")[0]
    assert content["script"] == "ADAM: Lovelace showed it. MATILDA: Indeed."
    assert metrics["pn_markers_removed"] == {"script": 2, "description": 1}


def test_the_prompt_tells_the_model_not_to_write_the_labels():
    import podcast_research_integrator as pri
    import inspect
    assert "Never write the labels [P1], [P2]" in inspect.getsource(pri)
