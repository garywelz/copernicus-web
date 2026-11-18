// Runs the real review page (public/onboarding/common.js + candidates.js, PR 4b-2b) and the engine page's link to it in Node, against the small fake DOM and a
// mocked API:   node --test cloud-run-backend/tests/onboarding_review_page.test.js
// It proves the behaviour of the scripts: what each paper shows, saving one decision with its revision, a stale save shown and never merged silently, the
// filters, bulk marking of the papers shown (and its refusals), Mark final, read-only states, and that hostile registry text only ever becomes text.
// It does not prove layout, CSS or the CSP in a browser.
const test = require('node:test');
const assert = require('node:assert');
const { run, settle, elementTags } = require('./onboarding_fake_dom');
const R = require('../../public/onboarding/candidates.js');

const HOSTILE = '<img src=x onerror=alert(1)><script>alert(2)</script>';
const BASE = '/api/onboarding/engines/eng-x';

function paper(n, over = {}) {
  return Object.assign({
    item_id: `cand-${String(n).padStart(12, '0')}`, identifier: `doi:10.9998/held.${n}`, title: `Held paper ${n}`, group: 'Group one', likely_keep: false, reason: 'top_cited',
    cited_by: 3, choice: null, comment: '', revision: 0, answered: false, author: null, updated_at: null, comment_count: 0, disagreed: false, lookup_state: null, unresolved: true,
    abstract: null, abstract_source: null, abstract_fetched_at: null, registry: null, warning: null,
  }, over);
}
const PAPERS = () => [
  paper(1, { lookup_state: 'found', unresolved: false, abstract: 'The first abstract.', abstract_source: 'crossref', registry: { title: 'Held paper 1', authors: ['Ada Example'], year: 2021 } }),
  paper(2, { likely_keep: true, choice: 'keep', comment: 'worth it', revision: 1, answered: true, author: 'other owner' }),
  paper(3, { group: 'Group two', lookup_state: 'title_mismatch', abstract: 'An abstract of something else.', abstract_source: 's2',
             registry: { title: 'A quite different paper', authors: [], year: 1999 }, warning: 'The registry\'s record for this identifier has a different title, shown here. This abstract may belong to a different paper. Please check before relying on it.' }),
];
function counts(ps) {
  return { papers: ps.length, likely_keep: ps.filter((p) => p.likely_keep).length, unresolved: ps.filter((p) => p.unresolved).length, keep: ps.filter((p) => p.choice === 'keep').length,
           drop: ps.filter((p) => p.choice === 'drop').length, unsure: ps.filter((p) => p.choice === 'unsure').length, unanswered: ps.filter((p) => !p.answered).length };
}
function reviewPayload(ps = PAPERS(), sec = {}) {
  return { section: Object.assign({ key: 'review', title: 'Hold list: review', status: 'draft', revision: 1, content_sha256: 'h', items: ps.length, open: 2, answered: 1, disagreed: 0,
                                    final: 0, approved: 0, ready: false, rejection_note: null, approved_at: null, approver_note: null, approved_revision: null }, sec),
           papers: ps, groups: [...new Set(ps.map((p) => p.group))], counts: counts(ps), choices: ['keep', 'drop', 'unsure'], bulk_max: 100, template_version: 1 };
}
const enginePayload = (over = {}) => Object.assign({ engine_id: 'eng-x', label: 'Synthetic X', state: 'open', role: 'owner', final_say: true, can_mark_final: true,
                                                     may_mark: ['scope', 'questions', 'keywords', 'seeds', 'review'], notifications_email: true }, over);
const ok = (data) => ({ status: 200, data });

function open({ papers = PAPERS(), engine = {}, section = {}, extra, token = 'tok', search = '?engine=eng-x', confirmAnswer = true } = {}) {
  const state = { review: reviewPayload(papers, section), engine: enginePayload(engine) };
  const page = run('candidates.html', ['common.js', 'candidates.js'], {
    search, token, confirmAnswer,
    route: (method, path, body) => {
      if (extra) { const r = extra(method, path, body, state); if (r) return r; }
      if (method === 'GET' && path === BASE) return ok(state.engine);
      if (method === 'GET' && path === `${BASE}/review`) return ok(state.review);
      return { status: 500, data: {} };
    },
  });
  page.state = state;
  return page;
}

function findAll(root, pred) { const out = []; root.walk((n) => { if (n.nodeType === 1 && pred(n)) out.push(n); }); return out; }
function cards(page) { return findAll(page.$('papers'), (e) => /^card/.test(e.className)); }
function cardOf(page, title) { return page.doc.all().filter((e) => /^card/.test(e.className) && e.children[0].children[0].textContent === title)[0]; }
const radio = (c, value) => findAll(c, (e) => e.attrs.type === 'radio' && e.attrs.value === value)[0];
const textarea = (c) => findAll(c, (e) => e.tag === 'textarea')[0];
const statusOf = (c) => findAll(c, (e) => e.className === 'status')[0].textContent;
const button = (root, text) => findAll(root, (e) => e.tag === 'button' && e.textContent === text)[0];
const calls = (page, method, path) => page.calls.filter((c) => c.method === method && (!path || c.path === path));
function noMarkupIn(page) { assert.deepStrictEqual(elementTags(page.doc).filter((t) => ['img', 'script', 'iframe', 'svg'].includes(t)), []); }

// ---- the pure helpers -----------------------------------------------------------------------------------------------------------------------------------
test('the filters combine group, likely keep and unresolved', () => {
  const ps = PAPERS();
  assert.deepStrictEqual(R.visible(ps, {}).map((p) => p.item_id), ps.map((p) => p.item_id));
  assert.deepStrictEqual(R.visible(ps, { group: 'Group two' }).map((p) => p.title), ['Held paper 3']);
  assert.deepStrictEqual(R.visible(ps, { likely: true }).map((p) => p.title), ['Held paper 2']);
  assert.deepStrictEqual(R.visible(ps, { unresolved: true }).map((p) => p.title), ['Held paper 2', 'Held paper 3']);
  assert.deepStrictEqual(R.visible(ps, { group: 'Group one', unresolved: true }).map((p) => p.title), ['Held paper 2']);
  assert.deepStrictEqual(R.visible(ps, { group: 'Nope' }), []);
});

test('the bulk body carries each paper with the revision the page last saw, and only the fields the route takes', () => {
  const ps = PAPERS();
  assert.deepStrictEqual(R.bulkBody('drop', ps, { [ps[1].item_id]: 4 }), { choice: 'drop', papers: [{ item_id: ps[0].item_id, base_revision: 0 }, { item_id: ps[1].item_id, base_revision: 4 },
                                                                                                    { item_id: ps[2].item_id, base_revision: 0 }] });
  assert.deepStrictEqual(R.CHOICES, ['keep', 'drop', 'unsure']);
  assert.strictEqual(R.BULK_MAX, 100);
});

test('the lookup state is said in plain words, and never as a paper that does not exist', () => {
  assert.strictEqual(R.stateLine({}), 'Not looked up yet.');
  assert.match(R.stateLine({ lookup_state: 'not_found' }), /does not mean the paper does not exist/);
  assert.strictEqual(R.abstractSource({ abstract_source: 's2' }), 'Abstract from Semantic Scholar');
  for (const s of ['found', 'no_abstract', 'title_mismatch', 'not_found', 'unavailable']) assert.ok(R.stateLine({ lookup_state: s }), s);
});

// ---- what each paper shows ----------------------------------------------------------------------------------------------------------------------------------
test('each paper shows its decision, comment, flags and abstract with its source, in the hold list\'s order', async () => {
  const page = open();
  await settle();
  assert.deepStrictEqual(cards(page).map((c) => c.children[0].children[0].textContent), ['Held paper 1', 'Held paper 2', 'Held paper 3']);
  const one = cardOf(page, 'Held paper 1'), two = cardOf(page, 'Held paper 2');
  assert.match(one.textContent, /doi:10\.9998\/held\.1 · Group: Group one · Reason held: top_cited · Cited by 3/);
  assert.match(one.textContent, /Abstract from Crossref:The first abstract\./);
  assert.match(one.textContent, /Ada Example \(2021\)/);
  assert.match(one.textContent, /Not decided yet/);
  assert.ok(!radio(one, 'keep').checked && !radio(one, 'drop').checked && !radio(one, 'unsure').checked);
  assert.ok(radio(two, 'keep').checked && textarea(two).value === 'worth it');
  assert.match(two.textContent, /Flagged by a reviewer as likely keep/);
  assert.match(two.textContent, /Decided: Keep by other owner/);
  assert.match(two.textContent, /No abstract\. Not looked up yet\./);
  assert.match(page.$('counts').textContent, /3 papers: 1 keep, 0 drop, 0 unsure, 2 not decided yet\. 1 flagged as likely keep; 2 unresolved\./);
  assert.strictEqual(page.$('title').textContent, 'Hold list: review');
  assert.strictEqual(page.$('back').getAttribute('href'), 'engine.html?engine=eng-x');
});

test('a title mismatch shows the plain warning with both titles, and the abstract stays beside them', async () => {
  const page = open();
  await settle();
  const three = cardOf(page, 'Held paper 3'), t = three.textContent;
  assert.match(t, /This abstract may belong to a different paper/);
  assert.match(t, /Title in the hold list: Held paper 3/);
  assert.match(t, /Title the registry gives for this identifier: A quite different paper/);
  assert.match(t, /Abstract from Semantic Scholar:An abstract of something else\./);
  assert.strictEqual(findAll(three, (e) => e.className === 'conflict' && !e.hidden && /different paper/.test(e.textContent)).length, 1);
});

test('hostile text in a title, an abstract, a registry title, a group and a comment becomes text and never markup', async () => {
  const page = open({ papers: [paper(1, { title: HOSTILE, abstract: HOSTILE, abstract_source: HOSTILE, group: HOSTILE, comment: HOSTILE, identifier: HOSTILE, reason: HOSTILE,
                                          lookup_state: 'title_mismatch', registry: { title: HOSTILE, authors: [HOSTILE], year: 2020 }, warning: HOSTILE })] });
  await settle();
  noMarkupIn(page);
  const c = cards(page)[0];
  assert.ok(c.textContent.includes(HOSTILE) && textarea(c).value === HOSTILE);
  assert.ok(findAll(page.$('fGroup'), (e) => e.tag === 'option' && e.textContent === HOSTILE).length === 1);
});

// ---- one decision -------------------------------------------------------------------------------------------------------------------------------------------
test('choosing a decision saves it at once with the comment and the revision it was based on; a comment saves after a pause', async () => {
  const page = open({ extra: (m, p, body) => {
    if (m === 'PUT' && p.startsWith(`${BASE}/items/`)) {
      return ok({ item: { item_id: p.split('/').pop(), choice: body.choice, value: body.value, revision: body.base_revision + 1, answered: true, author: 'you', updated_at: '2026-11-17T12:00:00Z' } });
    }
  } });
  await settle();
  const one = cardOf(page, 'Held paper 1');
  radio(one, 'unsure').click();
  await settle();
  assert.deepStrictEqual(calls(page, 'PUT').map((c) => [c.path, c.body]), [[`${BASE}/items/cand-000000000001`, { value: { comment: '' }, choice: 'unsure', base_revision: 0 }]]);
  assert.strictEqual(statusOf(one), 'Saved');
  assert.match(one.textContent, /Decided: Unsure by you/);
  textarea(one).type('on the fence');
  assert.strictEqual(calls(page, 'PUT').length, 1);
  assert.strictEqual(statusOf(one), 'Not saved yet');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(calls(page, 'PUT')[1].body, { value: { comment: 'on the fence' }, choice: 'unsure', base_revision: 1 });     // the new revision
  const two = cardOf(page, 'Held paper 2');
  textarea(two).type('a comment alone');
  page.timers.flushTimeouts();
  await settle();
  assert.deepStrictEqual(calls(page, 'PUT')[2].body, { value: { comment: 'a comment alone' }, choice: 'keep', base_revision: 1 });   // its existing decision is kept
  const three = cardOf(page, 'Held paper 3');
  textarea(three).type('no decision yet');
  page.timers.flushTimeouts();
  await settle();
  assert.strictEqual(calls(page, 'PUT').length, 3);                                                                       // a comment with no decision is not sent
  assert.match(statusOf(three), /Choose keep, drop or unsure/);
});

test('a stale save is refused and shown with both decisions; nothing is merged; Use theirs and Keep mine each do what they say', async () => {
  let puts = 0;
  const theirs = { item_id: 'cand-000000000001', choice: 'drop', value: { comment: 'off topic' }, revision: 2, answered: true, author: 'other owner', updated_at: '2026-11-17T11:00:00Z' };
  const page = open({ extra: (m, p, body) => {
    if (m === 'PUT') {
      puts += 1;
      if (puts === 1) return { status: 409, data: { detail: { message: 'Someone changed this answer since you opened it', stale: true, current: theirs } } };
      return ok({ item: Object.assign({}, theirs, { choice: body.choice, value: body.value, revision: body.base_revision + 1, author: 'you' }) });
    }
  } });
  await settle();
  const one = cardOf(page, 'Held paper 1');
  radio(one, 'keep').click();
  await settle();
  const box = findAll(one, (e) => e.className === 'conflict' && !e.hidden)[0];
  assert.match(box.textContent, /Your change was not saved/);
  assert.match(box.textContent, /Their decision \(other owner, .*\): Drop\. Comment: off topic/);
  assert.match(box.textContent, /Yours: Keep/);
  assert.match(statusOf(one), /Not saved: changed by someone else/);
  button(box, 'Use theirs').click();
  await settle();
  assert.ok(radio(one, 'drop').checked && textarea(one).value === 'off topic' && puts === 1);                              // theirs, and nothing sent
  radio(one, 'keep').click();
  await settle();
  assert.deepStrictEqual(calls(page, 'PUT')[1].body, { value: { comment: 'off topic' }, choice: 'keep', base_revision: 2 });   // on their revision
});

test('Keep mine re-sends my decision on their revision', async () => {
  let puts = 0;
  const theirs = { item_id: 'cand-000000000001', choice: 'drop', value: { comment: '' }, revision: 5, answered: true, author: 'other owner', updated_at: '2026-11-17T11:00:00Z' };
  const page = open({ extra: (m, p, body) => {
    if (m === 'PUT') {
      puts += 1;
      return puts === 1 ? { status: 409, data: { detail: { message: 'stale', stale: true, current: theirs } } }
        : ok({ item: Object.assign({}, theirs, { choice: body.choice, value: body.value, revision: body.base_revision + 1 }) });
    }
  } });
  await settle();
  const one = cardOf(page, 'Held paper 1');
  radio(one, 'keep').click();
  await settle();
  button(findAll(one, (e) => e.className === 'conflict' && !e.hidden)[0], 'Keep mine').click();
  await settle();
  assert.deepStrictEqual(calls(page, 'PUT')[1].body, { value: { comment: '' }, choice: 'keep', base_revision: 5 });
  assert.strictEqual(statusOf(one), 'Saved');
});

test('a refresh never overwrites a decision being typed, but picks up the other owner\'s change on a clean card', async () => {
  const page = open();
  await settle();
  textarea(cardOf(page, 'Held paper 1')).type('typing...');
  page.state.review = reviewPayload([paper(1, { comment: 'theirs', choice: 'drop', revision: 3, answered: true }), Object.assign(PAPERS()[1], { choice: 'drop', revision: 2 }), PAPERS()[2]]);
  page.timers.tickIntervals();
  await settle();
  assert.strictEqual(textarea(cardOf(page, 'Held paper 1')).value, 'typing...');
  assert.ok(radio(cardOf(page, 'Held paper 2'), 'drop').checked);
});

// ---- filters and bulk marking -----------------------------------------------------------------------------------------------------------------------------
test('the filters change which papers are shown and what the bulk button says', async () => {
  const page = open();
  await settle();
  assert.deepStrictEqual(findAll(page.$('fGroup'), (e) => e.tag === 'option').map((o) => o.textContent), ['All groups', 'Group one', 'Group two']);
  assert.strictEqual(page.$('shown').textContent, 'Showing 3 of 3 papers.');
  assert.strictEqual(page.$('bulkApply').textContent, 'Mark the 3 papers shown');
  page.$('fGroup').value = 'Group two';
  page.$('fGroup').fire('change');
  assert.strictEqual(cards(page).length, 1);
  assert.strictEqual(page.$('bulkApply').textContent, 'Mark the 1 paper shown');
  page.$('fGroup').value = '';
  page.$('fGroup').fire('change');
  page.$('fLikely').click();
  assert.deepStrictEqual(cards(page).map((c) => c.children[0].children[0].textContent), ['Held paper 2']);
  page.$('fLikely').click();
  page.$('fUnresolved').click();
  assert.deepStrictEqual(cards(page).map((c) => c.children[0].children[0].textContent), ['Held paper 2', 'Held paper 3']);
  page.$('fGroup').value = 'Group one';
  page.$('fGroup').fire('change');
  page.$('fLikely').click();
  page.$('fUnresolved').click();
  page.$('fGroup').value = 'Group two';
  page.$('fGroup').fire('change');
  assert.strictEqual(cards(page).length, 0);
  assert.match(page.$('papers').textContent, /No paper matches these filters/);
  assert.ok(page.$('bulkApply').disabled);
});

test('bulk marking sends only the papers shown, with their revisions, after asking; and says what was marked', async () => {
  const page = open({ extra: (m, p, body, state) => {
    if (m === 'POST' && p === `${BASE}/review/bulk`) {
      state.review = reviewPayload(PAPERS().map((x) => (body.papers.some((b) => b.item_id === x.item_id) ? Object.assign(x, { choice: body.choice, revision: x.revision + 1, answered: true }) : x)));
      return ok({ marked: body.papers.map((b) => b.item_id), unchanged: [], section_status: 'draft' });
    }
  } });
  await settle();
  page.$('fUnresolved').click();
  page.$('bulkChoice').value = 'drop';
  page.$('bulkApply').click();
  await settle();
  assert.deepStrictEqual(page.confirms, ['Mark all 2 papers shown as "Drop"? Their comments are kept.']);
  assert.deepStrictEqual(calls(page, 'POST').map((c) => [c.path, c.body]), [[`${BASE}/review/bulk`, { choice: 'drop', papers: [
    { item_id: 'cand-000000000002', base_revision: 1 }, { item_id: 'cand-000000000003', base_revision: 0 }] }]]);
  assert.strictEqual(page.$('bulkResult').textContent, 'Marked 2 papers "Drop".');
  assert.ok(radio(cardOf(page, 'Held paper 3'), 'drop').checked && radio(cardOf(page, 'Held paper 2'), 'drop').checked);
  assert.strictEqual(textarea(cardOf(page, 'Held paper 2')).value, 'worth it');                                         // comments are kept
  page.$('fUnresolved').click();                                                                                        // show every paper again
  assert.ok(!radio(cardOf(page, 'Held paper 1'), 'drop').checked);                                                      // a paper not shown is not touched
});

test('declining the question sends nothing', async () => {
  const page = open({ confirmAnswer: false });
  await settle();
  page.$('bulkApply').click();
  await settle();
  assert.strictEqual(page.confirms.length, 1);
  assert.deepStrictEqual(calls(page, 'POST'), []);
});

test('a stale paper refuses the whole batch, and the page says so plainly with the papers named', async () => {
  const page = open({ extra: (m, p) => {
    if (m === 'POST' && p === `${BASE}/review/bulk`) {
      return { status: 409, data: { detail: { message: '1 of these papers changed since you opened the page, so nothing was marked. Reload and try again.', reason: 'stale',
                                              stale: [{ item_id: 'cand-000000000002', title: HOSTILE }] } } };
    }
  } });
  await settle();
  page.$('bulkApply').click();
  await settle();
  const res = page.$('bulkResult');
  assert.strictEqual(res.className, 'error');
  assert.match(res.textContent, /^1 of these papers changed since you opened the page, so nothing was marked\./);
  assert.match(res.textContent, /Changed by someone else since you opened the page:/);
  assert.ok(res.textContent.includes(HOSTILE));
  noMarkupIn(page);
  assert.strictEqual(calls(page, 'GET', `${BASE}/review`).length, 2);                                                   // the list is reloaded
});

test('more than 100 papers shown, or a paper with an unsaved change, is refused before any request', async () => {
  const many = Array.from({ length: 101 }, (_, n) => paper(n + 1));
  const page = open({ papers: many });
  await settle();
  page.$('bulkApply').click();
  await settle();
  assert.match(page.$('bulkResult').textContent, /101 papers are shown\. Narrow the filters to 100 or fewer, then try again\. Nothing was marked\./);
  assert.deepStrictEqual(page.confirms, []);
  assert.deepStrictEqual(calls(page, 'POST'), []);
  const small = open();
  await settle();
  textarea(cardOf(small, 'Held paper 1')).type('unsaved');
  small.$('bulkApply').click();
  await settle();
  assert.match(small.$('bulkResult').textContent, /unsaved change/);
  assert.deepStrictEqual(calls(small, 'POST'), []);
});

test('any other refusal of a bulk mark is shown in the server\'s words', async () => {
  const page = open({ extra: (m, p) => (m === 'POST' ? { status: 409, data: { detail: 'This engine is not open for edits' } } : null) });
  await settle();
  page.$('bulkApply').click();
  await settle();
  assert.strictEqual(page.$('bulkResult').textContent, 'This engine is not open for edits Nothing was marked.');
});

// ---- read only, Mark final, and the gates ---------------------------------------------------------------------------------------------------------------------
test('a closed engine, or a reader who is not an owner, sees every decision but cannot change one and has no bulk marking', async () => {
  for (const engine of [{ state: 'closed' }, { role: 'admin', may_mark: [] }]) {
    const page = open({ engine });
    await settle();
    const one = cardOf(page, 'Held paper 1');
    assert.ok(radio(one, 'keep').disabled && textarea(one).disabled, JSON.stringify(engine));
    assert.ok(page.$('bulkBox').hidden);
    assert.ok(!page.$('banner').hidden && /can be read but not changed|can read this review but not change it/.test(page.$('banner').textContent));
    radio(one, 'keep').click();
    await settle();
    assert.deepStrictEqual(calls(page, 'PUT'), []);
  }
});

test('4c-1: a paper card is headed by its title, carries its anchor and its id in small grey text, and on a closed engine says it is read only', async () => {
  const page = open({ engine: { state: 'closed' } });
  await settle();
  const one = page.$('item-cand-000000000001');
  assert.ok(one, 'the card carries its anchor, for the engine page\'s "What is left" links');
  assert.strictEqual(one.children[0].children[0].textContent, 'Held paper 1');
  assert.strictEqual(findAll(one, (e) => e.className === 'itemid')[0].textContent, 'cand-000000000001');
  assert.match(one.className, /\breadonly\b/);
  const note = findAll(one, (e) => /readonly-note/.test(e.className))[0];
  assert.ok(note && !note.hidden && /Read only: this engine is closed/.test(note.textContent));
  assert.deepStrictEqual(findAll(one, (e) => ['input', 'textarea', 'select', 'button'].includes(e.tag) && !e.disabled).map((e) => e.tag), [], 'nothing on the card is enabled');
  const openPage = open();
  await settle();
  const live = openPage.$('item-cand-000000000001');
  assert.ok(!/\breadonly\b/.test(live.className) && findAll(live, (e) => /readonly-note/.test(e.className))[0].hidden, 'an open engine: no read-only marking');
  const untitled = open({ papers: [paper(9, { title: null })] });
  await settle();
  assert.strictEqual(untitled.$('item-cand-000000000009').children[0].children[0].textContent, 'doi:10.9998/held.9', 'no title: the identifier, never the id first');
});

test('Mark final shows only to someone who may mark the review, is disabled until it is ready, and posts once', async () => {
  const page = open({ section: { ready: true, open: 0, answered: 3 }, extra: (m, p) => (m === 'POST' && p === `${BASE}/sections/review/final` ? ok({ section: 'review', status: 'final' }) : null) });
  await settle();
  assert.ok(!page.$('finalRow').hidden && !page.$('markFinal').disabled);
  page.$('markFinal').click();
  await settle();
  assert.deepStrictEqual(calls(page, 'POST').map((c) => c.path), [`${BASE}/sections/review/final`]);
  assert.match(page.$('msg').textContent, /now marked final/);
  const notReady = open();
  await settle();
  assert.ok(notReady.$('markFinal').disabled);
  assert.match(notReady.$('finalNote').textContent, /2 paper\(s\) without a decision/);
  const notMine = open({ engine: { may_mark: ['scope'] } });
  await settle();
  assert.ok(notMine.$('finalRow').hidden);
});

test('the review page needs a session and an engine, and an engine with no hold list is said plainly', async () => {
  const anon = run('candidates.html', ['common.js', 'candidates.js'], { search: '?engine=eng-x', token: '', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.ok(!anon.$('signin').hidden && anon.calls.length === 0);
  const lost = run('candidates.html', ['common.js', 'candidates.js'], { search: '?engine=ENG_BAD', route: () => ({ status: 500, data: {} }) });
  await settle();
  assert.ok(lost.calls.length === 0 && /needs the link from the engine page/.test(lost.$('msg').textContent));
  const none = open({ extra: (m, p) => (p === `${BASE}/review` ? { status: 404, data: { detail: 'Not found' } } : null) });
  await settle();
  assert.ok(none.$('review').hidden && /no hold list to review/.test(none.$('msg').textContent));
});

test('the page polls the engine and the review', async () => {
  const page = open();
  await settle();
  page.timers.tickIntervals();
  await settle();
  assert.strictEqual(calls(page, 'GET', `${BASE}/review`).length, 2);
  assert.strictEqual(calls(page, 'GET', BASE).length, 2);
});

// ---- the engine page's link ------------------------------------------------------------------------------------------------------------------------------------
test('the engine page links its "Hold list: review" row and left items to the review page, and lets the holder delegate it', async () => {
  const sections = [['scope', 'Scope and use case'], ['questions', 'Research questions'], ['keywords', 'Keywords and horizons'], ['seeds', 'Seed papers: confirm'],
                    ['review', 'Hold list: review']].map(([key, title]) => ({ key, title, status: 'draft', items: 3, open: 1, answered: 2, disagreed: 0, final: 0, approved: 0, ready: false }));
  const page = run('engine.html', ['common.js', 'engine.js'], {
    search: '?engine=eng-x',
    route: (m, p) => {
      if (m === 'GET' && p === BASE) {
        return ok(Object.assign(enginePayload(), { template_version: 1, bundles: [], progress: { template_version: 1, sections,
          left: [{ section: 'review', item_id: 'cand-000000000001', reason: 'unanswered' }, { section: 'scope', item_id: 'use-case', reason: 'unanswered' }], left_total: 2,
          waiting_on: { who: ['owners'], line: 'Waiting on the owners' } } }));
      }
      if (m === 'GET' && p === `${BASE}/delegations`) return ok({ delegations: [] });
      if (m === 'PUT' && p === `${BASE}/delegations`) return ok({ scope: ['review'] });
      return { status: 500, data: {} };
    },
  });
  await settle();
  const links = findAll(page.doc.body, (e) => e.tag === 'a').map((a) => [a.textContent, a.attrs.href]);
  assert.ok(links.some(([t, href]) => t === 'Open' && href === 'candidates.html?engine=eng-x'), JSON.stringify(links));
  assert.ok(links.some(([t, href]) => t === 'Open' && href === 'section.html?engine=eng-x&section=scope'));
  // 4c-1: a left item links to its own card; with no label from the server (an older server), the id is the last resort for its text
  assert.ok(links.some(([t, href]) => t === 'cand-000000000001' && href === 'candidates.html?engine=eng-x#item-cand-000000000001'), JSON.stringify(links));
  assert.ok(!links.some(([, href]) => /section=review/.test(href || '')));
  assert.ok(page.$('d_review'));
  page.timers.tickIntervals();
  await settle();
  assert.strictEqual(findAll(page.$('dsections'), (e) => e.attrs.id === 'd_review').length, 1);                          // added once, not on every refresh
  page.$('dscopeSome').click();
  page.$('d_review').click();
  page.$('delegate').click();
  await settle();
  assert.deepStrictEqual(page.calls.filter((c) => c.method === 'PUT').map((c) => c.body), [{ to: 'other_owner', scope: ['review'] }]);
});

test('an engine with no hold list shows no review row and offers no review box to delegate', async () => {
  const page = run('engine.html', ['common.js', 'engine.js'], {
    search: '?engine=eng-x',
    route: (m, p) => {
      if (m === 'GET' && p === BASE) {
        return ok(Object.assign(enginePayload({ may_mark: ['scope', 'questions', 'keywords', 'seeds'] }), { template_version: 1, bundles: [], progress: { template_version: 1,
          sections: ['scope', 'questions', 'keywords', 'seeds'].map((key) => ({ key, title: key, status: 'draft', items: 1, open: 1, answered: 0, disagreed: 0, final: 0, approved: 0, ready: false })),
          left: [], left_total: 0, waiting_on: { who: [], line: 'Nothing is waiting.' } } }));
      }
      if (m === 'GET' && p === `${BASE}/delegations`) return ok({ delegations: [] });
      return { status: 500, data: {} };
    },
  });
  await settle();
  assert.ok(!page.$('d_review'));
  assert.ok(!findAll(page.doc.body, (e) => e.tag === 'a' && /candidates\.html/.test(e.attrs.href || '')).length);
});
