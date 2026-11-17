"""The PubMed scout was re-reading one relevance head.

The daily config has ten queries and a target of 500. The first query's
max_results was 500, sort defaulted to relevance, and the loop stopped when the
target was full, so queries 2–10 never ran. The dates in the config run through
2026/12/31. These tests check the plan the scout now builds. None of them call
PubMed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_pubmed_batch.py"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "daily_scout_config.json"
TODAY = date(2026, 11, 17)


def _load_mod():
    spec = importlib.util.spec_from_file_location("acquire_pubmed_batch_window", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["acquire_pubmed_batch_window"] = mod
    spec.loader.exec_module(mod)
    return mod


pubmed = _load_mod()


def test_the_rolling_window_ends_today_and_starts_lookback_days_earlier():
    mindate, maxdate = pubmed.rolling_pubmed_dates(TODAY, lookback_days=14)
    assert (mindate, maxdate) == ("2026/11/03", "2026/11/17")
    mindate, maxdate = pubmed.rolling_pubmed_dates(date(2027, 1, 5), lookback_days=14)
    assert (mindate, maxdate) == ("2026/12/22", "2027/01/05")


def test_the_scout_window_is_entrez_date_and_the_sort_is_publication_date():
    """PubMed accepts sort=pub_date together with datetype=edat.

    Checked 2026-11-17 against esearch: sort=pub_date returned a different
    order and no warning. sort=edat and sort=most_recent were rejected
    ("Unknown sort schema") and ignored. So the scout keeps sort=pub_date
    and filters the window on edat, the date the record was added.
    """
    params = pubmed.pubmed_search_params(
        "gene regulation", 50, mindate="2026/11/03", maxdate="2026/11/17", datetype="edat",
    )
    assert params["sort"] == "pub_date"
    assert params["datetype"] == "edat"
    assert params["mindate"] == "2026/11/03"
    assert params["maxdate"] == "2026/11/17"
    omitted = pubmed.pubmed_search_params("gene regulation", 50, mindate="2026/11/03", maxdate="2026/11/17")
    assert omitted["datetype"] == "pdat"
    explicit = pubmed.pubmed_search_params("x", 10, sort="relevance")
    assert explicit["sort"] == "relevance"
    assert "datetype" not in explicit


def test_every_config_query_runs_and_none_can_take_the_whole_target():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    queries = config["pubmed_queries"]
    assert len(queries) == 10
    plan = pubmed.plan_config_queries(queries, target_count=500, today=TODAY)
    assert len(plan) == 10
    assert [item["query"] for item in plan] == [q["query"] for q in queries]
    assert [item["max_results"] for item in plan] == [50] * 10
    assert sum(item["max_results"] for item in plan) == 500
    assert {item["mindate"] for item in plan} == {"2026/11/03"}
    assert {item["maxdate"] for item in plan} == {"2026/11/17"}
    assert all(item["sort"] == "pub_date" and item["datetype"] == "edat" for item in plan)
    # The stored config dates are the old fixed range. The plan does not use them.
    assert all(q.get("maxdate") == "2026/12/31" for q in queries)
    assert all(item["maxdate"] != q.get("maxdate") for item, q in zip(plan, queries))


def test_a_query_keeps_its_own_smaller_cap_and_a_short_target_still_visits_every_query():
    queries = [
        {"name": "wide", "query": "a", "max_results": 500},
        {"name": "narrow", "query": "b", "max_results": 10},
    ]
    plan = pubmed.plan_config_queries(queries, target_count=100, today=TODAY)
    assert [item["max_results"] for item in plan] == [50, 10]
    short = pubmed.plan_config_queries(
        [{"query": f"q{i}", "max_results": 100} for i in range(10)],
        target_count=5,
        today=TODAY,
    )
    assert len(short) == 10
    assert [item["max_results"] for item in short] == [1] * 10


def test_the_supplement_uses_the_same_window_and_not_the_open_ended_range():
    mindate, maxdate = pubmed.rolling_pubmed_dates(TODAY)
    query = pubmed.supplement_term_query("gene regulatory network inference", mindate, maxdate)
    assert query == '(gene regulatory network inference) AND ("2026/11/03"[EDAT] : "2026/11/17"[EDAT])'
    assert "3000" not in query
    assert "[PDAT]" not in query
    assert '"2024"' not in query
