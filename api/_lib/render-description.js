// Renders an episode's stored description (Markdown) as the episode page shows it. The stored text is never rewritten: every fix is made here,
// at render time, so it applies to old and new episodes alike.
//   - structure: headings, paragraphs, bullet lists, one reference per line (the stored description_html collapsed line breaks);
//   - References: each reference is one link (arXiv abs URL with version, DOI URL, or PubMed URL), like the Further reading list;
//   - the Further reading pointer ("... listed on the episode page at www.copernicusai.fyi.", whose link captured ".*") becomes "listed below";
//   - the Hashtags section is not shown on the page (it stays in the stored text and the feed).
// Lives under api/ because .vercelignore excludes lib/.
const { escapeHtml } = require('./further-reading');

const HASHTAG_HEADING = /^\s*(?:#{1,6}\s*)?[*_]*hashtags?[*_]*\s*:?[*_]*\s*$/i;
const HASHTAG_ONLY_LINE = /^\s*(?:#[A-Za-z0-9_]+\s*)+$/;
const REFS_HEADING = /^\s*#{1,6}\s*(?:references|sources|bibliography|works cited)\s*$/i;
const FURTHER_HEADING = /^\s*#{1,6}\s*further reading\s*$/i;
const POINTER = /^\s*[*_]*\s*Further reading:/i;
const BULLET = /^\s*(?:[-*•])\s+(.*)$/;
const HEADING = /^\s*(#{1,6})\s+(.*?)\s*#*\s*$/;
const MD_LINK = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
const BARE_URL = /(https?:\/\/[^\s<>"')\]]*[^\s<>"')\].,;:!?*])/g;

const POINTER_BELOW = 'Further reading: the other papers reviewed for this episode are listed below.';

function stripHtml(text) {
  return text.replace(/<br\s*\/?>/gi, '\n').replace(/<\/?[a-z][^>]*>/gi, '');
}

// Inline Markdown on already-trusted text: escape first, then add links, emphasis and code.
function inline(text) {
  const links = [];
  const keep = (html) => `\u0000${links.push(html) - 1}\u0000`;
  let s = String(text ?? '').replace(MD_LINK, (_, label, url) => keep(`<a href="${escapeHtml(url)}" rel="noopener">${escapeHtml(label)}</a>`));
  s = s.replace(BARE_URL, (url) => keep(`<a href="${escapeHtml(url)}" rel="noopener">${escapeHtml(url)}</a>`));
  s = escapeHtml(s)
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^\w*])\*([^*\n]+)\*(?![\w*])/g, '$1<em>$2</em>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => links[Number(i)]);
}

// The one URL a reference points to: a link already in the line, else arXiv (with its version), DOI or PubMed.
function referenceUrl(line) {
  const md = /\[[^\]]*\]\((https?:\/\/[^\s)]+)\)/.exec(line);
  if (md) return /(\.\.\.?|…)$/.test(md[1]) ? '' : md[1]; // a stored link cut short ("https://pubmed...") goes nowhere
  const arxiv = /arXiv:\s*((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?\/\d{7})(?:v\d+)?)/i.exec(line);
  if (arxiv) return `https://arxiv.org/abs/${arxiv[1]}`;
  const doi = /\bDOI:?\s*(10\.\d{4,9}\/[^\s]+?)[.,;]*(?=\s|$)/i.exec(line);
  if (doi) return `https://doi.org/${doi[1]}`;
  const pmid = /\bPMID:?\s*(\d{5,9})\b/i.exec(line);
  if (pmid) return `https://pubmed.ncbi.nlm.nih.gov/${pmid[1]}/`;
  const bare = new RegExp(BARE_URL.source).exec(line);
  return bare && !/(\.\.\.?|…)$/.test(bare[1]) ? bare[1] : '';
}

function referenceHtml(line) {
  const url = referenceUrl(line);
  const label = escapeHtml(line.replace(MD_LINK, (_, text) => text).replace(/^[\s*_-]+|[\s*_]+$/g, '').replace(/\s+/g, ' '));
  return url ? `<a href="${escapeHtml(url)}" rel="noopener">${label}</a>` : label;
}

function cutHashtags(lines) {
  const at = lines.findIndex((l) => HASHTAG_HEADING.test(l));
  let out = at === -1 ? lines.slice() : lines.slice(0, at);
  while (out.length && (!out[out.length - 1].trim() || HASHTAG_ONLY_LINE.test(out[out.length - 1]))) out.pop();
  return out;
}

function renderDescriptionHtml(markdown, { hasFurtherReading = false } = {}) {
  // Stored lines were sometimes cut mid-line, leaving "... ## Hashtags" (or "## Hashtags#Tag") at the end of the last reference: cut there first.
  const text = stripHtml(String(markdown ?? '').replace(/\r\n?/g, '\n')).replace(/[ \t]*#{1,6}[ \t]*hashtags?\b[\s\S]*$/i, '');
  const lines = cutHashtags(text.split('\n'));
  const html = [];
  let para = [];
  let list = false;
  let inRefs = false;
  let pending = null; // a heading is shown only when something follows it (the stored text has empty "## References")

  const emitPending = () => { if (pending) { html.push(pending); pending = null; } };
  const flushPara = () => { if (para.length) { emitPending(); html.push(`<p>${para.map(inline).join('<br>')}</p>`); para = []; } };
  const closeList = () => { if (list) { html.push('</ul>'); list = false; } };

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    if (!line.trim()) { flushPara(); closeList(); continue; }
    if (HASHTAG_ONLY_LINE.test(line)) continue;                       // a tag line with no "Hashtags" heading before it
    if (/^\s*-{3,}\s*$/.test(line)) { flushPara(); closeList(); continue; }   // a horizontal rule is not content
    const h = HEADING.exec(line);
    if (h) {
      flushPara(); closeList();
      pending = null;
      inRefs = REFS_HEADING.test(line);
      if (FURTHER_HEADING.test(line)) { pending = null; inRefs = false; continue; } // the list below has its own heading
      pending = `<h2>${inline(h[2])}</h2>`;
      continue;
    }
    if (POINTER.test(line)) {
      flushPara(); closeList();
      if (hasFurtherReading) { emitPending(); html.push(`<p class="pointer">${POINTER_BELOW}</p>`); }
      continue;
    }
    const b = BULLET.exec(line);
    if (b) {
      flushPara();
      emitPending();
      if (!list) { html.push(inRefs ? '<ul class="references">' : '<ul>'); list = true; }
      html.push(`<li>${inRefs ? referenceHtml(b[1]) : inline(b[1])}</li>`);
      continue;
    }
    if (inRefs && !/[A-Za-z0-9]/.test(line)) continue; // a stray ":" before the list
    closeList();
    para.push(line.trim());
  }
  flushPara(); closeList();
  return html.join('\n');
}

module.exports = { renderDescriptionHtml, referenceUrl, referenceHtml, inline, POINTER_BELOW };
