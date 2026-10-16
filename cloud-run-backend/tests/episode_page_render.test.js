// Run with: node cloud-run-backend/tests/episode_page_render.test.js
// The real /episodes/<id> handler, with the backend stubbed by real episode data (fixture), renders the description as intended.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const handler = require(path.join(__dirname, '..', '..', 'api', 'episodes', 'index.js'));
const other = require(path.join(__dirname, '..', '..', 'api', 'episodes', '[episodeId].js'));
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'episodes_render.json'), 'utf8')).episodes;
const count = (s, re) => (s.match(re) || []).length;

function page(h, id) {
  const res = { headers: {}, statusCode: 0, body: '' };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  res.status = (c) => { res.statusCode = c; return res; };
  res.send = (b) => { res.body = b; return res; };
  res.json = (b) => { res.body = JSON.stringify(b); return res; };
  global.fetch = async () => ({ status: 200, ok: true, json: async () => fx[id] });
  return h({ method: 'GET', query: { episodeId: id }, url: '/episodes/' + id }, res).then(() => res);
}

(async () => {
  for (const h of [handler, other]) {
    const r = await page(h, 'ever-math-260010');
    assert.strictEqual(r.statusCode, 200);
    const b = r.body;
    const article = b.slice(b.indexOf('<article class="description">'), b.indexOf('</article>'));
    assert.strictEqual(count(article, /<ul class="references">[\s\S]*?<\/ul>/g), 1);
    assert.strictEqual(count(article.match(/<ul class="references">[\s\S]*?<\/ul>/)[0], /<li><a href="https:\/\/arxiv\.org\/abs\//g), 5);
    assert(article.includes('listed below.</p>') && article.indexOf('listed below') < article.indexOf('<h2>Further reading</h2>'));   // the pointer, then the list it points to
    assert(count(article, /<li><a href="https:\/\/arxiv\.org\/abs\//g) > 5);                                                     // Further reading links too
    assert(!article.includes('www.copernicusai.fyi') && !/hashtag/i.test(article) && !article.includes('## '));
    assert(/<ul>\s*<li>The divergence/.test(article));
  }
  for (const id of ['ever-phys-250044', 'ever-bio-250014', 'ever-math-260002']) {
    const r = await page(handler, id);
    assert.strictEqual(r.statusCode, 200, id);
    const article = r.body.slice(r.body.indexOf('<article class="description">'), r.body.indexOf('</article>'));
    assert(!/hashtag/i.test(article) && !article.includes('## ') && !article.includes('\n- '), id);
    assert(count(article, /<p>/g) >= 3, id);
  }
  console.log('episode page render: ok');
})().catch((e) => { console.error(e); process.exit(1); });
