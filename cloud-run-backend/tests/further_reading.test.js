// Run with: node cloud-run-backend/tests/further_reading.test.js  (checks the episode page's Further reading section)
const assert = require('assert');
const { furtherReadingHtml } = require('../../api/episodes/[episodeId].js');

const papers = [
  { pid: 'P1', title: 'Requested paper', authors: ['Ada Lovelace'], year: 2025, ids: { doi: '10.1/p1' }, url: 'https://doi.org/10.1/p1' },
  { pid: 'P2', title: 'Named paper', authors: ['Alan Turing'], year: 2024, ids: { arxiv: '2601.00001', arxiv_version: 'v1' }, url: 'https://arxiv.org/abs/2601.00001v1' },
  { pid: 'P3', title: 'Unnamed <b>paper</b>', authors: ['A', 'B', 'C', 'D'], year: 2023, venue: 'Zenodo preprint', ids: { doi: '10.5281/zenodo.1' }, url: 'https://doi.org/10.5281/zenodo.1' },
  { pid: 'P4', title: 'No link paper', authors: [], year: null, ids: { pmid: '123456' }, url: 'javascript:alert(1)' },
];
const html = furtherReadingHtml({ papers, papers_named: ['P2'], requested_pid: 'P1' });
assert(html.includes('<h2>Further reading</h2>'));
assert(!html.includes('Requested paper') && !html.includes('Named paper'), 'listed papers are not repeated');
assert(html.includes('A, B, C et al. (2023). Unnamed &lt;b&gt;paper&lt;/b&gt;. Zenodo preprint. DOI: 10.5281/zenodo.1'));
assert(html.includes('href="https://doi.org/10.5281/zenodo.1"') && !html.includes('javascript:'));
assert(html.includes('No link paper. PMID 123456'));
assert.strictEqual(furtherReadingHtml({ papers, papers_named: ['P2', 'P3', 'P4'], requested_pid: 'P1' }), '');
assert.strictEqual(furtherReadingHtml({}), '');
console.log('further reading: ok');
