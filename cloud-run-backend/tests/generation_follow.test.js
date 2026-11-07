'use strict';
// Dashboard fixes, change 1: the page starts a generation and follows it by polling; it never depends on the long request's answer.
// Runs the real public/generation-follow.js with a scripted fetch and a manual clock. No network, no waiting.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const GF = require('../../public/generation-follow.js');

const JOB = '11111111-2222-4333-8444-555555555555';

function harness(handlers) {
    const clock = { t: 1000000, timers: [], id: 0 };
    const calls = [], events = [];
    const h = {
        clock, calls, events,
        now: () => clock.t,
        setTimeout: (fn, ms) => { const id = ++clock.id; clock.timers.push({ id, fn, at: clock.t + ms }); return id; },
        clearTimeout: (id) => { clock.timers = clock.timers.filter((x) => x.id !== id); },
        fetch: (url, opts) => { calls.push({ url, opts }); const isPost = opts && opts.method === 'POST'; return (isPost ? handlers.post : handlers.status)(url, opts); },
        headers: (extra) => Object.assign({}, extra || {}, { 'X-Subscriber-Token': 'tok' }),
    };
    // run every due timer, advancing the clock by `ms`, letting promises settle between steps
    h.advance = async (ms) => {
        const end = clock.t + ms;
        for (let guard = 0; guard < 2000; guard++) {
            await settle();
            const due = clock.timers.filter((x) => x.at <= end).sort((a, b) => a.at - b.at)[0];
            if (!due) { break; }
            clock.timers = clock.timers.filter((x) => x.id !== due.id);
            clock.t = Math.max(clock.t, due.at);
            due.fn();
        }
        clock.t = end;
        await settle();
    };
    return h;
}
const settle = async () => { for (let i = 0; i < 20; i++) { await Promise.resolve(); await new Promise((r) => setImmediate(r)); } };
const reply = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });
const never = () => new Promise(() => {});

function begin(h, extra) {
    const seen = [];
    const o = Object.assign({
        base: 'https://api.example.test', jobId: JOB, startUrl: 'https://api.example.test/generate-podcast-with-subscriber?subscriber_id=s1', body: '{"topic":"t"}',
        headers: h.headers, fetch: h.fetch, setTimeout: h.setTimeout, clearTimeout: h.clearTimeout, now: h.now,
        onRunning: (d) => seen.push(['running', d.status]), onDone: (d) => seen.push(['done', d.episode_id]), onFailed: (d) => seen.push(['failed', d.unit_returned]),
        onRefused: (s, t) => seen.push(['refused', s, t]), onLost: () => seen.push(['lost']),
    }, extra || {});
    const handle = GF.start(o);
    return { seen, handle };
}
const statusCalls = (h) => h.calls.filter((c) => !c.opts || c.opts.method !== 'POST').length;

test('newJobId makes a version 4 UUID, with or without randomUUID', () => {
    const re = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    assert.match(GF.newJobId(), re);
    assert.match(GF.newJobId({ getRandomValues: (b) => { b.fill(255); return b; } }), re);
    assert.match(GF.newJobId({}), re);
    assert.notStrictEqual(GF.newJobId(), GF.newJobId());
});

test('it sends the request with the chosen job id and the session, and looks at the job at once', async () => {
    const h = harness({ post: never, status: () => reply(404, {}) });
    begin(h);
    await settle();
    const post = h.calls.find((c) => c.opts && c.opts.method === 'POST');
    assert.strictEqual(post.url, 'https://api.example.test/generate-podcast-with-subscriber?subscriber_id=s1&client_job_id=' + JOB);
    assert.strictEqual(post.opts.headers['X-Subscriber-Token'], 'tok');
    assert.strictEqual(post.opts.headers['Content-Type'], 'application/json');
    assert.strictEqual(post.opts.body, '{"topic":"t"}');
    assert.strictEqual(statusCalls(h), 1);
    assert.strictEqual(h.calls[h.calls.length - 1].url.includes('/api/subscribers/jobs/' + JOB + '/status') || h.calls[0].url.includes('/api/subscribers/jobs/' + JOB + '/status'), true);
});

test('a request that never answers does not matter: the poll finishes the job', async () => {
    let n = 0;
    const h = harness({ post: never, status: () => { n++; return n < 3 ? reply(200, { state: 'running', status: 'generating_content' }) : reply(200, { state: 'completed', episode_id: 'ever-x-1' }); } });
    const { seen } = begin(h);
    await h.advance(60000);
    assert.deepStrictEqual(seen, [['running', 'generating_content'], ['running', 'generating_content'], ['done', 'ever-x-1']]);
    const after = statusCalls(h);
    await h.advance(60000);
    assert.strictEqual(statusCalls(h), after, 'it stops polling once the job is done');
});

test('a dropped connection shows nothing while the job runs, and the poll still reports the finish', async () => {
    let n = 0;
    const h = harness({ post: () => Promise.reject(new TypeError('Failed to fetch')), status: () => (++n < 4 ? reply(200, { state: 'running' }) : reply(200, { state: 'completed', episode_id: 'e' })) });
    const { seen } = begin(h);
    await h.advance(1000);
    assert.ok(!seen.some((e) => e[0] === 'refused' || e[0] === 'lost' || e[0] === 'failed'), 'nothing alarming was shown: ' + JSON.stringify(seen));
    await h.advance(60000);
    assert.deepStrictEqual(seen[seen.length - 1], ['done', 'e']);
});

test('a 502, 503, 504 or 500 from the long request is not shown either: the job may be running', async () => {
    for (const code of [500, 502, 503, 504]) {
        const h = harness({ post: () => reply(code, { detail: 'upstream' }), status: () => reply(200, { state: 'running' }) });
        const { seen } = begin(h);
        await h.advance(12000);
        assert.ok(!seen.some((e) => e[0] === 'refused'), code + ' was shown as a refusal');
        assert.ok(statusCalls(h) >= 2, code + ': polling continued');
    }
});

test('a quick refusal (4xx) is shown once with the server text, and polling stops', async () => {
    for (const [code, body, text] of [[400, { detail: 'Choose a category: Biology.' }, 'Choose a category: Biology.'], [429, { detail: 'monthly limit reached' }, 'monthly limit reached'],
                                       [422, { detail: [{ msg: 'Field required' }] }, 'Field required'], [401, {}, ''], [409, { detail: 'That job id is already in use' }, 'That job id is already in use']]) {
        const h = harness({ post: () => reply(code, body), status: () => reply(404, {}) });
        const { seen } = begin(h);
        await h.advance(30000);
        assert.deepStrictEqual(seen, [['refused', code, text]]);
        const polled = statusCalls(h);
        await h.advance(30000);
        assert.strictEqual(statusCalls(h), polled, code + ': polling stopped');
    }
});

test('a 404 from the status route is quiet at first (the job is made a moment after the request arrives)', async () => {
    let n = 0;
    const h = harness({ post: never, status: () => (++n < 4 ? reply(404, {}) : reply(200, { state: 'completed', episode_id: 'e' })) });
    const { seen } = begin(h);
    await h.advance(40000);
    assert.deepStrictEqual(seen, [['done', 'e']]);
});

test('a job that stays 404 past the grace period is called lost, once; a job that never finishes is given up after 45 minutes', async () => {
    const h = harness({ post: never, status: () => reply(404, {}) });
    const { seen } = begin(h);
    await h.advance(GF.NOT_FOUND_GRACE_MS - 10000);
    assert.deepStrictEqual(seen, []);
    await h.advance(30000);
    assert.deepStrictEqual(seen, [['lost']]);
    const h2 = harness({ post: never, status: () => reply(200, { state: 'running' }) });
    const r2 = begin(h2);
    await h2.advance(GF.GIVE_UP_MS + 20000);
    assert.strictEqual(r2.seen[r2.seen.length - 1][0], 'lost');
    assert.strictEqual(r2.seen.filter((e) => e[0] === 'lost').length, 1);
});

test('a failed job is reported once with whether the unit came back', async () => {
    const h = harness({ post: () => reply(500, { detail: 'Podcast generation failed' }), status: () => reply(200, { state: 'failed', unit_returned: true }) });
    const { seen } = begin(h);
    await h.advance(20000);
    assert.deepStrictEqual(seen, [['failed', true]]);
});

test('when the long request does answer 200, the page looks at the job straight away', async () => {
    let resolvePost;
    const h = harness({ post: () => new Promise((r) => { resolvePost = r; }), status: () => reply(200, { state: 'running' }) });
    begin(h);
    await settle();
    const before = statusCalls(h);
    resolvePost({ ok: true, status: 200, json: () => Promise.resolve({}) });
    await settle();
    assert.ok(statusCalls(h) > before, 'an immediate look after the answer');
});

test('stop() ends everything and nothing is reported afterwards', async () => {
    const h = harness({ post: never, status: () => reply(200, { state: 'running' }) });
    const { seen, handle } = begin(h);
    await h.advance(6000);
    handle.stop();
    const n = statusCalls(h), shown = seen.length;
    await h.advance(60000);
    assert.strictEqual(statusCalls(h), n);
    assert.strictEqual(seen.length, shown);
});

test('the dashboard loads this script and uses it for both ways of starting a generation; the old "await the long request" code is gone', () => {
    const html = fs.readFileSync(path.join(__dirname, '..', '..', 'public', 'subscriber-dashboard.html'), 'utf8');
    assert.ok(html.includes('<script src="/generation-follow.js"></script>'));
    assert.strictEqual((html.match(/GenerationFollow\.start\(/g) || []).length, 1, 'one place starts and follows a job');
    assert.strictEqual((html.match(/GenerationFollow\.newJobId\(/g) || []).length, 1);
    assert.strictEqual((html.match(/this\.beginGeneration\(/g) || []).length, 2, 'both the topic form and the paper form use it');
    assert.ok(!/await fetch\(`\$\{this\.API_BASE_URL\}\/generate-podcast/.test(html), 'a page call still awaits the generation request');
    assert.ok(html.includes('Generating'), 'it says so at once');
    const generate = html.slice(html.indexOf('async generatePodcast()'), html.indexOf('authHeaders(extra'));
    assert.ok(!generate.includes('Network error'), 'a dropped connection is not reported as an error while the job may run');
});
