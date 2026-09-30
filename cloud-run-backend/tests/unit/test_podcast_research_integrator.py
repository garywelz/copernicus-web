"""Tests for the 'REAL CITATIONS' evidence-line builder (B1/B2 fixtures)
and the enhanced-analysis aggregator (B5 fixture)."""

from research_pipeline import ResearchSource
from enhanced_research_service import PaperAnalysis
from podcast_research_integrator import (
    format_real_citation_line,
    aggregate_enhanced_analyses,
)


def _source(**overrides):
    defaults = dict(
        title="Identifying protein-binding sites from unaligned DNA fragments",
        authors=["G D Stormo", "G W Hartzell"],
        abstract="",
        url="",
        publication_date="1989-01-01",
        source="pubmed",
        doi="10.1073/pnas.86.4.1183",
    )
    defaults.update(overrides)
    return ResearchSource(**defaults)


class TestFormatRealCitationLine:
    def test_real_doi_and_year_used_as_is(self):
        line = format_real_citation_line(_source())
        assert "(1989)" in line
        assert "DOI: 10.1073/pnas.86.4.1183" in line
        assert "Recent" not in line

    def test_missing_year_is_omitted_not_faked(self):
        """B2: no publication_date -> no parenthetical at all, never '(Recent)'."""
        line = format_real_citation_line(_source(publication_date=""))
        assert "(Recent)" not in line
        assert "()" not in line
        assert "Stormo" in line

    def test_missing_doi_falls_back_to_url_not_a_placeholder(self):
        """B1: no doi -> Available: <url>, never a fabricated DOI field."""
        line = format_real_citation_line(
            _source(doi=None, url="https://example.org/paper")
        )
        assert "DOI:" not in line
        assert "Available: https://example.org/paper" in line

    def test_missing_doi_and_url_yields_no_citation_line(self):
        line = format_real_citation_line(_source(doi=None, url=""))
        assert line is None

    def test_missing_doi_and_year_together(self):
        """B1 + B2 together: neither fabricated."""
        line = format_real_citation_line(
            _source(doi=None, url="https://example.org/paper", publication_date="")
        )
        assert "10.xxxx" not in line
        assert "Recent" not in line
        assert "Available: https://example.org/paper" in line


def _analysis(**overrides):
    defaults = dict(
        title="A Paper",
        summary="summary",
        key_findings=["A real finding"],
        methodology="m",
        implications="i",
        related_work="r",
        technical_complexity="medium",
        suggested_questions=[],
        keywords=[],
        paradigm_shift_potential="high",
        interdisciplinary_connections=["A real connection"],
        practical_applications=[],
        future_research_directions=[],
    )
    defaults.update(overrides)
    return PaperAnalysis(**defaults)


class TestAggregateEnhancedAnalyses:
    def test_real_analysis_contributes_normally(self):
        shifts, connections, findings = aggregate_enhanced_analyses([_analysis()])
        assert shifts == ["A Paper: high"]
        assert connections == ["A real connection"]
        assert findings == ["A real finding"]

    def test_failed_analysis_is_excluded_entirely(self):
        """B5: a fallback ('analysis_failed') entry must contribute
        nothing -- no placeholder paradigm shift, no boilerplate finding.
        """
        failed = _analysis(
            title="Broken Paper",
            key_findings=["Research findings require further analysis"],
            paradigm_shift_potential="unknown",
            interdisciplinary_connections=[],
            analysis_failed=True,
        )
        shifts, connections, findings = aggregate_enhanced_analyses([failed])
        assert shifts == []
        assert connections == []
        assert findings == []

    def test_mixed_list_keeps_only_the_real_one(self):
        failed = _analysis(
            title="Broken Paper",
            key_findings=["Research findings require further analysis"],
            paradigm_shift_potential="unknown",
            analysis_failed=True,
        )
        real = _analysis(title="Good Paper")
        shifts, connections, findings = aggregate_enhanced_analyses([failed, real])
        assert shifts == ["Good Paper: high"]
        assert "Research findings require further analysis" not in findings
        assert "Broken Paper: unknown" not in shifts
