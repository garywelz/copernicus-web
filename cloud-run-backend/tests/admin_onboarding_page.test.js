// Runs the real invitation script (public/admin-onboarding.js) in Node against the small fake DOM and a mocked API:
//   node --test cloud-run-backend/tests/admin_onboarding_page.test.js
// 4c-1, finding 6 (the attended look of 2026-11-18): the result line kept showing an earlier "Revoked (revoked_member)." although the new revoke sent nothing,
// so it looked done. These tests prove that the line starts empty, says what an action is doing when it starts, carries the time of every result, says so when a
// confirmation is cancelled, and is not overwritten by the list refresh that follows an action.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { settle, Doc } = require('./onboarding_fake_dom');

const PUBLIC = path.join(__dirname, '..', '..', 'public');
const INVITE = 'b'.repeat(32);
const STAMP = /^\[\d\d:\d\d:\d\d\] /;

function loadPage(doc) {
  const html = fs.readFileSync(path.join(PUBLIC, 'admin-onboarding.html'), 'utf8');
  const re = /<(\w+)\b([^>]*?)\sid="([^"]+)"([^>]*)>/g;
  let m;
  while ((m = re.exec(html))) {
    const el = doc.createElement(m[1]);
    el.setAttribute('id', m[3]);
    const a = /\svalue="([^"]*)"/.exec(m[2] + ' ' + m[4]);
    if (a) el.value = a[1];
    doc.body.appendChild(el);
  }
}

function page(route, { confirmAnswer = true, before = null } = {}) {
  const doc = new Doc();
  loadPage(doc);
  if (before) before(doc);
  const calls = [], confirms = [];
  const sandbox = {
    document: doc, console, Promise, JSON, Object, Array, String, Number, Math, Date, encodeURIComponent, Error,
    confirm: (q) => { confirms.push(q); return confirmAnswer; },
    localStorage: { getItem: (k) => (k === 'admin_api_key' ? 'the-key' : null), setItem() {} },
    fetch: (url, init) => {
      const p = String(url).replace(/^https:\/\/[^/]+/, '');
      calls.push({ method: (init && init.method) || 'GET', path: p });
      return Promise.resolve(route((init && init.method) || 'GET', p)).then((r) => ({ ok: r.status >= 200 && r.status < 300, status: r.status, json: () => Promise.resolve(r.data) }));
    },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(PUBLIC, 'admin-onboarding.js'), 'utf8'), sandbox, { filename: 'admin-onboarding.js' });
  return { doc, calls, confirms, $: (id) => doc.getElementById(id) };
}

const listed = () => ({ status: 200, data: { invites: [{ invite_id: INVITE, engine_id: 'tdap', status: 'revoked', final_say: false, can_generate: false, monthly_quota: 0 }] } });

test('the result line starts empty, whatever an earlier page left in it', () => {
  const p = page(() => ({ status: 500, data: {} }), { before: (doc) => { doc.getElementById('result').textContent = 'Revoked (revoked_member).'; } });
  assert.strictEqual(p.$('result').textContent, '');
});

test('a cancelled confirmation says nothing was sent, with its time, and replaces the earlier result', async () => {
  const p = page(() => ({ status: 200, data: { outcome: 'revoked_member' } }), { confirmAnswer: false });
  p.$('result').textContent = '[09:00:00] Revoked (revoked_member).';
  p.$('invRevokeId').value = INVITE;
  p.$('revokeInvite').click();
  await settle();
  assert.strictEqual(p.confirms.length, 1);
  assert.deepStrictEqual(p.calls, [], 'no request at all');
  assert.match(p.$('result').textContent, STAMP);
  assert.match(p.$('result').textContent, /Not revoked: the confirmation was cancelled, so nothing was sent\.$/);
  assert.doesNotMatch(p.$('result').textContent, /Revoked \(/);
});

test('an action says what it is doing as soon as it starts, before any answer comes back', async () => {
  let release;
  const p = page((m) => (m === 'DELETE' ? new Promise((r) => { release = r; }) : listed()));
  p.$('result').textContent = '[09:00:00] Revoked (revoked_member).';
  p.$('invRevokeId').value = INVITE;
  p.$('revokeInvite').click();
  assert.match(p.$('result').textContent, new RegExp(STAMP.source + 'Revoking ' + INVITE + '…$'));
  release({ status: 200, data: { outcome: 'revoked_unused' } });
  await settle();
  assert.match(p.$('result').textContent, new RegExp(STAMP.source + 'Revoked \\(revoked_unused\\)\\.$'));
});

test('a revoke\'s result stays on the line after the list refresh that follows it, and every result carries its time', async () => {
  const p = page((m) => (m === 'DELETE' ? { status: 200, data: { outcome: 'revoked_member' } } : listed()));
  p.$('invEngine').value = 'tdap';
  p.$('invRevokeId').value = INVITE;
  p.$('revokeInvite').click();
  await settle();
  assert.deepStrictEqual(p.calls.map((c) => c.method), ['DELETE', 'GET'], 'revoked, then the list refreshed');
  assert.match(p.$('result').textContent, new RegExp(STAMP.source + 'Revoked \\(revoked_member\\)\\.$'));
  p.$('loadList').click();
  await settle();
  assert.match(p.$('result').textContent, new RegExp(STAMP.source + 'Loaded 1 invitation\\(s\\) for tdap\\.$'), 'a list asked for on its own says so');
  const refused = page(() => ({ status: 403, data: { detail: 'Invalid admin API key' } }));
  refused.$('invRevokeId').value = INVITE;
  refused.$('revokeInvite').click();
  await settle();
  assert.match(refused.$('result').textContent, new RegExp(STAMP.source + 'Not revoked: Invalid admin API key$'));
});
