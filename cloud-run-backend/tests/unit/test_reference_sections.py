"""Tests for reference_sections (gap 3 fix 1, C6): the lists are built by code from registry records. Offline."""
import pytest

import paper_confirmation as pc
import reference_sections as rs


def paper(pid, title, authors, year, venue="Journal of Tests", arxiv=None, ver=None, doi=None, pmid=None):
    return pc.ConfirmedPaper(pid=pid, title=title, authors=authors, year=year, venue=venue,
                             ids={"arxiv": arxiv, "arxiv_version": ver, "pmid": pmid, "doi": doi},
                             url=f"https://arxiv.org/abs/{arxiv}{ver or ''}" if arxiv else f"https://doi.org/{doi}",
                             abstract="Abs.", registry="arxiv" if arxiv else "crossref", confirmed_at="t", title_match=1.0)


P1 = paper("P1", "Requested paper title", ["Ada Lovelace"], 2025, doi="10.1/p1")
P2 = paper("P2", "AI prediction leads people to forgo guaranteed rewards", ["Aoi Naito", "Hirokazu Shirado"], 2026, venue=None, arxiv="2603.28944", ver="v1")
P3 = paper("P3", "Third paper on cells", ["Grace Hopper", "Alan Turing", "Marie Curie", "Ada Lovelace"], 2023, pmid="12345678", doi="10.1/p3")
P4 = paper("P4", "Fourth paper unnamed", ["Edsger Dijkstra"], 2022, doi="10.1/p4")
ALL = [P1, P2, P3, P4]

DESC = "Opening.\n\n## Key ideas\n\n- one\n\n## References\n\n- Model Wrote This (2019). Fake Paper. DOI: 10.9/fake\n\n## Hashtags\n#a #b\n"


def test_strip_removes_model_reference_sections_and_keeps_the_rest():
    out = rs.strip_model_reference_sections(DESC)
    assert "Fake Paper" not in out and "## References" not in out
    assert "## Key ideas" in out and "## Hashtags" in out and "#a #b" in out


def test_strip_handles_other_headings_and_end_of_text():
    out = rs.strip_model_reference_sections("Body\n\n### Bibliography\n\n- x\n\n# Sources\n\n- y\n")
    assert out.strip() == "Body"


def test_sections_use_only_registry_fields_and_label_further_reading():
    md = rs.build_sections(ALL, named_pids=["P3", "P2"], requested_pid="P1")
    refs, further = md.split("## Further reading")
    assert refs.index("Requested paper title") < refs.index("Third paper on cells") < refs.index("AI prediction leads")  # requested, then order of mention
    assert "Journal of Tests" in refs  # venue shown in References
    assert "arXiv:2603.28944v1" in refs and "PMID 12345678" in refs and "DOI: 10.1/p3" in refs
    assert "Grace Hopper, Alan Turing, Marie Curie et al. (2023)." in refs
    assert "Papers reviewed while preparing this episode but not discussed in it." in further
    assert "Fourth paper unnamed" in further and "Journal of Tests" not in further
    assert "Requested paper title" not in further and "Third paper on cells" not in further


def test_unnamed_papers_never_appear_under_references():
    md = rs.build_sections(ALL, named_pids=["P2"], requested_pid=None)
    refs = md.split("## Further reading")[0]
    assert "AI prediction leads" in refs and "Fourth paper unnamed" not in refs and "Third paper" not in refs


def test_duplicates_in_named_pids_are_listed_once():
    md = rs.build_sections(ALL, named_pids=["P2", "P2", "P1"], requested_pid="P1")
    assert md.count("Requested paper title") == 1 and md.count("AI prediction leads") == 1


def test_no_named_papers_and_no_request_omits_references_heading():
    md = rs.build_sections(ALL, named_pids=[], requested_pid=None)
    assert "## References" not in md and "## Further reading" in md


def test_nothing_to_list_returns_empty():
    assert rs.build_sections([], [], None) == ""


def test_apply_inserts_before_hashtags_and_replaces_model_text():
    out = rs.apply_reference_sections(DESC, ALL, ["P2"], "P1")
    assert "Fake Paper" not in out
    assert out.index("## References") < out.index("## Further reading") < out.index("## Hashtags")
    assert out.count("## References") == 1 and "#a #b" in out


def test_apply_appends_when_there_is_no_hashtag_section():
    out = rs.apply_reference_sections("Opening.\n", ALL, ["P2"], None)
    assert out.startswith("Opening.") and out.rstrip().endswith("https://doi.org/10.1/p4")


def test_apply_is_idempotent():
    once = rs.apply_reference_sections(DESC, ALL, ["P2", "P3"], "P1")
    twice = rs.apply_reference_sections(once, ALL, ["P2", "P3"], "P1")
    assert once == twice


def test_does_not_mutate_the_papers():
    before = P3.venue
    rs.build_sections(ALL, ["P2"], "P1")
    assert P3.venue == before and P3.venue == "Journal of Tests"


def test_survives_the_existing_length_limiter_with_both_sections_intact():
    from content_fixes import limit_description_length
    body = "Paragraph of body text. " * 200
    desc = body + "\n\n## Hashtags\n#a #b\n"
    out = rs.apply_reference_sections(desc, ALL, ["P2", "P3"], "P1")
    limited = limit_description_length(out, 4000)
    assert "## References" in limited and "## Further reading" in limited and "## Hashtags" in limited
    for title in ("Requested paper title", "Fourth paper unnamed", "AI prediction leads"):
        assert title in limited
    assert len(limited) <= 4100


def test_passes_the_existing_pre_publish_placeholder_gate():
    from content_fixes import validate_description_before_publish
    out = rs.apply_reference_sections(DESC, ALL, ["P2", "P3"], "P1")
    validate_description_before_publish(out)  # raises DescriptionValidationError on a placeholder pattern
