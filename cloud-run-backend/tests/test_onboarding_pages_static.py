"""Onboarding PR 3a-3: static checks of the workspace pages (public/onboarding/engine.html, section.html, panel.html and their scripts). The scripts are RUN in Node by
tests/onboarding_pages.test.js; these tests check what cannot be seen from running them: the markup, the CSP, the approved panel text, that no script or handler can
render user text as HTML, and that every request the pages make matches the backend's own routes, fields, choices and caps."""
import html as html_lib
import json
import re
from pathlib import Path

import pytest

from endpoints.onboarding import routes
from utils import onboarding_template as tpl

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "public" / "onboarding"
API = "https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app"

# The approved text of the "Who can see and change your work" panel (Gary, 2026-11-06; recorded in the PR #190 body). Exactly, in order.
PANEL_TITLE = "Who can see and change your work"
PANEL = [
    "Only the owners of this engine and Gary can open this workspace. Anyone else, signed in or not, gets \"not found\". They can't even tell the workspace exists.",
    "Only the owners can change answers. Gary can read, comment, and approve or reject a finished section, but he can't edit your answers, and he can never override a section marked final.",
    "Nothing becomes public until two people have said yes: the advisor (or the other owner, if the advisor has delegated it) marks a section final, then Gary approves it. Only then is it proposed as a change to the engine's public repository, which Gary reviews and merges. What can become public is the scope statement, the research questions, keywords, seed papers and review-queue decisions.",
    "Your private bibliography stays private. It's never published or added to the corpus, the form never shows it to the other owner, and you can delete it at any time. Entries are marked \"not yet public\" by default, and an entry so marked can never leave the system.",
    "Your email address is never published. Your name appears only as you chose: by role only, unless you picked otherwise.",
    "Your podcasts are private until you make one public. Only Gary can undo that.",
    "Every change made in this workspace is recorded, with who made it and when.",
    "Outside services: if you agreed to lookups, paper titles and identifiers are sent to public scholarly services (Crossref, OpenAlex, arXiv, Semantic Scholar) to find the papers. Making a podcast sends its topic and text to the AI services that write, voice and illustrate it (Google's Gemini, ElevenLabs, and OpenAI's image service). Emails are sent through Google's mail service. Gary's own AI assistants help him check approved changes before they reach the repository.",
    "Gary runs the system, so he has technical access to its database. He doesn't use it to read your private bibliography.",
]

HTML = {"engine": "engine.html", "section": "section.html", "panel": "panel.html"}
SCRIPTS = {"engine": ["common.js", "engine.js"], "section": ["common.js", "section.js"], "panel": []}


def read(name):
    return (PAGES / name).read_text(encoding="utf-8").replace("\r\n", "\n")


def panel_items(page_html):
    start = page_html.index('id="panelList"')
    block = page_html[start:page_html.index("</ul>", start)]
    return [html_lib.unescape(x) for x in re.findall(r"<li>(.*?)</li>", block, re.S)]


@pytest.mark.parametrize("page", ["engine", "section", "panel"])
def test_each_page_has_a_strict_csp_noindex_no_inline_script_or_style_and_only_its_own_files(page):
    t = read(HTML[page])
    assert 'name="robots" content="noindex, nofollow"' in t and 'name="referrer" content="no-referrer"' in t
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', t).group(1)
    assert "default-src 'none'" in csp and "script-src 'self'" in csp and "style-src 'self'" in csp and f"connect-src {API}" in csp and "form-action 'none'" in csp
    assert "unsafe-inline" not in t and "unsafe-eval" not in t and "'unsafe" not in t
    assert re.findall(r'<script\b[^>]*>', t) == [f'<script src="{s}">' for s in SCRIPTS[page]]
    assert not re.search(r"<script[^>]*>[^<]+</script>", t) and "<style" not in t and " style=" not in t
    assert not re.search(r"\son\w+\s*=", t) and "javascript:" not in t.lower()
    assert re.findall(r'<link\b[^>]*>', t) == ['<link rel="stylesheet" href="workspace.css">']
    assert not re.findall(r"""(?:src|href|action)\s*=\s*["']https?:""", t), "no page links or loads anything from another site"
    assert "<iframe" not in t and "<object" not in t and "<embed" not in t and "<form" not in t


@pytest.mark.parametrize("name", ["common.js", "engine.js", "section.js"])
def test_the_scripts_cannot_render_text_as_html_and_talk_only_to_the_site_api(name):
    js = read(name)
    for token in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "setTimeout('", 'setTimeout("', "srcdoc", "javascript:", "createContextualFragment",
                  "DOMParser", "document.cookie", "localStorage.setItem", "sessionStorage", "window.open", "location.href", "location.assign", "location.replace", "postMessage", "WebSocket", "EventSource"):
        assert token not in js, token
    assert not re.search(r"setAttribute\(\s*['\"]on", js) and not re.search(r"\.on[a-z]+\s*=", js), "no inline-style event handlers: listeners are attached with addEventListener"
    urls = set(re.findall(r"https?://[^\s'\"`)]+", js))
    assert urls <= {API}, urls
    assert ("fetch(" in js) == (name == "common.js"), "only common.js talks to the network"
    hrefs = re.findall(r"""setAttribute\(\s*'href',\s*([^;]+?)\);""", js) + re.findall(r"""\bhref:\s*('[^']*'[^}]*?),\s*text""", js)
    if name != "common.js":
        assert hrefs, "the page builds its links"
    for href in hrefs:
        assert re.match(r"""^\s*'(section|engine)\.html\?""", href), f"a link is built only from a page name and encodeURIComponent'd parts: {href}"


def test_the_approved_panel_text_is_in_the_page_exactly_as_static_text_and_in_the_standalone_page():
    for name in ("engine.html", "panel.html"):
        t = read(name)
        assert panel_items(t) == PANEL, name
        assert PANEL_TITLE in t
    e = read("engine.html")
    assert re.search(r'<details class="panel" id="panelBox">\s*<summary>' + re.escape(PANEL_TITLE) + r"</summary>", e), "collapsible, near the top"
    assert e.index('id="panelBox"') < e.index('id="workspace"'), "the panel comes before the workspace"
    assert 'href="panel.html"' in e
    for name in ("common.js", "engine.js", "section.js"):
        js = read(name)
        assert "can't even tell" not in js and "never override" not in js and PANEL_TITLE not in js, "the panel text is static HTML, not injected by a script"


def test_the_accept_page_links_to_the_panel_in_a_new_tab_without_losing_the_invitation():
    t, js = read("accept.html"), read("accept.js")
    link = re.search(r'<a id="panelLink"[^>]*>', t).group(0)
    assert 'href="panel.html"' in link and 'target="_blank"' in link and 'rel="noopener noreferrer"' in link
    assert "who can see and change your work" in t
    assert re.findall(r"<script\b[^>]*>", t) == ['<script src="accept.js">']
    assert "innerHTML" not in js and "engine.html?engine=" in js and "encodeURIComponent" in js and "[a-z0-9][a-z0-9-]{1,40}" in js     # the workspace link is validated like the engine id
    assert "id=\"panelLink\"" in t and "token" not in re.search(r'<a id="panelLink"[^>]*>', t).group(0)


@pytest.mark.parametrize("path", ["/onboarding/engine.html", "/onboarding/section.html", "/onboarding/panel.html", "/onboarding/common.js", "/onboarding/workspace.css",
                                  "/onboarding/engine.js", "/onboarding/section.js", "/onboarding/accept.html"])
def test_vercel_serves_every_workspace_file_with_the_strict_headers(path):
    cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    route = next(r for r in cfg["routes"] if re.fullmatch(r["src"], path) and r.get("headers") and "X-Robots-Tag" in r["headers"])
    assert route["src"] == "/onboarding/(.*)" and route.get("continue") is True
    h = route["headers"]
    assert "script-src 'self'" in h["Content-Security-Policy"] and "frame-ancestors 'none'" in h["Content-Security-Policy"] and f"connect-src {API}" in h["Content-Security-Policy"]
    assert h["X-Robots-Tag"].startswith("noindex") and h["Cache-Control"] == "no-store" and h["Referrer-Policy"] == "no-referrer" and h["X-Content-Type-Options"] == "nosniff"
    assert cfg["routes"].index(route) < next(i for i, r in enumerate(cfg["routes"]) if r.get("src") == "/(.*)")


def test_the_meta_csp_of_every_page_matches_the_header_apart_from_frame_ancestors():
    cfg = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    header = next(r for r in cfg["routes"] if r["src"] == "/onboarding/(.*)")["headers"]["Content-Security-Policy"]
    header = "; ".join(p for p in header.split("; ") if not p.startswith("frame-ancestors"))
    for name in ("engine.html", "section.html", "panel.html", "accept.html"):
        assert re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', read(name)).group(1) == header, name


# ---- what the pages send is what the backend expects ------------------------------------------------------------------------------------------------------
def js_text():
    return {n: read(n) for n in ("common.js", "engine.js", "section.js")}


def object_keys(source, anchor, nth=0):
    """The top-level keys of the object literal that follows the `nth` occurrence of `anchor` in `source`."""
    start = [m.end() for m in re.finditer(re.escape(anchor), source)][nth]
    depth, i, keys = 0, source.index("{", start), []
    begin = i
    while True:
        ch = source[i]
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = source[begin + 1:i]
    level, cur = 0, ""
    for ch in body:
        if ch in "{[(":
            level += 1
        elif ch in "}])":
            level -= 1
        if level == 0 and ch == ",":
            keys.append(cur)
            cur = ""
        else:
            cur += ch
    keys.append(cur)
    return {k.split(":")[0].strip() for k in keys if ":" in k}


def test_every_request_the_pages_make_is_a_real_route_with_the_fields_the_backend_models_expect():
    from tests.test_onboarding_invites import walk
    js = js_text()
    engine, section = js["engine.js"], js["section.js"]
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(routes.router)
    table = {(m, r.path.replace("/api/onboarding/engines/{engine_id}", "")) for r in walk(app.routes) if r.path.startswith("/api/onboarding/engines/") for m in r.methods}
    used = [("GET", ""), ("GET", "/delegations"), ("POST", "/sections/final-all"), ("PUT", "/delegations"), ("DELETE", "/delegations/{delegation_id}"), ("PUT", "/notifications"),
            ("GET", "/sections/{section_key}"), ("PUT", "/items/{item_id}"), ("POST", "/items/{item_id}/comments"), ("POST", "/comments/{comment_id}/resolve"),
            ("POST", "/questions"), ("POST", "/entries"), ("POST", "/sections/{section_key}/final")]
    for pair in used:
        assert pair in table, pair
    for needle in ("OB.call('POST', base + '/sections/final-all')", "OB.call('PUT', base + '/delegations'", "OB.call('DELETE', base + '/delegations/' + encodeURIComponent(id))",
                   "OB.call('PUT', base + '/notifications'", "OB.call('GET', base + '/delegations')"):
        assert needle in engine, needle
    for needle in ("OB.call('PUT', base + '/items/' + encodeURIComponent(c.item.item_id)", "base + '/comments/' + encodeURIComponent(cm.comment_id) + '/resolve'", "OB.call('POST', base + '/questions'",
                   "OB.call('POST', base + '/entries'", "'/sections/' + encodeURIComponent(key) + '/final'", "base + '/items/' + encodeURIComponent(c.item.item_id) + '/comments'",
                   "OB.call('GET', base + '/sections/' + encodeURIComponent(key))"):
        assert needle in section, needle
    assert object_keys(engine, "OB.call('PUT', base + '/delegations', ") == set(routes.DelegationIn.model_fields)
    assert object_keys(engine, "OB.call('PUT', base + '/notifications', ") == set(routes.NotificationsIn.model_fields)
    assert object_keys(section, "'/items/' + encodeURIComponent(c.item.item_id), ") == set(routes.ItemSave.model_fields)
    assert object_keys(section, "'/comments', ") == set(routes.CommentIn.model_fields)
    assert object_keys(section, "OB.call('POST', base + '/entries', ") == {f.alias or n for n, f in routes.EntryIn.model_fields.items()}
    assert object_keys(section, "OB.call('POST', base + '/questions', { action: 'add', questions: [") == set(routes.NewQuestion.model_fields)
    assert object_keys(section, "OB.call('POST', base + '/questions', ", 0) == {"action", "from_item", "questions"} == set(routes.QuestionAction.model_fields)      # the split call
    assert object_keys(section, "OB.call('POST', base + '/questions', ", 1) == {"action", "questions"} <= set(routes.QuestionAction.model_fields)                    # the add call
    assert "action: 'split'" in section and "action: 'add'" in section
    assert "to: 'other_owner'" in engine and routes.DelegationIn.model_fields["to"].default == "other_owner"


def test_the_choices_lists_and_caps_in_the_pages_are_the_templates():
    js = js_text()
    section, common = js["section.js"], js["common.js"]
    assert re.search(r"LISTS = \[([^\]]+)\]", section).group(1).replace("'", "").replace(" ", "").split(",") == list(tpl.KEYWORD_LISTS)
    assert set(re.findall(r"\['(accept|reword|drop|add|keep|yes|no|unsure|split)'", section)) == {"accept", "reword", "drop", "add", "keep", "yes", "no", "unsure"}
    assert "'split'" in section and "choice: 'split'" not in section.replace("action: 'split'", ""), "split goes through its own action, never as an answer choice"
    assert re.search(r"\['keep', 'reword', 'drop', 'add'\]\.map", section) and tuple(["keep", "reword", "drop", "add"]) == tpl.TERM_CHOICES
    assert {"accept", "reword", "drop", "add"} <= set(tpl.QUESTION_CHOICES) and {"keep", "reword", "drop", "add"} == set(tpl.ENTRY_CHOICES) and set(tpl.SEED_CHOICES) == {"yes", "no", "unsure"}
    caps = {tpl.TEXT_CAP, tpl.WORDING_CAP, tpl.REASON_CAP, tpl.TERM_CAP, tpl.ENTRY_CAP, tpl.SEED_COMMENT_CAP, tpl.COMMENT_CAP}
    used = {int(x) for x in re.findall(r"maxlength:\s*(\d+)", section)} | {int(x) for x in re.findall(r"textArea\(c, [^;]+?, \d+, (\d+)\)", section)} \
        | {int(x) for x in re.findall(r"lineInput\(c, [^;]+?, (\d+)\)", section)}
    assert caps <= used, caps - used
    extra = used - caps
    assert len(extra) == 1 and min(extra) >= tpl.LIST_MAX * (tpl.LIST_ITEM_CAP + 1), extra          # the out-of-scope box: 30 lines of 200, with room for the line breaks
    assert re.search(r"maxlength: %d \}\), dis" % tpl.COMMENT_CAP, section)
    titles = dict(re.findall(r"(\w+): '([^']+)'", re.search(r"SECTION_TITLES = \{([^}]+)\}", common).group(1)))
    assert titles == {s["key"]: s["title"] for s in tpl.SECTIONS}
    assert re.search(r"SECTION_KEYS = \[([^\]]+)\]", common).group(1).replace("'", "").replace(" ", "").split(",") == tpl.SECTION_KEYS
    assert re.search(r"ENGINE_RE = /\^\[a-z0-9\]\[a-z0-9-\]\{1,40\}\$/", common) and tpl.ID_RE.pattern.startswith("^[a-z0-9]")
    from utils import onboarding as ob
    assert ob.ENGINE_ID_RE.pattern == r"^[a-z0-9][a-z0-9-]{1,40}$"
    reasons = set(re.findall(r"(\w+): '", re.search(r"REASONS = \{(.+?)\};", common, re.S).group(1)))
    assert reasons == {"not_ready", "not_delegated", "already_final", "approved", "rejected", "unanswered", "disagreed"}


def test_the_pages_are_not_linked_from_any_public_page_and_the_only_link_in_is_the_accept_page():
    names = {"engine.html", "section.html", "panel.html"}
    for p in (ROOT / "public").glob("*.html"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        assert not any(("onboarding/" + n) in t for n in names), p.name
    assert not re.findall(r"onboarding/(engine|section|panel)\.html", (ROOT / "public" / "sitemap.xml").read_text(encoding="utf-8", errors="ignore") if (ROOT / "public" / "sitemap.xml").exists() else "")
    robots = ROOT / "public" / "robots.txt"
    assert not robots.exists() or "Allow: /onboarding" not in robots.read_text(encoding="utf-8", errors="ignore")
