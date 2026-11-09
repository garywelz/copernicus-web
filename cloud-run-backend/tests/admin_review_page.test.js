// Runs the real review script (public/admin-review.js) in Node against the small fake DOM and a mocked API:
//   node --test cloud-run-backend/tests/admin_review_page.test.js
// It proves what the script does (loads the engines, shows a diff as text, sends the revision and hash the diff showed, asks before deciding, needs a note to send
// back) and that a hostile string only ever becomes text. It does not prove layout, CSS or the CSP in a browser.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { settle, elementTags, Doc } = require('./onboarding_fake_dom');

const PUBLIC = path.join(__dirname, '..', '..', 'public');
const HOSTILE = '<img src=x onerror=alert(1)><script>alert(2)</script>';
const SHA = 'a'.repeat(64);

function loadPage(doc) {
  const html = fs.readFileSync(path.join(PUBLIC, 'admin-onboarding.html'), 'utf8');
  const re = /<(\w+)\b([^>]*?)\sid="([^"]+)"([^>]*)>/g;
  let m;
  while ((m = re.exec(html))) {
    const el = doc.createElement(m[1]);
    el.setAttribute('id', m[3]);
    if (/\shidden(\s|$|>)/.test(m[2] + ' ' + m[4] + ' ')) el.hidden = true;
    doc.body.appendChild(el);
  }
}

function page(route, { key = 'the-key', confirmAnswer = true } = {}) {
  const doc = new Doc();
  loadPage(doc);
  const calls = [], confirms = [], saved = [];
  const sandbox = {
    document: doc, console, Promise, JSON, Object, Array, String, Number, Math, encodeURIComponent, Error,
    confirm: (q) => { confirms.push(q); return confirmAnswer; },
    localStorage: { getItem: (k) => (k === 'admin_api_key' ? key : null), setItem() {} },
    Blob: class { constructor(parts, opts) { this.text = parts.join(''); this.type = opts && opts.type; } },
    URL: { createObjectURL: (b) => { saved.push(b); return 'blob:fake'; }, revokeObjectURL() {} },
    fetch: (url, init) => {
      const p = String(url).replace(/^https:\/\/[^/]+/, '');
      const body = init && init.body ? JSON.parse(init.body) : undefined;
      calls.push({ method: (init && init.method) || 'GET', path: p, body, key: init && init.headers && init.headers['X-Admin-API-Key'] });
      return Promise.resolve(route((init && init.method) || 'GET', p, body)).then((r) => ({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.data), text: () => Promise.resolve(typeof r.data === 'string' ? r.data : JSON.stringify(r.data)) }));
    },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  for (const f of ['admin-onboarding.js', 'admin-review.js']) vm.runInContext(fs.readFileSync(path.join(PUBLIC, f), 'utf8'), sandbox, { filename: f });
  return { doc, calls, confirms, saved, $: (id) => doc.getElementById(id) };
}

const row = (o) => Object.assign({ key: 'scope', title: 'Scope and use case', status: 'final', revision: 3, items: 3, ready: true, open: 0, disagreed: 0, waiting_on: { who: 'admin', label: 'admin' },
                                   age_seconds: 7200, rejection_note: null }, o);
const engines = (sections) => ({ engines: [{ engine_id: 'eng-x', label: HOSTILE, state: 'open', repo: 'org/repo', awaiting_review: 1, sections }] });
const detail = (status) => ({ engine_id: 'eng-x', label: 'Synthetic X', details: [{ section: { key: 'scope', title: 'Scope and use case', status, revision: 3, rejection_note: null },
  items: [{ item_id: 'use-case', revision: 2, value: HOSTILE, choice: null, history: [{ revision: 1, author: 'owner', value: 'older', choice: null }],
            comments: [{ author: 'advisor', kind: 'comment', body: HOSTILE, resolved: false }] }] }] });
const diff = (o) => Object.assign({ engine_id: 'eng-x', section: 'scope', section_status: 'final', revision: 3, content_sha256: SHA, repo: 'org/repo', no_repo: false, note: null,
  base: { branch: 'main', commit_sha: 'b'.repeat(40), commit_state: 'ok' },
  files: [{ path: 'README.md', action: 'modify', base_state: 'ok', proposed_sha256: 'c', notes: [], added: 1, removed: 1, truncated: false,
            lines: [{ t: '@', text: '@@ -1 +1 @@' }, { t: '-', text: 'old' }, { t: '+', text: HOSTILE }, { t: ' ', text: 'same' }] }] }, o);
const ok = (data) => ({ status: 200, data });
function api(over = {}) {
  return (m, p, body) => {
    if (over[m + ' ' + p]) return over[m + ' ' + p](body);
    if (m === 'GET' && p === '/api/admin/onboarding/engines') return ok(engines([row(), row({ key: 'questions', title: 'Research questions', status: 'draft' })]));
    if (m === 'GET' && p === '/api/admin/onboarding/engines/eng-x') return ok(detail('final'));
    if (m === 'GET' && p.startsWith('/api/admin/onboarding/engines/eng-x/diff')) return ok(diff());
    if (m === 'POST') return ok({ section: 'scope', status: 'approved', revision: 3, mail_sent: 1 });
    return { status: 404, data: { detail: 'Not found' } };
  };
}
const all = (doc, pred) => doc.all().filter(pred);
const button = (doc, text) => all(doc, (e) => e.tag === 'button' && e.textContent === text)[0];
const noMarkup = (doc) => assert.deepStrictEqual(elementTags(doc).filter((t) => ['img', 'script', 'iframe', 'svg'].includes(t)), []);

test('the engines load on start with the admin key, and everything from the server is text', async () => {
  const p = page(api());
  await settle();
  assert.deepStrictEqual(p.calls.map((c) => [c.method, c.path, c.key]), [['GET', '/api/admin/onboarding/engines', 'the-key']]);
  assert.match(p.$('engineList').textContent, /org\/repo/);
  assert.match(p.$('engineList').textContent, /Scope and use case/);
  assert.match(p.$('engineList').textContent, /2 h/);
  noMarkup(p.doc);                                                                  // the hostile engine label is text
});

test('no key saved: nothing is requested', async () => {
  const p = page(api(), { key: '' });
  await settle();
  assert.deepStrictEqual(p.calls, []);
});

test('opening a final section shows the diff and the owners history as text, and the decision box', async () => {
  const p = page(api());
  await settle();
  button(p.doc, 'Review').fire('click');
  await settle();
  assert.deepStrictEqual(p.calls.slice(1).map((c) => c.path), ['/api/admin/onboarding/engines/eng-x', '/api/admin/onboarding/engines/eng-x/diff?section=scope']);
  const lines = all(p.doc, (e) => /^(dadd|ddel|dctx|dhunk)$/.test(e.className));
  assert.deepStrictEqual(lines.map((l) => l.className), ['dhunk', 'ddel', 'dadd', 'dctx']);
  assert.strictEqual(lines[2].textContent, '+' + HOSTILE);
  assert.match(p.$('diffBox').textContent, /commit bbbbbbbbbbbb/);
  assert.match(p.$('historyBox').textContent, /Revision 1 by owner: older/);
  assert.strictEqual(p.$('decideBox').hidden, false);
  noMarkup(p.doc);
});

test('a draft section has no diff request and no decision box', async () => {
  const p = page(api({ 'GET /api/admin/onboarding/engines/eng-x': () => ok(detail('draft')) }));
  await settle();
  button(p.doc, 'View').fire('click');
  await settle();
  assert.ok(!p.calls.some((c) => c.path.includes('/diff')));
  assert.strictEqual(p.$('decideBox').hidden, true);
});

test('an engine with no repository and a file that could not be read are said plainly', async () => {
  const noRepo = diff({ no_repo: true, repo: null, files: [
    { path: 'README.md', action: 'add', base_state: 'none', proposed_sha256: 'c', notes: [], added: 1, removed: 0, truncated: false, lines: [{ t: '+', text: 'x' }] },
    { path: 'docs/a.json', action: 'unknown', base_state: 'unavailable', proposed_sha256: 'c', notes: [], added: 1, removed: 0, truncated: false, lines: [{ t: '+', text: 'y' }] }] });
  const p = page(api({ 'GET /api/admin/onboarding/engines/eng-x/diff?section=scope': () => ok(noRepo) }));
  await settle();
  button(p.doc, 'Review').fire('click');
  await settle();
  assert.match(p.$('diffBox').textContent, /no repository: every file is shown as an add/);
  assert.match(p.$('diffBox').textContent, /current file unavailable/);
});

test('Approve asks first, then sends the revision and hash of the diff that was shown, with the note', async () => {
  const declined = page(api(), { confirmAnswer: false });
  await settle();
  button(declined.doc, 'Review').fire('click');
  await settle();
  declined.$('decisionNote').value = 'Fine.';
  declined.$('approve').fire('click');
  await settle();
  assert.strictEqual(declined.confirms.length, 1);
  assert.ok(!declined.calls.some((c) => c.method === 'POST'));

  const p = page(api());
  await settle();
  button(p.doc, 'Review').fire('click');
  await settle();
  p.$('decisionNote').value = 'Fine.';
  p.$('approve').fire('click');
  await settle();
  const post = p.calls.find((c) => c.method === 'POST');
  assert.strictEqual(post.path, '/api/admin/onboarding/engines/eng-x/sections/scope/approve');
  assert.deepStrictEqual(post.body, { note: 'Fine.', expected_revision: 3, expected_content_sha256: SHA });
  assert.strictEqual(post.key, 'the-key');
  assert.match(p.$('reviewResult').textContent, /Approved\. 1 email\(s\) sent \(no note in them\)/);
});

test('Send back needs a note; with one it posts to reject; a 409 says to reload', async () => {
  const changed = { status: 409, data: { detail: { message: 'This section changed since you opened it; reload and look again', reason: 'changed' } } };
  const p = page(api({ 'POST /api/admin/onboarding/engines/eng-x/sections/scope/reject': () => changed }));
  await settle();
  button(p.doc, 'Review').fire('click');
  await settle();
  p.$('reject').fire('click');
  await settle();
  assert.ok(!p.calls.some((c) => c.method === 'POST'));
  assert.match(p.$('reviewResult').textContent, /note is required/);
  p.$('decisionNote').value = 'Please narrow it.';
  p.$('reject').fire('click');
  await settle();
  const post = p.calls.find((c) => c.method === 'POST');
  assert.strictEqual(post.path, '/api/admin/onboarding/engines/eng-x/sections/scope/reject');
  assert.strictEqual(post.body.note, 'Please narrow it.');
  assert.match(p.$('reviewResult').textContent, /changed since you opened it.*Reload the section/);
});

// ---- PR 3b-2: the bundle panel ----------------------------------------------------------------------------------------------------------------------
const BID = 'c'.repeat(32);
const bundleRow = (o) => Object.assign({ bundle_id: BID, status: 'created', created_at: '2026-11-09T10:00:00+00:00', sections: ['scope'], base_commit_sha: 'd'.repeat(40), pr_url: null,
  checks: { public_safe: true, no_email: true, no_not_yet_public: true, names_ok: true, schema_ok: true }, problems: {} }, o);
const engineDetail = () => ({ engine_id: 'eng-x', label: 'X', sections: [
  { key: 'scope', title: 'Scope and use case', status: 'approved', approved_revision: 2 }, { key: 'questions', title: 'Research questions', status: 'final' }] });
function bundlePage(over = {}, opts) {
  const p = page(api(Object.assign({
    'GET /api/admin/onboarding/engines/eng-x': () => ok(engineDetail()),
    'GET /api/admin/onboarding/engines/eng-x/bundles': () => ok({ bundles: [bundleRow()] }),
  }, over)), opts);
  p.$('bundleEngine').value = 'eng-x';
  return p;
}
const checkboxes = (p) => all(p.doc, (e) => e.tag === 'input' && e.attrs['data-section']);

test('the bundle panel offers only the approved sections and lists the bundles of the engine', async () => {
  const p = bundlePage();
  await settle();
  p.$('loadBundles').fire('click');
  await settle();
  assert.deepStrictEqual(checkboxes(p).map((c) => [c.attrs['data-section'], c.checked]), [['scope', true]]);   // the final-not-approved section is not offered
  assert.strictEqual(p.$('createBundle').disabled, false);
  assert.match(p.$('bundleList').textContent, /CREATED.*scope.*base dddddddddddd/);
  assert.match(p.$('bundleList').textContent, /passed: no email address/);
});

test('Create bundle posts the chosen sections; a blocked bundle shows which check failed, as text, and says it cannot be downloaded', async () => {
  const blocked = { status: 'blocked', bundle_id: BID, sections: ['scope'], checks: { public_safe: false, no_email: false, no_not_yet_public: true, names_ok: true, schema_ok: true },
                    problems: { no_email: ['README.md: ' + HOSTILE] }, preview: [{ path: 'README.md', action: 'modify', added: 1, removed: 0, lines: [{ t: '+', text: HOSTILE }] }], notes: ['not exported in v1 (shape not yet agreed with Core)'] };
  const p = bundlePage({ 'POST /api/admin/onboarding/engines/eng-x/bundles': () => ok(blocked),
                         'GET /api/admin/onboarding/engines/eng-x/bundles': () => ok({ bundles: [bundleRow({ status: 'blocked', checks: blocked.checks, problems: blocked.problems })] }) });
  await settle();
  p.$('loadBundles').fire('click');
  await settle();
  p.$('createBundle').fire('click');
  await settle();
  assert.deepStrictEqual(p.calls.find((c) => c.method === 'POST').body, { sections: ['scope'] });
  assert.match(p.$('bundleChecks').textContent, /FAILED: no email address/);
  assert.match(p.$('bundleChecks').textContent, /passed: files parse/);
  assert.match(p.$('bundleMsg').textContent, /BLOCKED.*cannot be downloaded as ready/);
  assert.match(p.$('bundleDiff').textContent, /not exported in v1/);
  noMarkup(p.doc);
  assert.strictEqual(button(p.doc, 'Download'), undefined);                                  // a blocked bundle has no Download button
  assert.strictEqual(button(p.doc, 'Mark merged'), undefined);
});

test('Download fetches the bundle with the admin key and saves the file; Mark merged sends the trimmed PR address', async () => {
  const p = bundlePage({ ['GET /api/admin/onboarding/engines/eng-x/bundles/' + BID]: () => ok({ format: 'engine_onboarding_bundle' }),
                         ['POST /api/admin/onboarding/engines/eng-x/bundles/' + BID + '/merged']: () => ok({ status: 'merged', mail_sent: 2 }) });
  await settle();
  p.$('loadBundles').fire('click');
  await settle();
  button(p.doc, 'Download').fire('click');
  await settle();
  const get = p.calls.find((c) => c.path === '/api/admin/onboarding/engines/eng-x/bundles/' + BID);
  assert.strictEqual(get.key, 'the-key');
  assert.strictEqual(p.saved.length, 1);
  assert.match(p.saved[0].text, /engine_onboarding_bundle/);
  const url = all(p.doc, (e) => e.tag === 'input' && e.attrs.placeholder)[0];
  url.value = '  https://github.com/org/repo/pull/12  ';
  button(p.doc, 'Mark merged').fire('click');
  await settle();
  const post = p.calls.find((c) => c.method === 'POST');
  assert.strictEqual(post.path, '/api/admin/onboarding/engines/eng-x/bundles/' + BID + '/merged');
  assert.deepStrictEqual(post.body, { pr_url: 'https://github.com/org/repo/pull/12' });
  assert.match(p.$('bundleMsg').textContent, /Marked merged; 2 owner\(s\) told \(no content\)/);
});

test('a 409 from the server is shown as the server worded it, and nothing is saved', async () => {
  const refusal = { status: 409, data: { detail: { message: 'This bundle is blocked by a failed check and cannot be downloaded as ready' } } };
  const p = bundlePage({ ['GET /api/admin/onboarding/engines/eng-x/bundles/' + BID]: () => refusal });
  await settle();
  p.$('loadBundles').fire('click');
  await settle();
  button(p.doc, 'Download').fire('click');
  await settle();
  assert.strictEqual(p.saved.length, 0);
  assert.match(p.$('bundleMsg').textContent, /Not downloaded: This bundle is blocked/);
});
