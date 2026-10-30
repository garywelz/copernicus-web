"""A fake of the pinned `openai/math` repository for offline tests: what `safe_fetch.guarded_get` would return for the manuscript map, the git tree
listings and the raw files (README, history.md, lean/formalization.yaml). The files are the repository's own, as fixtures."""
import json
import os
from urllib.parse import unquote

from safe_fetch import FetchResult

FIX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")


def fixture(name):
    return open(os.path.join(FIX, name), encoding="utf-8").read()


ETH = "The-Exponential-Time-Hypothesis-is-False-October-25-2026"
HADWIGER = "A-counterexample-to-Hadwigers-conjecture-September-23-2026"
CH = "A-CH-Obstruction-to-a-Prescribed-Categoricity-Threshold-September-24-2026"
QRH_SEPT = "The-Quasi-Riemann-Hypothesis-September-30-2026"
QRH_OCT = "The-Quasi-Riemann-Hypothesis-October-5-2026"
WEIL = "Algebraicity-of-Weil-classes-on-split-abelian-eightfolds-September-18-2026"
OLD_EDITION = "The-Quasi-Riemann-Hypothesis-September-1-2026"


class FakeRepo:
    """Serves the map from the fixture; `trees` maps a directory to [(name, blob-letter)]; `files` maps a repository path to text (overrides)."""

    def __init__(self, trees=None, files=None, map_status=200, raw_status=None, tree_status=None):
        self.trees = dict(trees or {})
        self.files = dict(files or {})
        self.map_status, self.raw_status, self.tree_status = map_status, raw_status or {}, tree_status or {}
        self.urls = []

    def _default_file(self, path):
        if path == "CONTENTS.md":
            return fixture("openai_math_contents_excerpt.md")
        if path == "history.md":
            return fixture("openai_math_history.md")
        if path == "lean/formalization.yaml":
            return fixture("openai_math_formalization_excerpt.yaml")
        if path.startswith("preprints/") and path.endswith("/README.md"):
            d = path.split("/")[1]
            if d == WEIL:
                return fixture("openai_math_withdrawn_readme.md")
            if d in self.trees:
                return fixture("openai_math_standing_readme.md")
        return None

    async def __call__(self, url, **kw):
        self.urls.append(url)
        if "raw.githubusercontent.com" in url:
            path = unquote(url.split("/openai/math/", 1)[1].split("/", 1)[1])
            if path in self.raw_status:
                return FetchResult(self.raw_status[path], {}, b"", url)
            if path == "CONTENTS.md" and self.map_status != 200:
                return FetchResult(self.map_status, {}, b"", url)
            text = self.files.get(path, self._default_file(path))
            return FetchResult(200 if text is not None else 404, {}, (text or "").encode("utf-8"), url)
        if "/git/trees/" in url:
            d = unquote(url.split("%2F", 1)[1])
            if d in self.tree_status:
                return FetchResult(self.tree_status[d], {}, b"{}", url)
            if d not in self.trees:
                return FetchResult(404, {}, b"{}", url)
            return FetchResult(200, {}, json.dumps({"tree": [{"path": n, "type": "blob", "sha": s * 40} for n, s in self.trees[d]]}).encode(), url)
        raise AssertionError(url)


def standard_trees():
    return {ETH: [("paper.pdf", "a"), ("README.md", "b")], HADWIGER: [("paper.pdf", "c"), ("README.md", "d")], CH: [("paper.pdf", "e"), ("README.md", "f")],
            QRH_SEPT: [("paper.pdf", "1"), ("README.md", "2")], QRH_OCT: [("paper2.pdf", "3"), ("README.md", "4")],
            WEIL: [("paper.pdf", "9"), ("README.md", "8")]}
