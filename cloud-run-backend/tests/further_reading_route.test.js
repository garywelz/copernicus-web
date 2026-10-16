// Run with: node cloud-run-backend/tests/further_reading_route.test.js
// Requests the REAL public route: /episodes/<id> is resolved through vercel.json to the handler file Vercel would run, that handler is
// called with a request and a stubbed backend, and the page it returns must contain the Further reading section. (The first version
// of this feature was put in the handler for /api/episodes/<id>, which is not the public route, and nothing noticed.)
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', '..');
const vercel = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));

// The first route whose pattern matches the URL wins, as in Vercel; named groups fill $name in the destination.
function resolveRoute(url) {
  for (const r of vercel.routes) {
    if (!r.src || !r.dest) continue;
    const m = new RegExp('^' + r.src + '$').exec(url);
    if (m) {
      let dest = r.dest;
      for (const [k, v] of Object.entries(m.groups || {})) dest = dest.replace('$' + k, v);
      for (let i = 1; i < m.length; i++) dest = dest.replace('$' + i, m[i]);
      return dest;
    }
  }
  return null;
}

// /api/episodes -> api/episodes.js or api/episodes/index.js; /api/episodes/<id> -> api/episodes/[episodeId].js
function handlerFileFor(dest) {
  const p = dest.split('?')[0].replace(/^\//, '');
  const candidates = [p + '.js', path.join(p, 'index.js')];
  for (const c of candidates) if (fs.existsSync(path.join(root, c))) return c;
  const dir = path.dirname(p);
  const dynamic = fs.readdirSync(path.join(root, dir)).find((f) => /^\[.+\]\.js$/.test(f));
  return dynamic ? path.join(dir, dynamic) : null;
}

function call(handlerFile, url, query) {
  const handler = require(path.join(root, handlerFile));
  const res = { headers: {}, statusCode: 0, body: '' };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  res.status = (c) => { res.statusCode = c; return res; };
  res.send = (b) => { res.body = b; return res; };
  res.json = (b) => { res.body = JSON.stringify(b); return res; };
  return handler({ method: 'GET', query, url }, res).then(() => res);
}

const papers = [
  { pid: 'P1', title: 'Named paper', authors: ['Ada Lovelace'], year: 2025, ids: { arxiv: '2601.00001', arxiv_version: 'v1' }, url: 'https://arxiv.org/abs/2601.00001v1' },
  { pid: 'P2', title: 'Unnamed paper about proofs', authors: ['Alan Turing'], year: 2024, venue: 'Zenodo preprint', ids: { doi: '10.5281/zenodo.2' }, url: 'https://doi.org/10.5281/zenodo.2' },
];
const episode = (extra) => ({ title: 'T', episode_id: 'ever-x-1', description_markdown: 'Body.', audio_url: 'https://x/a.mp3', ...extra });

(async () => {
  // 1. the public route resolves to api/episodes/index.js
  const dest = resolveRoute('/episodes/ever-x-1');
  assert.strictEqual(dest, '/api/episodes?episodeId=ever-x-1');
  const file = handlerFileFor(dest);
  assert.strictEqual(file, path.join('api', 'episodes', 'index.js'), 'the public route must be served by api/episodes/index.js');

  // 2. an episode with papers shows only the unnamed ones
  let backendBody = episode({ papers, papers_named: ['P1'], requested_pid: null });
  global.fetch = async (url) => {
    assert(String(url).includes('/api/episodes/ever-x-1'), 'handler asked the backend for ' + url);
    return { status: 200, ok: true, json: async () => backendBody };
  };
  let res = await call(file, dest, { episodeId: 'ever-x-1' });
  assert.strictEqual(res.statusCode, 200);
  assert(res.body.includes('<h2>Further reading</h2>'), 'Further reading section is on the page');
  assert(res.body.includes('Unnamed paper about proofs') && res.body.includes('href="https://doi.org/10.5281/zenodo.2"'));
  assert(!res.body.includes('Named paper</'), 'a paper named in the script is not repeated');
  assert(res.body.indexOf('Body.') < res.body.indexOf('Further reading'), 'it comes after the description');

  // 3. an old episode (no stored papers) renders exactly as before: no section, no failure
  backendBody = episode({});
  res = await call(file, dest, { episodeId: 'ever-x-1' });
  assert.strictEqual(res.statusCode, 200);
  assert(!res.body.includes('Further reading</h2>') && res.body.includes('Body.'));

  // 4. every paper already named: no section
  backendBody = episode({ papers, papers_named: ['P1', 'P2'] });
  res = await call(file, dest, { episodeId: 'ever-x-1' });
  assert(!res.body.includes('Further reading</h2>'));

  // 5. malformed stored data does not break the page
  backendBody = episode({ papers: [null, 5, { pid: 'P9' }, { pid: 'P8', title: '<script>x</script>', ids: null, url: 'javascript:alert(1)' }] });
  res = await call(file, dest, { episodeId: 'ever-x-1' });
  assert.strictEqual(res.statusCode, 200);
  assert(!res.body.includes('<script>x</script>') && res.body.includes('&lt;script&gt;x&lt;/script&gt;') && !res.body.includes('javascript:'));

  // 6. the other handler (/api/episodes/<id>) uses the same shared code
  const dest2 = resolveRoute('/api/episodes/ever-x-1');
  assert.strictEqual(dest2, '/api/episodes/ever-x-1');
  const file2 = handlerFileFor(dest2);
  assert.strictEqual(file2, path.join('api', 'episodes', '[episodeId].js'));
  backendBody = episode({ papers, papers_named: ['P1'] });
  res = await call(file2, dest2, { episodeId: 'ever-x-1' });
  assert(res.body.includes('<h2>Further reading</h2>'));
  // 7. the date is readable on both pages, not the raw ISO text the backend stores
  backendBody = episode({ generated_at: '2026-08-21T02:38:37.986690' });
  for (const [f, d] of [[file, dest], [file2, dest2]]) {
    res = await call(f, d, { episodeId: 'ever-x-1' });
    assert(res.body.includes('August 21, 2026'), 'readable date on ' + f);
    assert(!res.body.includes('2026-08-21T02:38:37'), 'no raw ISO timestamp on ' + f);
  }
  console.log('further reading on the real route: ok');
})().catch((e) => { console.error(e); process.exit(1); });
