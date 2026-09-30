"""Tests for the fallback-analysis failure flag (B5 fixture)."""

from enhanced_research_service import EnhancedResearchService, PaperAnalysis
from research_pipeline import ResearchSource


def _paper():
    return ResearchSource(
        title="Some Paper Title",
        authors=["A Author"],
        abstract="An abstract.",
        url="https://example.org/paper",
        publication_date="2024-01-01",
        source="pubmed",
    )


class TestCreateFallbackAnalysis:
    def test_fallback_analysis_is_marked_failed(self):
        """B5: a fallback analysis (built when AI processing fails for a
        paper) must be marked analysis_failed=True so callers can exclude
        it from anything shown to the model or written into a
        description.
        """
        service = EnhancedResearchService.__new__(EnhancedResearchService)
        analysis = service._create_fallback_analysis(_paper())
        assert isinstance(analysis, PaperAnalysis)
        assert analysis.analysis_failed is True

    def test_real_analysis_defaults_to_not_failed(self):
        """A normally-constructed PaperAnalysis (the success path) must
        default to analysis_failed=False so nothing has to pass it
        explicitly at every call site."""
        analysis = PaperAnalysis(
            title="Real Paper",
            summary="Real summary",
            key_findings=["A real, specific finding"],
            methodology="Real methodology",
            implications="Real implications",
            related_work="Real related work",
            technical_complexity="medium",
            suggested_questions=["A real question?"],
            keywords=["real"],
            paradigm_shift_potential="high",
            interdisciplinary_connections=[],
            practical_applications=[],
            future_research_directions=[],
        )
        assert analysis.analysis_failed is False
