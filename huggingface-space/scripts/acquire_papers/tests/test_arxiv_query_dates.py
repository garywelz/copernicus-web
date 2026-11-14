"""The arXiv scout's date range (governance/BULLETIN.md entry 045).

From 2026-10-18 export.arxiv.org answered HTTP 500 to every scout query, because the range was written with
wildcards: `submittedDate:[20261031* TO 20261114*]`. The same query with full timestamps,
`submittedDate:[202610310000 TO 202611142359]`, is answered 200. These tests look only at the query string; no
test calls arXiv. Each one fails on the old form.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import urllib.parse
from datetime import date
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_arxiv_batch.py"
RANGE_RE = re.compile(r"submittedDate:\[(\S+) TO (\S+)\]")
TODAY = date(2026, 11, 14)


def _load_mod():
    spec = importlib.util.spec_from_file_location("acquire_arxiv_batch_dates", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["acquire_arxiv_batch_dates"] = mod
    spec.loader.exec_module(mod)
    return mod


arxiv = _load_mod()


def test_the_date_range_is_two_full_timestamps_with_no_wildcard():
    query = arxiv.build_arxiv_query(["q-bio.GN", "q-bio.MN"], days_back=14, today=TODAY)
    assert query == "(cat:q-bio.GN OR cat:q-bio.MN) AND submittedDate:[202610310000 TO 202611142359]"
    assert "*" not in query, "a wildcard in the range is what arXiv answered with HTTP 500"
    start, end = RANGE_RE.search(query).groups()
    assert re.fullmatch(r"\d{12}", start) and re.fullmatch(r"\d{12}", end), "YYYYMMDDHHMM at both ends"


def test_the_old_wildcard_form_would_fail_these_checks():
    """The control: the form the scout sent until this fix does not pass what the test above asks of a query."""
    old = "(cat:q-bio.GN OR cat:q-bio.MN) AND submittedDate:[20261031* TO 20261114*]"
    start, end = RANGE_RE.search(old).groups()
    assert "*" in old and not re.fullmatch(r"\d{12}", start) and not re.fullmatch(r"\d{12}", end)
    assert arxiv.build_arxiv_query(["q-bio.GN", "q-bio.MN"], days_back=14, today=TODAY) != old


def test_the_range_covers_the_whole_first_day_and_the_whole_last_day():
    assert arxiv.submitted_date_filter(date(2026, 10, 18), date(2026, 11, 14)) == "submittedDate:[202610180000 TO 202611142359]"
    assert arxiv.submitted_date_filter(TODAY, TODAY) == "submittedDate:[202611140000 TO 202611142359]"
    start, end = RANGE_RE.search(arxiv.build_arxiv_query(["cs.LG"], days_back=0, today=TODAY)).groups()
    assert (start, end) == ("202611140000", "202611142359")
    start, end = RANGE_RE.search(arxiv.build_arxiv_query(["cs.LG"], days_back=30, today=date(2027, 1, 5))).groups()
    assert (start, end) == ("202612060000", "202701052359"), "a range across a month and a year end"


def test_the_keyword_filter_and_the_categories_are_unchanged_and_the_date_range_comes_last():
    query = arxiv.build_arxiv_query(["cs.LG", "cs.NE"], days_back=14, keyword_filter="biology OR genomics", today=TODAY)
    assert query == "(cat:cs.LG OR cat:cs.NE) AND (all:biology OR all:genomics) AND submittedDate:[202610310000 TO 202611142359]"


def test_the_default_is_today_and_the_encoded_query_carries_no_wildcard():
    query = arxiv.build_arxiv_query(["q-bio.PE"], days_back=14)
    start, end = RANGE_RE.search(query).groups()
    assert end == date.today().strftime("%Y%m%d") + "2359" and start.endswith("0000") and len(start) == 12
    encoded = urllib.parse.urlencode({"search_query": query})
    assert "%2A" not in encoded and "*" not in encoded


def test_no_wildcard_date_range_is_left_anywhere_in_the_scout():
    source = MODULE_PATH.read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines() if "submittedDate" in line and not line.lstrip().startswith(("#", '"', "`")))
    assert not re.search(r"submittedDate:\[[^\]]*\*", code), "no code line builds a date range with a wildcard"
