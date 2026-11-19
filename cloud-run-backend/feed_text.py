"""The podcast feed's own episode text: what podcast apps (Spotify, Apple Podcasts and the others reading the RSS feed) are given.

The website renders an episode's stored Markdown description with its own styled HTML (services/episode_service.py, main.py); nothing here changes
that. The feed gets two plainer forms of the same text, built from the same Markdown after the 4,000-character limit has been applied:

  feed_plain(md)  the <description> and <itunes:summary> text: plain paragraphs separated by a blank line; a heading becomes a line of its own
                  ("References"), a list item a line starting "- ", a link its text followed by its address; no Markdown or HTML markup is left.
  feed_html(md)   the <content:encoded> HTML: only the few tags podcast apps accept (ALLOWED_TAGS), no attributes except a link's http(s) address,
                  no inline styles; a heading becomes a bold paragraph, since apps do not render <h1> to <h6>.

Both are plain strings. The feed writer (services/rss_service.py) puts them into the XML as text and lets the XML library escape them exactly once;
an app decodes them once and gets real markup, never the escaped text "&lt;p style=...&gt;" that it would show to the listener (the defect of
2026-11-16, found in 8 of the 40 feed items)."""
import html
import re
from html.parser import HTMLParser

ALLOWED_TAGS = ("p", "br", "a", "ul", "ol", "li", "strong", "em")
_HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_DROP_WITH_CONTENT = ("script", "style", "head", "title")
_VOID = ("br",)


def _markdown_html(md: str) -> str:
    try:
        import markdown  # type: ignore
        return markdown.markdown(md or "", extensions=["extra", "sane_lists"])
    except Exception:                                                    # noqa: BLE001 - no library: plain paragraphs, escaped
        return "".join(f"<p>{html.escape(p.strip())}</p>" for p in (md or "").split("\n\n") if p.strip())


class _Sanitizer(HTMLParser):
    """Keeps ALLOWED_TAGS only. A heading becomes <p><strong>...</strong></p>; any other tag is dropped and its text kept; every attribute is
    dropped except an http(s) href on <a>. Text is re-escaped, so whatever reaches the output is markup this class wrote or escaped text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in _DROP_WITH_CONTENT:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in _HEADINGS:
            self.out.append("<p><strong>")
            self.stack.append(tag)
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            if re.match(r"^https?://", href, re.I):
                self.out.append(f'<a href="{html.escape(href, quote=True)}">')
                self.stack.append("a")
            else:
                self.stack.append("a-dropped")
        elif tag in ALLOWED_TAGS:
            self.out.append("<br>" if tag in _VOID else f"<{tag}>")
            if tag not in _VOID:
                self.stack.append(tag)
        elif tag == "b":
            self.out.append("<strong>")
            self.stack.append("strong-from-b")
        elif tag == "i":
            self.out.append("<em>")
            self.stack.append("em-from-i")

    def handle_startendtag(self, tag, attrs):
        if tag in _VOID and not self.skip:
            self.out.append("<br>")

    def handle_endtag(self, tag):
        if tag in _DROP_WITH_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        want = {"b": "strong-from-b", "i": "em-from-i"}.get(tag, tag)
        if tag == "a" and self.stack and self.stack[-1] == "a-dropped":
            self.stack.pop()
            return
        if want in self.stack:
            while self.stack:
                top = self.stack.pop()
                self.out.append(self._close(top))
                if top == want:
                    break

    @staticmethod
    def _close(tag):
        if tag in _HEADINGS:
            return "</strong></p>"
        if tag == "a-dropped":
            return ""
        return {"strong-from-b": "</strong>", "em-from-i": "</em>"}.get(tag, f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self):
        while self.stack:
            self.out.append(self._close(self.stack.pop()))
        return "".join(self.out)


def sanitize_html(fragment: str) -> str:
    s = _Sanitizer()
    s.feed(fragment or "")
    s.close()
    return re.sub(r"\n{3,}", "\n\n", s.result()).strip()


def feed_html(md: str) -> str:
    """The <content:encoded> HTML for this Markdown: simple paragraphs, lists and links, nothing a podcast app would show as markup."""
    return sanitize_html(_markdown_html(md))


_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def feed_plain(md: str) -> str:
    """The <description> text for this Markdown: plain text only (see the module docstring)."""
    lines = []
    for raw in (md or "").replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            line = m.group(1)
        line = re.sub(r"^(\s*)[*+]\s+", r"\1- ", line)                                 # every bullet as "- "
        line = _MD_LINK.sub(lambda k: k.group(1) if k.group(1).strip() == k.group(2) else f"{k.group(1)} ({k.group(2)})", line)
        line = re.sub(r"(\*\*|__)(.+?)\1", r"\2", line)                                 # bold
        line = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", line)         # italic with *
        line = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"\1", line)           # italic with _
        line = re.sub(r"`([^`]+)`", r"\1", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"<[^>]+>", "", text)                                               # any HTML that came in with the Markdown
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
