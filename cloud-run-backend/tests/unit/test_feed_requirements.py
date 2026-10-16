"""Every third-party package the feed code imports must be listed in requirements.txt. A package that is installed on a developer machine but
not in requirements.txt passes every local test and is missing on Cloud Run: that is how `markdown` was missing from the feed's HTML
description (2026-10-14, the new item's content:encoded came out as raw Markdown). Offline."""
import ast
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ["services/rss_service.py", "audio_length.py", "reference_sections.py"]


def _norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def listed(requirements_text):
    names = set()
    for line in requirements_text.splitlines():
        line = line.split("#", 1)[0].strip()
        m = re.match(r"([A-Za-z0-9_.\-]+)", line) if line and not line.startswith("-") else None
        if m:
            names.add(_norm(m.group(1)))
    return names


def _local(top):
    return (ROOT / f"{top}.py").exists() or (ROOT / top).is_dir()


def imports_of(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):                 # includes imports inside functions, where `markdown` was imported
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def feed_modules(entry=ENTRY):
    """The entry files and every local module they import, transitively."""
    seen, todo = set(), [ROOT / e for e in entry]
    while todo:
        f = todo.pop()
        if f in seen or not f.exists():
            continue
        seen.add(f)
        for mod in imports_of(f):
            top = mod.split(".")[0]
            if _local(top):
                for cand in (ROOT / (mod.replace(".", "/") + ".py"), ROOT / mod.replace(".", "/") / "__init__.py", ROOT / f"{top}.py"):
                    if cand.exists():
                        todo.append(cand)
    return seen


def missing_packages(requirements_text, entry=ENTRY):
    have = listed(requirements_text)
    dists = metadata.packages_distributions()
    missing = {}
    for f in feed_modules(entry):
        for mod in imports_of(f):
            top = mod.split(".")[0]
            if top in sys.stdlib_module_names or _local(top) or top == "__future__":
                continue
            names = {_norm(d) for d in dists.get(top, [])}
            ok = bool(names & have) or (top == "google" and any(h.startswith("google-") for h in have))
            if not ok:
                missing.setdefault(mod, set()).add(str(f.relative_to(ROOT)))
    return missing


def test_every_package_the_feed_code_imports_is_in_requirements():
    missing = missing_packages((ROOT / "requirements.txt").read_text(encoding="utf-8"))
    assert not missing, f"imported by the feed code but not in requirements.txt: {sorted(missing)}"


def test_the_check_would_have_caught_the_missing_markdown_and_mutagen():
    text = "\n".join(l for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
                     if not l.lower().startswith(("markdown", "mutagen")))
    assert {"markdown", "mutagen.mp3"} <= set(missing_packages(text))


def test_the_scan_reaches_the_lazy_import_and_the_local_modules():
    names = {p.name for p in feed_modules()}
    assert {"rss_service.py", "content_fixes.py", "audio_length.py"} <= names
    assert "markdown" in {m for f in feed_modules() for m in imports_of(f)}
