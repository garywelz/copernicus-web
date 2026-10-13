// Further reading for the episode page: the confirmed papers that are neither named in the script nor the requested paper.
// Shared by both episode handlers (api/episodes/index.js serves /episodes/<id>; api/episodes/[episodeId].js serves /api/episodes/<id>).
// Lives under api/ because .vercelignore excludes lib/ (the first version in lib/ crashed every episode page in production).
function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Further reading: confirmed papers that are neither named in the script nor the requested paper. Built from the registry
// records stored on the episode (papers, papers_named); the description carries only one pointer line to this list.
function furtherReadingHtml(payload = {}) {
  const papers = Array.isArray(payload.papers) ? payload.papers : [];
  const named = new Set(Array.isArray(payload.papers_named) ? payload.papers_named : []);
  const requested = payload.requested_pid ? String(payload.requested_pid) : null;
  const items = papers
    .filter((p) => p && p.pid && !named.has(p.pid) && p.pid !== requested && p.title)
    .map((p) => {
      const authors = Array.isArray(p.authors) ? p.authors : [];
      const who = authors.slice(0, 3).join(', ') + (authors.length > 3 ? ' et al.' : '');
      const ids = p.ids || {};
      const ident = ids.arxiv
        ? `arXiv:${ids.arxiv}${ids.arxiv_version || ''}`
        : ids.doi
          ? `DOI: ${ids.doi}`
          : ids.pmid
            ? `PMID ${ids.pmid}`
            : '';
      const url = typeof p.url === 'string' && /^https?:\/\//.test(p.url) ? p.url : '';
      const label = [who && p.year ? `${who} (${p.year}).` : who ? `${who}.` : '', `${String(p.title).replace(/\.$/, '')}.`, p.venue ? `${String(p.venue).replace(/\.$/, '')}.` : '', ident]
        .filter(Boolean)
        .map(escapeHtml)
        .join(' ');
      return `<li>${url ? `<a href="${escapeHtml(url)}" rel="noopener">${label}</a>` : label}</li>`;
    });
  if (!items.length) return '';
  return `<h2>Further reading</h2><p><em>Papers reviewed while preparing this episode but not discussed in it.</em></p><ul>${items.join('')}</ul>`;
}

module.exports = { escapeHtml, furtherReadingHtml };
