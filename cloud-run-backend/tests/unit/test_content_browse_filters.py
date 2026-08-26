from content_browse_filters import (
    facet_values,
    matches_keyword,
    normalize_discipline,
    paginate,
    paper_matches_discipline,
    paper_matches_keyword,
    video_disciplines,
    video_matches,
    video_question_ids,
)


class TestNormalizeDiscipline:
    def test_cs_alias(self):
        assert normalize_discipline("cs") == "computer_science"

    def test_blank(self):
        assert normalize_discipline("  ") is None


class TestVideoQuestionIds:
    def test_reads_metadata_and_top_level(self):
        doc = {
            "question_scope_ids": ["glmp-q1"],
            "metadata": {"question_scope_ids": ["glmp-q8", "glmp-q1"]},
        }
        assert video_question_ids(doc) == ["glmp-q1", "glmp-q8"]


class TestVideoMatches:
    def sample(self):
        return {
            "title": "Lac Operon regulation",
            "description": "E. coli catabolite repression",
            "channel_name": "Khan Academy",
            "disciplines": ["biology", "cs"],
            "tags": ["glmp-sweep"],
            "metadata": {"question_scope_ids": ["glmp-q1", "glmp-q8"]},
        }

    def test_keyword_title(self):
        assert video_matches(self.sample(), keyword="lac operon")
        assert not video_matches(self.sample(), keyword="proof nets")

    def test_discipline_alias(self):
        assert video_matches(self.sample(), discipline="computer_science")
        assert video_disciplines(self.sample()) == ["biology", "computer_science"]

    def test_channel_and_question(self):
        doc = self.sample()
        assert video_matches(doc, channel="Khan Academy", question="glmp-q8")
        assert not video_matches(doc, channel="Veritasium")
        assert not video_matches(doc, question="atap-q1")


class TestPaperKeyword:
    def test_title_and_abstract(self):
        doc = {"title": "CRP binding", "abstract": "catabolite activator protein"}
        assert paper_matches_keyword(doc, "activator")
        assert paper_matches_discipline({"discipline": "Biology"}, "biology")
        assert not paper_matches_discipline({"discipline": "mathematics"}, "biology")


class TestPaginateAndFacets:
    def test_paginate(self):
        page, total = paginate(list(range(10)), page=2, limit=3)
        assert total == 10
        assert page == [3, 4, 5]

    def test_keyword_empty_matches_all(self):
        assert matches_keyword("anything", "")

    def test_facets_ignore_own_dimension(self):
        docs = [
            {
                "title": "A",
                "channel_name": "Khan Academy",
                "disciplines": ["biology"],
                "metadata": {"question_scope_ids": ["glmp-q1"]},
            },
            {
                "title": "B",
                "channel_name": "Veritasium",
                "disciplines": ["physics"],
                "metadata": {"question_scope_ids": []},
            },
        ]
        facets = facet_values(docs, discipline="biology")
        channels = {row["id"]: row["count"] for row in facets["channels"]}
        assert channels["Khan Academy"] == 1
        assert "Veritasium" not in channels
