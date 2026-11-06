// Runs the real page scripts (public/onboarding/common.js, engine.js, section.js) in Node against a small fake DOM and a mocked API:
//   node --test cloud-run-backend/tests/onboarding_pages.test.js
// It proves the behaviour of the scripts (rendering, autosave, one-at-a-time saves, the stale-save merge, comments, splitting, marking final, delegation, the
// notification switch, polling that never clobbers typing) and that a hostile string only ever becomes text. It does not prove layout, CSS or the CSP in a browser.
const test = require('node:test');
const assert = require('node:assert');
const { run, settle, elementTags } = require('./onboarding_fake_dom');
const OB = require('../../public/onboarding/common.js');

const HOSTILE = '<img src=x onerror=alert(1)><script>alert(2)</script>';

// ---- fixtures ---------------------------------------------------------------------------------------------------------------------------------------------
const SECTION_META = [['scope', 'Scope and use case'], ['questions', 'Research questions'], ['keywords', 'Keywords and horizons'], ['seeds', 'Seed papers: confirm']];
function enginePayload(over = {}) {
  return Object.assign({
    engine_id: 'eng-x', label: 'Synthetic X', state: 'open', role: 'owner', final_say: true, can_mark_final: true, may_mark: ['scope', 'questions', 'keywords', 'seeds'],
    notifications_email: true, template_version: 1,
    progress: {
      template_version: 1,
      sections: SECTION_META.map(([key, title]) => ({ key, title, status: 'draft', items: 3, open: 1, answered: 2, disagreed: 0, final: 0, approved: 0, ready: false })),
      left: [{ section: 'scope', item_id: 'use-case', reason: 'unanswered' }], left_total: 1,
      waiting_on: { who: ['owners'], line: 'Waiting on the owners to answer 1 item(s) and resolve 0 disagreement(s)' },
    },
  }, over);
}
const item = (o) => Object.assign({ item_id: 'use-case', section: 'scope', type: 'use_case', choice: null, value: null, context: {}, revision: 0, answered: false, author: null, updated_at: null,
                                    comment_count: 0, disagreed: false, history: [], comments: [] }, o);
const sectionPayload = (items, over = {}, key = 'scope') => ({
  section: Object.assign({ key, title: SECTION_META.find((s) => s[0] === key)[1], design: '2.1', status: 'draft', revision: 1, content_sha256: 'h', reopened_by: null, items: items.length,
                           open: 0, answered: items.length, disagreed: 0, final: 0, approved: 0, ready: true }, over),
  items, template_version: 1,
});
const ok = (data) => ({ status: 200, data });
const stale = (current) => ({ status: 409, data: { detail: { message: 'Someone changed this answer since you opened it', stale: true, current } } });

function findAll(root, pred) { const out = []; root.walk((n) => { if (n.nodeType === 1 && pred(n)) out.push(n); }); return out; }
function button(root, text) { return findAll(root, (e) => e.tag === 'button' && e.textContent === text)[0]; }
function card(page, id) {
  return page.doc.all().filter((e) => /^card/.test(e.className) && e.children[0] && e.children[0].children[0] && e.children[0].children[0].textContent === id)[0];
}
function box(page, id, sel) { return findAll(card(page, id), sel); }
const textarea = (page, id) => box(page, id, (e) => e.tag === 'textarea')[0];
const radio = (page, id, value) => box(page, id, (e) => e.attrs.type === 'radio' && e.attrs.value === value)[0];
const status = (page, id) => box(page, id, (e) => e.className === 'status')[0].textContent;
const puts = (page) => page.calls.filter((c) => c.method === 'PUT');
const posts = (page) => page.calls.filter((c) => c.method === 'POST');
function noMarkupIn(page) { assert.deepStrictEqual(elementTags(page.doc).filter((t) => ['img', 'script', 'iframe', 'svg'].includes(t)), []); }

// ---- common.js: the pure helpers ---------------------------------------------------------------------------------------------------------------------------
test('mergeText keeps both versions once and never duplicates', () => {
  assert.strictEqual(OB.mergeText('theirs', 'mine'), 'theirs\n\nmine');
  assert.strictEqual(OB.mergeText('theirs and mine', 'mine'), 'theirs and mine');
  assert.strictEqual(OB.mergeText('', 'mine'), 'mine');
  assert.strictEqual(OB.mergeText('theirs', '  '), 'theirs');
  assert.strictEqual(OB.mergeText('mine plus more', 'mine'), 'mine plus more');
  assert.strictEqual(OB.mergeText('mine', 'mine plus more'), 'mine plus more');
});
test('mergeLists is a union that keeps their order first', () => {
  assert.deepStrictEqual(OB.mergeLists(['a', 'b'], ['b', 'c']), ['a', 'b', 'c']);
  assert.deepStrictEqual(OB.mergeLists(undefined, ['x']), ['x']);
});
test('linesOf trims and drops empty lines', () => { assert.deepStrictEqual(OB.linesOf(' a \n\n b\n  \n'), ['a', 'b']); assert.deepStrictEqual(OB.linesOf(null), []); });
test('problem turns every kind of refusal into plain words', () => {
  assert.strictEqual(OB.problem({ status: 400, data: { detail: 'The wording is required' } }), 'The wording is required');
  assert.strictEqual(OB.problem({ status: 409, data: { detail: { message: 'This section is not ready', reason: 'not_ready' } } }), 'This section is not ready (not ready yet)');
  assert.strictEqual(OB.problem({ status: 422, data: { detail: [{ msg: 'x' }] } }), 'Please check what you entered.');
  assert.match(OB.problem({ status: 404, data: {} }), /Not found/);
  assert.match(OB.problem({ status: 500, data: null }), /Something went wrong/);
});
test('describe and scopeText give readable text', () => {
  assert.strictEqual(OB.describe({ value: 'plain' }), 'plain');
  assert.strictEqual(OB.describe({ value: ['a', 'b'] }), 'a\nb');
  assert.match(OB.describe({ choice: 'reword', value: { wording: 'W?', centrality: 'central', terms: [{ text: 't', choice: 'keep' }] } }), /\[reword\] W\? \(central\) Terms: t \[keep\]/);
  assert.strictEqual(OB.scopeText('all'), 'all sections');
  assert.strictEqual(OB.scopeText(['scope', 'seeds']), 'Scope and use case, Seed papers: confirm');
});

// ---- the engine page ---------------------------------------------------------------------------------------------------------------------------------------
function enginePage(over = {}, delegations = [], extra = null) {
  const state = { engine: enginePayload(over), delegations };
  const page = run('engine.html', ['common.js', 'engine.js'], {
    search: '?engine=eng-x',
    route: (m, p, b) => {
      if (extra) { const r = extra(m, p, b, state); if (r) return r; }
      if (m === 'GET' && p === '/api/onboarding/engines/eng-x') return ok(state.engine);
      if (m === 'GET' && p === '/api/onboarding/engines/eng-x/delegations') return ok({ delegations: state.delegations });
      return { status: 500, data: {} };
    },
  });
  return page;
}

test('the engine page shows the tracker, what is left and the waiting-on line, and the panel text is in the page', async () => {
  const page = enginePage();
  await settle();
  assert.strictEqual(page.$('title').textContent, 'Synthetic X');
  assert.match(page.$('who').textContent, /with the final say/);
  assert.strictEqual(page.$('workspace').hidden, false);
  assert.match(page.$('waiting').textContent, /Waiting on the owners/);
  const rows = page.$('sectionRows').children;
  assert.strictEqual(rows.length, 4);
  assert.match(rows[0].textContent, /Scope and use case/);
  assert.match(page.$('left').textContent, /use-case \(not answered yet\)/);
  assert.strictEqual(page.$('finalBox').hidden, false);
  assert.strictEqual(page.$('delegationBox').hidden, false);
  assert.strictEqual(page.$('notifyEmail').checked, true);
  assert.ok(page.calls.every((c) => c.token === 'tok'));
});

test('hostile text from the server becomes text and never markup', async () => {
  const e = enginePayload({ label: HOSTILE });
  e.progress.left = [{ section: 'scope', item_id: HOSTILE, reason: HOSTILE }];
  const page = enginePage({ label: HOSTILE, progress: e.progress });
  await settle();
  assert.strictEqual(page.$('title').textContent, HOSTILE);
  assert.match(page.$('left').textContent, /<script>alert\(2\)<\/script>/);
  noMarkupIn(page);
});

test('an owner without the power sees no Mark final and no delegation controls, and a delegate is told what they cover', async () => {
  const page = enginePage({ final_say: false, can_mark_final: true, may_mark: ['seeds'] }, [{ delegation_id: 'd'.repeat(32), from: 'advisor', to: 'you', scope: ['seeds'], active: true, created_at: null, revoked_at: null }]);
  await settle();
  assert.strictEqual(page.$('delegationBox').hidden, true);
  assert.match(page.$('delegateText').textContent, /delegated final say to you for: Seed papers: confirm/);
  assert.strictEqual(page.$('delegateBox').hidden, false);
  const none = enginePage({ final_say: false, can_mark_final: false, may_mark: [] });
  await settle();
  assert.strictEqual(none.$('finalBox').hidden, true);
  assert.strictEqual(none.$('delegateBox').hidden, true);
});

test('Mark all ready sections final posts once and says what was marked and what was left', async () => {
  const page = enginePage({}, [], (m, p) => (m === 'POST' && p.endsWith('/sections/final-all')
    ? ok({ marked: ['scope'], skipped: [{ section: 'keywords', reason: 'not_ready' }, { section: 'seeds', reason: 'not_delegated' }], via_delegation: false, progress: enginePayload().progress }) : null));
  await settle();
  page.$('markAll').click();
  await settle();
  assert.strictEqual(posts(page).length, 1);
  assert.match(page.$('markAllResult').textContent, /Marked final: Scope and use case\./);
  assert.match(page.$('markAllResult').textContent, /Keywords and horizons \(not ready yet\); Seed papers: confirm \(not delegated to you\)/);
});

test('delegating: all sections, or only the ones chosen; nothing chosen is refused before any request', async () => {
  const page = enginePage({}, [], (m, p, b) => (m === 'PUT' && p.endsWith('/delegations') ? ok({ delegation_id: 'e'.repeat(32), scope: b.scope, from: 'you', to: 'other owner', active: true }) : null));
  await settle();
  page.$('delegate').click();
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body), [{ to: 'other_owner', scope: 'all' }]);
  page.$('dscopeSome').click();
  page.$('delegate').click();
  await settle();
  assert.strictEqual(puts(page).length, 1);
  assert.match(page.$('delegateResult').textContent, /Choose at least one section/);
  page.$('d_questions').click();
  page.$('d_seeds').click();
  page.$('delegate').click();
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body.scope), ['all', ['questions', 'seeds']]);
  assert.match(page.$('delegateResult').textContent, /Delegated to the other owner for: Research questions, Seed papers: confirm/);
});

test('a delegation can be revoked from the page, and only an active one has the button', async () => {
  const dl = [{ delegation_id: 'a'.repeat(32), from: 'you', to: 'other owner', scope: 'all', active: true, created_at: null, revoked_at: null },
              { delegation_id: 'b'.repeat(32), from: 'you', to: 'other owner', scope: ['scope'], active: false, created_at: null, revoked_at: '2026-11-06T00:00:00' }];
  const page = enginePage({}, dl, (m, p) => (m === 'DELETE' ? ok({ delegation_id: 'a'.repeat(32), active: false }) : null));
  await settle();
  const buttons = findAll(page.$('delegationRows'), (e) => e.tag === 'button');
  assert.strictEqual(buttons.length, 1);
  buttons[0].click();
  await settle();
  const del = page.calls.filter((c) => c.method === 'DELETE');
  assert.deepStrictEqual(del.map((c) => c.path), ['/api/onboarding/engines/eng-x/delegations/' + 'a'.repeat(32)]);
  assert.match(page.$('delegateResult').textContent, /revoked/);
});

test('the notification switch saves the choice and undoes the checkbox if saving fails', async () => {
  let fail = false;
  const page = enginePage({}, [], (m, p) => (m === 'PUT' && p.endsWith('/notifications') ? (fail ? { status: 500, data: {} } : ok({ email: false })) : null));
  await settle();
  page.$('notifyEmail').checked = false;
  page.$('notifyEmail').fire('change');
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body), [{ email: false }]);
  assert.match(page.$('notifyResult').textContent, /will not get/);
  fail = true;
  page.$('notifyEmail').checked = true;
  page.$('notifyEmail').fire('change');
  await settle();
  assert.strictEqual(page.$('notifyEmail').checked, false);
  assert.strictEqual(page.$('notifyResult').className, 'error');
});

test('the engine page polls, and without a session or an engine it asks for neither data nor a guess', async () => {
  const page = enginePage();
  await settle();
  const before = page.calls.length;
  page.timers.tickIntervals();
  await settle();
  assert.ok(page.calls.length > before);
  const anon = run('engine.html', ['common.js', 'engine.js'], { search: '?engine=eng-x', token: '', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.strictEqual(anon.calls.length, 0);
  assert.strictEqual(anon.$('signin').hidden, false);
  const lost = run('engine.html', ['common.js', 'engine.js'], { search: '?engine=ENG_BAD', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.strictEqual(lost.calls.length, 0);
  assert.match(lost.$('msg').textContent, /needs the link from your email/);
  const gone = run('engine.html', ['common.js', 'engine.js'], { search: '?engine=eng-x', route: () => ({ status: 404, data: { detail: 'Not found' } }) });
  await settle();
  assert.strictEqual(gone.$('workspace').hidden, true);
  assert.strictEqual(gone.$('msg').className, 'error');
});

// ---- the section page ------------------------------------------------------------------------------------------------------------------------------------
function sectionPage(key, items, { section = {}, engine = {}, extra = null } = {}) {
  const state = { items, section, engine: enginePayload(engine) };
  const page = run('section.html', ['common.js', 'section.js'], {
    search: '?engine=eng-x&section=' + key,
    route: (m, p, b) => {
      if (extra) { const r = extra(m, p, b, state); if (r) return r; }
      if (m === 'GET' && p === '/api/onboarding/engines/eng-x') return ok(state.engine);
      if (m === 'GET' && p === '/api/onboarding/engines/eng-x/sections/' + key) return ok(sectionPayload(state.items, state.section, key));
      return { status: 500, data: {} };
    },
  });
  page.state = state;
  return page;
}
const saved = (it, revision) => ok({ item: Object.assign({}, it, { revision, answered: true, author: 'you', updated_at: '2026-11-06T12:00:00' }), section_status: 'draft' });

test('a text item autosaves after a pause with the revision it was based on, and the next save uses the new revision', async () => {
  const it = item({ value: 'first', revision: 1, author: 'advisor', updated_at: '2026-11-06T10:00:00' });
  let rev = 1;
  const page = sectionPage('scope', [it], { extra: (m, p, b) => (m === 'PUT' ? saved(it, ++rev) : null) });
  await settle();
  const ta = textarea(page, 'use-case');
  assert.strictEqual(ta.value, 'first');
  ta.type('second');
  ta.type('second!');
  assert.strictEqual(status(page, 'use-case'), 'Unsaved changes...');
  assert.strictEqual(puts(page).length, 0, 'nothing is sent before the pause');
  assert.strictEqual(page.timers.pending(), 1, 'a second keystroke replaces the first timer');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body), [{ value: 'second!', choice: null, base_revision: 1 }]);
  assert.strictEqual(status(page, 'use-case'), 'Saved');
  ta.type('third');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body.base_revision), [1, 2]);
});

test('one item is saved at a time: the next waits until the first has answered', async () => {
  const a = item({ item_id: 'scope-statement', type: 'scope_statement', value: 'a', revision: 1 });
  const b = item({ item_id: 'use-case', value: 'b', revision: 1 });
  const release = [];
  const page = sectionPage('scope', [a, b], { extra: (m, p) => (m === 'PUT' ? new Promise((res) => release.push(() => res(saved(a, 2)))) : null) });
  await settle();
  textarea(page, 'scope-statement').type('A2');
  textarea(page, 'use-case').type('B2');
  page.timers.flushTimeouts();
  await settle();
  assert.strictEqual(puts(page).length, 1, 'only the first save is in flight');
  release.shift()();
  await settle();
  assert.strictEqual(puts(page).length, 2);
  assert.deepStrictEqual(puts(page).map((c) => c.path.split('/').pop()), ['scope-statement', 'use-case']);
  release.shift()();
  await settle();
});

test('a stale save shows both versions and Merge both re-sends the merged text on the current revision', async () => {
  const mine = item({ value: 'base', revision: 1 });
  const theirs = item({ value: 'their edit', revision: 3, author: 'advisor', updated_at: '2026-11-06T11:00:00' });
  let n = 0;
  const page = sectionPage('scope', [mine], { extra: (m, p, b) => (m === 'PUT' ? (n++ === 0 ? stale(theirs) : saved(theirs, 4)) : null) });
  await settle();
  textarea(page, 'use-case').type('my edit');
  page.timers.flushTimeouts();
  await settle();
  const conflict = box(page, 'use-case', (e) => e.className === 'conflict')[0];
  assert.strictEqual(conflict.hidden, false);
  assert.match(conflict.textContent, /Someone changed this answer/);
  assert.match(conflict.textContent, /their edit/);
  assert.match(conflict.textContent, /my edit/);
  assert.match(status(page, 'use-case'), /needs your decision/);
  textarea(page, 'use-case').type('typing while blocked');
  assert.strictEqual(page.timers.pending(), 0, 'no autosave while a conflict is waiting');
  button(conflict, 'Merge both').click();
  await settle();
  assert.deepStrictEqual(puts(page).map((c) => c.body), [{ value: 'my edit', choice: null, base_revision: 1 }, { value: 'their edit\n\nmy edit', choice: null, base_revision: 3 }]);
  assert.strictEqual(conflict.hidden, true);
  assert.strictEqual(textarea(page, 'use-case').value, 'their edit\n\nmy edit');
  assert.strictEqual(status(page, 'use-case'), 'Saved');
});

test('Use theirs takes their answer without saving, and Keep mine overwrites on the current revision', async () => {
  const theirs = item({ value: 'their edit', revision: 3, author: 'advisor' });
  for (const mode of ['theirs', 'mine']) {
    let n = 0;
    const page = sectionPage('scope', [item({ value: 'base', revision: 1 })], { extra: (m) => (m === 'PUT' ? (n++ === 0 ? stale(theirs) : saved(theirs, 4)) : null) });
    await settle();
    textarea(page, 'use-case').type('my edit');
    page.timers.flushTimeouts();
    await settle();
    const conflict = box(page, 'use-case', (e) => e.className === 'conflict')[0];
    button(conflict, mode === 'theirs' ? 'Use theirs' : 'Keep mine').click();
    await settle();
    if (mode === 'theirs') {
      assert.strictEqual(puts(page).length, 1);
      assert.strictEqual(textarea(page, 'use-case').value, 'their edit');
      textarea(page, 'use-case').type('after');
      page.timers.flushTimeouts();
      await settle();
      assert.strictEqual(puts(page)[1].body.base_revision, 3, 'the next save is based on THEIR revision');
    } else {
      assert.deepStrictEqual(puts(page)[1].body, { value: 'my edit', choice: null, base_revision: 3 });
    }
  }
});

test('a conflict on a list merges as a union, and on a structured answer there is no merge button', async () => {
  const theirs = item({ item_id: 'out-of-scope', type: 'out_of_scope', value: ['a', 'b'], revision: 2, author: 'advisor' });
  let n = 0;
  const page = sectionPage('scope', [item({ item_id: 'out-of-scope', type: 'out_of_scope', value: ['a'], revision: 1 })], { extra: (m) => (m === 'PUT' ? (n++ === 0 ? stale(theirs) : saved(theirs, 3)) : null) });
  await settle();
  textarea(page, 'out-of-scope').type('a\nc');
  page.timers.flushTimeouts();
  await settle();
  button(box(page, 'out-of-scope', (e) => e.className === 'conflict')[0], 'Merge both').click();
  await settle();
  assert.deepStrictEqual(puts(page)[1].body.value, ['a', 'b', 'c']);
  const q = item({ item_id: 'ex-q1', section: 'questions', type: 'question', choice: 'accept', value: { centrality: 'central', terms: [] }, revision: 1 });
  const qt = Object.assign({}, q, { revision: 2, value: { centrality: 'background', terms: [] } });
  const qp = sectionPage('questions', [q], { extra: (m) => (m === 'PUT' ? stale(qt) : null) });
  await settle();
  radio(qp, 'ex-q1', 'drop').click();
  qp.timers.flushTimeouts();
  await settle();
  const c = box(qp, 'ex-q1', (e) => e.className === 'conflict')[0];
  assert.strictEqual(button(c, 'Merge both'), undefined);
  assert.ok(button(c, 'Use theirs') && button(c, 'Keep mine'));
});

test('a question: choosing reword shows the wording, and the payload carries the choice, centrality, wording and terms', async () => {
  const q = item({ item_id: 'ex-q1', section: 'questions', type: 'question', context: { original_wording: 'Original?', terms: ['alpha', 'beta'] } });
  const page = sectionPage('questions', [q], { extra: (m) => (m === 'PUT' ? saved(q, 1) : null) });
  await settle();
  assert.match(card(page, 'ex-q1').textContent, /Original wording: Original\?/);
  textarea(page, 'ex-q1').type('typed before choosing');
  page.timers.flushTimeouts();
  await settle();
  assert.strictEqual(puts(page).length, 0);
  assert.match(status(page, 'ex-q1'), /Choose an option/);
  radio(page, 'ex-q1', 'reword').click();
  const wording = textarea(page, 'ex-q1');
  wording.type('Reworded?');
  const termInputs = box(page, 'ex-q1', (e) => e.tag === 'input' && e.attrs.type === 'text' && e.attrs.maxlength === '120');
  assert.deepStrictEqual(termInputs.map((i) => i.value), ['alpha', 'beta']);
  termInputs[1].type('gamma');
  const sels = box(page, 'ex-q1', (e) => e.tag === 'select' && e.parentNode.className === 'term');
  sels[1].value = 'reword';
  sels[1].fire('change');
  button(card(page, 'ex-q1'), 'Add a term').click();
  const all = box(page, 'ex-q1', (e) => e.tag === 'input' && e.attrs.type === 'text' && e.attrs.maxlength === '120');
  all[2].type('delta');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page)[0].body, { choice: 'reword', base_revision: 0, value: { centrality: 'central', wording: 'Reworded?', terms: [
    { text: 'alpha', choice: 'keep' }, { text: 'gamma', choice: 'reword', was: 'beta' }, { text: 'delta', choice: 'add' }] } });
});

test('a question that is dropped sends its reason and no centrality, and an accepted one sends neither wording nor reason', async () => {
  const q = item({ item_id: 'ex-q1', section: 'questions', type: 'question', context: { original_wording: 'Original?' } });
  const page = sectionPage('questions', [q], { extra: (m) => (m === 'PUT' ? saved(q, 1) : null) });
  await settle();
  radio(page, 'ex-q1', 'accept').click();
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page)[0].body, { choice: 'accept', base_revision: 0, value: { centrality: 'central', terms: [] } });
  radio(page, 'ex-q1', 'drop').click();
  const reason = box(page, 'ex-q1', (e) => e.tag === 'input' && e.attrs.maxlength === '500')[0];
  reason.type('Out of scope');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page)[1].body.value, { terms: [], reason: 'Out of scope' });
});

test('a split question is shown as split with no controls, and splitting posts the parts for that question', async () => {
  const split = item({ item_id: 'ex-q9', section: 'questions', type: 'question', choice: 'split', value: { split_into: ['ex-q10', 'ex-q11'] }, revision: 2 });
  const q = item({ item_id: 'ex-q1', section: 'questions', type: 'question', context: { original_wording: 'Original?' } });
  const page = sectionPage('questions', [split, q], { extra: (m, p) => (m === 'POST' && p.endsWith('/questions') ? ok({ ids: ['ex-q12', 'ex-q13'], items: [] }) : null) });
  await settle();
  assert.match(card(page, 'ex-q9').textContent, /split into: ex-q10, ex-q11/);
  assert.strictEqual(box(page, 'ex-q9', (e) => e.attrs.type === 'radio').length, 0);
  button(card(page, 'ex-q1'), 'Split this question...').click();
  const parts = box(page, 'ex-q1', (e) => e.tag === 'textarea' && e.attrs.rows === '2' && e.attrs.maxlength === '600');
  assert.strictEqual(parts.length, 2);
  parts[0].type('Part A?');
  parts[1].type('Part B?');
  button(card(page, 'ex-q1'), 'Split it').click();
  await settle();
  assert.deepStrictEqual(posts(page)[0].body, { action: 'split', from_item: 'ex-q1', questions: [{ wording: 'Part A?', centrality: 'central' }, { wording: 'Part B?', centrality: 'central' }] });
  assert.match(page.$('msg').textContent, /was split/);
});

test('keyword and seed items send their list, text, choice and comment', async () => {
  const kw = item({ item_id: 'kw-1', section: 'keywords', type: 'keyword_entry', context: { list: 'mute' } });
  const added = item({ item_id: 'ex-k1', section: 'keywords', type: 'keyword_entry', choice: 'add', value: { list: 'horizons', text: 'long run' }, revision: 1 });
  const page = sectionPage('keywords', [kw, added], { extra: (m) => (m === 'PUT' ? saved(kw, 1) : null) });
  await settle();
  assert.match(card(page, 'kw-1').textContent, /List: mute/);
  radio(page, 'kw-1', 'keep').click();
  box(page, 'kw-1', (e) => e.attrs.type === 'text')[0].type('noise');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(page)[0].body, { value: { list: 'mute', text: 'noise' }, choice: 'keep', base_revision: 0 });
  assert.deepStrictEqual(box(page, 'ex-k1', (e) => e.attrs.type === 'radio').map((r) => r.attrs.value), ['add', 'drop']);
  assert.strictEqual(radio(page, 'ex-k1', 'add').checked, true);
  const seed = item({ item_id: 'seed-1', section: 'seeds', type: 'seed_confirm', context: { citation: 'A. Author (2020).', identifier: 'doi:10.0/x' } });
  const sp = sectionPage('seeds', [seed], { extra: (m) => (m === 'PUT' ? saved(seed, 1) : null) });
  await settle();
  assert.match(card(sp, 'seed-1').textContent, /A\. Author \(2020\)\.\ndoi:10\.0\/x/);
  radio(sp, 'seed-1', 'unsure').click();
  box(sp, 'seed-1', (e) => e.attrs.type === 'text')[0].type('check the year');
  sp.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(puts(sp)[0].body, { value: { comment: 'check the year' }, choice: 'unsure', base_revision: 0 });
});

test('provenance, history and comments render as text, with a hostile comment and context staying text', async () => {
  const it = item({ value: 'now', revision: 3, author: 'advisor', updated_at: '2026-11-06T10:00:00', context: { citation: HOSTILE },
                    history: [{ revision: 1, author: 'other owner', at: '2026-11-05T10:00:00', value: 'v1', choice: null }, { revision: 2, author: 'you', at: '2026-11-05T11:00:00', value: 'v2', choice: null }],
                    comments: [{ comment_id: 'c'.repeat(32), item_id: 'use-case', kind: 'disagree', body: HOSTILE, author: HOSTILE, role: 'owner', created_at: null, resolved: false, resolved_by: null, resolved_at: null },
                               { comment_id: 'd'.repeat(32), item_id: 'use-case', kind: 'comment', body: 'done', author: 'admin', role: 'admin', created_at: null, resolved: true, resolved_by: 'you', resolved_at: null }],
                    disagreed: true });
  const page = sectionPage('scope', [it]);
  await settle();
  const text = card(page, 'use-case').textContent;
  assert.match(text, /Last changed by advisor on .* \(revision 3\)/);
  assert.match(text, /History \(2 earlier versions\)/);
  assert.match(text, /Revision 2 by you[\s\S]*Revision 1 by other owner/);
  assert.ok(text.includes(HOSTILE));
  assert.match(card(page, 'use-case').className, /disagreed/);
  assert.strictEqual(findAll(card(page, 'use-case'), (e) => e.tag === 'button' && e.textContent === 'Resolve').length, 1, 'only the unresolved comment can be resolved');
  noMarkupIn(page);
});

test('posting a comment, a disagreement, and resolving one', async () => {
  const it = item({ value: 'x', revision: 1, comments: [{ comment_id: 'c'.repeat(32), item_id: 'use-case', kind: 'disagree', body: 'No', author: 'other owner', role: 'owner', created_at: null, resolved: false, resolved_by: null, resolved_at: null }] });
  const page = sectionPage('scope', [it], { extra: (m, p) => (m === 'POST' ? ok({}) : null) });
  await settle();
  const ta = box(page, 'use-case', (e) => e.tag === 'textarea' && e.attrs.maxlength === '2000')[0];
  ta.type('Because of this.');
  const dis = box(page, 'use-case', (e) => e.attrs.type === 'checkbox')[0];
  dis.click();
  button(card(page, 'use-case'), 'Add comment').click();
  await settle();
  assert.deepStrictEqual(posts(page)[0].body, { body: 'Because of this.', kind: 'disagree' });
  assert.strictEqual(posts(page)[0].path, '/api/onboarding/engines/eng-x/items/use-case/comments');
  assert.strictEqual(ta.value, '');
  button(card(page, 'use-case'), 'Resolve').click();
  await settle();
  assert.strictEqual(posts(page)[1].path, '/api/onboarding/engines/eng-x/comments/' + 'c'.repeat(32) + '/resolve');
  ta.type('   ');
  button(card(page, 'use-case'), 'Add comment').click();
  await settle();
  assert.strictEqual(posts(page).length, 2, 'an empty comment is not sent');
});

test('Mark final shows only to someone who may mark this section, is disabled until ready, and posts once', async () => {
  const it = item({ value: 'x', revision: 1 });
  const ready = sectionPage('scope', [it], { extra: (m, p) => (m === 'POST' && p.endsWith('/final') ? ok({ section: 'scope', status: 'final' }) : null) });
  await settle();
  assert.strictEqual(ready.$('finalRow').hidden, false);
  assert.strictEqual(ready.$('markFinal').disabled, false);
  ready.$('markFinal').click();
  await settle();
  assert.deepStrictEqual(posts(ready).map((c) => c.path), ['/api/onboarding/engines/eng-x/sections/scope/final']);
  assert.match(ready.$('msg').textContent, /now marked final/);
  const notReady = sectionPage('scope', [it], { section: { ready: false, open: 2, disagreed: 1 } });
  await settle();
  assert.strictEqual(notReady.$('markFinal').disabled, true);
  assert.match(notReady.$('finalNote').textContent, /2 not answered, 1 disagreement/);
  const noPower = sectionPage('scope', [it], { engine: { can_mark_final: false, may_mark: [] } });
  await settle();
  assert.strictEqual(noPower.$('finalRow').hidden, true);
  const other = sectionPage('scope', [it], { engine: { may_mark: ['seeds'] } });
  await settle();
  assert.strictEqual(other.$('finalRow').hidden, true, 'a delegate for another section sees no button here');
  const done = sectionPage('scope', [it], { section: { status: 'final' } });
  await settle();
  assert.strictEqual(done.$('finalRow').hidden, true);
  assert.match(done.$('banner').textContent, /Editing any answer re-opens it/);
});

test('adding a question and adding a keyword entry post what was typed', async () => {
  const qp = sectionPage('questions', [], { extra: (m, p) => (m === 'POST' ? ok({ ids: ['ex-q4'], items: [] }) : null) });
  await settle();
  const w = findAll(qp.$('adders'), (e) => e.tag === 'textarea')[0];
  w.value = 'A new question?';
  button(qp.$('adders'), 'Add this question').click();
  await settle();
  assert.deepStrictEqual(posts(qp)[0].body, { action: 'add', questions: [{ wording: 'A new question?', centrality: 'central' }] });
  const kp = sectionPage('keywords', [], { extra: (m, p) => (m === 'POST' ? ok({ id: 'ex-k1', item: {} }) : null) });
  await settle();
  findAll(kp.$('adders'), (e) => e.tag === 'input')[0].value = 'long run';
  button(kp.$('adders'), 'Add this entry').click();
  await settle();
  assert.deepStrictEqual(posts(kp)[0], { method: 'POST', path: '/api/onboarding/engines/eng-x/entries', body: { list: 'horizons', text: 'long run' }, token: 'tok' });
});

test('a refresh never overwrites what is being typed, but picks up another owner\'s change on a clean card', async () => {
  const page = sectionPage('scope', [item({ value: 'v1', revision: 1 })]);
  await settle();
  const ta = textarea(page, 'use-case');
  ta.type('my unsaved words');
  page.state.items = [item({ value: 'their v2', revision: 2, author: 'advisor' })];
  page.timers.tickIntervals();
  await settle();
  assert.strictEqual(textarea(page, 'use-case').value, 'my unsaved words');
  assert.match(status(page, 'use-case'), /Another owner changed this answer/);
  const clean = sectionPage('scope', [item({ value: 'v1', revision: 1 })]);
  await settle();
  clean.state.items = [item({ value: 'their v2', revision: 2, author: 'advisor', updated_at: '2026-11-06T10:00:00' })];
  clean.timers.tickIntervals();
  await settle();
  assert.strictEqual(textarea(clean, 'use-case').value, 'their v2');
  const focused = sectionPage('scope', [item({ value: 'v1', revision: 1 })]);
  await settle();
  focused.doc.activeElement = textarea(focused, 'use-case');
  focused.state.items = [item({ value: 'their v2', revision: 2 })];
  focused.timers.tickIntervals();
  await settle();
  assert.strictEqual(textarea(focused, 'use-case').value, 'v1', 'a card with the cursor in it is left alone');
});

test('new items from the other owner appear, and a closed engine makes every control read-only', async () => {
  const page = sectionPage('questions', [item({ item_id: 'ex-q1', section: 'questions', type: 'question', choice: 'accept', value: { centrality: 'central', terms: [] }, revision: 1 })]);
  await settle();
  page.state.items.push(item({ item_id: 'ex-q4', section: 'questions', type: 'question', choice: 'add', value: { wording: 'Added?', centrality: 'background', terms: [] }, revision: 1 }));
  page.timers.tickIntervals();
  await settle();
  assert.ok(card(page, 'ex-q4'));
  const closed = sectionPage('scope', [item({ value: 'x', revision: 1 })], { engine: { state: 'closed' } });
  await settle();
  assert.strictEqual(textarea(closed, 'use-case').disabled, true);
  assert.match(closed.$('banner').textContent, /not open/);
  assert.strictEqual(closed.$('markFinal').disabled, true);
});

test('a validation refusal is shown on the item and the answer stays unsaved; a network error retries', async () => {
  let n = 0;
  const page = sectionPage('scope', [item({ value: 'x', revision: 1 })], { extra: (m) => (m === 'PUT' ? { status: 400, data: { detail: 'the use case is longer than 2000 characters' } } : null) });
  await settle();
  textarea(page, 'use-case').type('y');
  page.timers.flushTimeouts();
  await settle();
  assert.match(status(page, 'use-case'), /Not saved: the use case is longer than 2000 characters/);
  const flaky = sectionPage('scope', [item({ value: 'x', revision: 1 })], { extra: (m) => (m === 'PUT' ? (n++ === 0 ? Promise.reject(new Error('offline')) : saved(item({ value: 'y' }), 2)) : null) });
  await settle();
  textarea(flaky, 'use-case').type('y');
  flaky.timers.flushTimeouts();
  await settle();
  assert.match(status(flaky, 'use-case'), /Network error/);
  flaky.timers.flushTimeouts();
  await settle();
  assert.strictEqual(puts(flaky).length, 2);
  assert.strictEqual(status(flaky, 'use-case'), 'Saved');
});

test('the section page needs a signed-in session and a real section', async () => {
  const anon = run('section.html', ['common.js', 'section.js'], { search: '?engine=eng-x&section=scope', token: '', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.strictEqual(anon.calls.length, 0);
  assert.strictEqual(anon.$('signin').hidden, false);
  const bad = run('section.html', ['common.js', 'section.js'], { search: '?engine=eng-x&section=nope', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.strictEqual(bad.calls.length, 0);
  assert.match(bad.$('msg').textContent, /needs the link from the engine page/);
  const gone = run('section.html', ['common.js', 'section.js'], { search: '?engine=eng-x&section=scope', route: () => ({ status: 404, data: { detail: 'Not found' } }) });
  await settle();
  assert.strictEqual(gone.$('items').hidden, true);
  assert.strictEqual(gone.$('msg').className, 'error');
});
