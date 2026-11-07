/* Starting a generation and following it (dashboard fixes, 2026-11-07).
 *
 * A generation request runs the whole job inside the request (the server cannot run it in the background), so it stays open for minutes and may drop. The page
 * therefore never depends on its answer: it chooses the job's id, sends the request WITHOUT waiting for it, and follows the job by polling an owner-only status route.
 *   - A quick refusal (a 4xx: a missing category, the monthly limit, a bad session) is shown, and following stops.
 *   - A dropped connection, a 5xx or a gateway timeout shows NOTHING: the job may still be running, and polling decides.
 *   - A 404 from the status route is expected for a moment (the job is created a little after the request arrives); only after a grace period is the job
 *     called lost. Plain JavaScript, no third-party code, text only. */
(function (root) {
    'use strict';

    var POLL_MS = 5000;
    var NOT_FOUND_GRACE_MS = 90000;
    var GIVE_UP_MS = 45 * 60 * 1000;

    function newJobId(cryptoObj) {
        var c = cryptoObj || root.crypto;
        if (c && typeof c.randomUUID === 'function') { return c.randomUUID(); }
        var b = new Uint8Array(16);
        if (c && typeof c.getRandomValues === 'function') { c.getRandomValues(b); } else { for (var i = 0; i < 16; i++) { b[i] = Math.floor(Math.random() * 256); } }
        b[6] = (b[6] & 0x0f) | 0x40;
        b[8] = (b[8] & 0x3f) | 0x80;
        var h = Array.prototype.map.call(b, function (x) { return (x < 16 ? '0' : '') + x.toString(16); }).join('');
        return h.slice(0, 8) + '-' + h.slice(8, 12) + '-' + h.slice(12, 16) + '-' + h.slice(16, 20) + '-' + h.slice(20);
    }

    function detailText(d) {
        if (!d) { return ''; }
        if (typeof d.detail === 'string') { return d.detail; }
        if (Array.isArray(d.detail) && d.detail.length && d.detail[0] && d.detail[0].msg) { return String(d.detail[0].msg); }
        return '';
    }

    /* o: base, jobId, startUrl (without the job id), body (a string), headers() -> object, plus the callbacks
     *    onRunning(data), onDone(data), onFailed(data), onRefused(status, text), onLost()
     *    and, for tests, fetch, setTimeout, clearTimeout, now. Returns { stop() }. */
    function start(o) {
        var f = o.fetch || root.fetch.bind(root);
        var setT = o.setTimeout || root.setTimeout.bind(root);
        var clearT = o.clearTimeout || root.clearTimeout.bind(root);
        var now = o.now || Date.now;
        var begun = now(), timer = null, stopped = false, polling = false;

        function stop() { stopped = true; if (timer) { clearT(timer); timer = null; } }
        function finish(cb, a, b) { if (stopped) { return; } stop(); if (cb) { cb(a, b); } }
        function later() { if (!stopped) { timer = setT(poll, POLL_MS); } }

        function poll() {
            timer = null;
            if (stopped || polling) { return; }
            polling = true;
            f(o.base + '/api/subscribers/jobs/' + encodeURIComponent(o.jobId) + '/status', { headers: o.headers(), cache: 'no-store' }).then(function (res) {
                if (res.ok) {
                    return res.json().then(function (d) {
                        if (d && d.state === 'completed') { finish(o.onDone, d); }
                        else if (d && d.state === 'failed') { finish(o.onFailed, d); }
                        else { if (o.onRunning && !stopped) { o.onRunning(d || {}); } checkAge(); }
                    });
                }
                if (res.status === 404 && now() - begun > NOT_FOUND_GRACE_MS) { return finish(o.onLost); }      // never started, or not ours
                checkAge();
            }).catch(function () { checkAge(); }).then(function () { polling = false; later(); });
        }

        function checkAge() { if (!stopped && now() - begun > GIVE_UP_MS) { finish(o.onLost); } }

        // The long request. Its answer is used ONLY to stop early on a quick refusal; everything else is left to the polling.
        var sent;
        try {
            sent = f(o.startUrl + (o.startUrl.indexOf('?') === -1 ? '?' : '&') + 'client_job_id=' + encodeURIComponent(o.jobId), {
                method: 'POST', headers: o.headers({ 'Content-Type': 'application/json' }), body: o.body
            });
        } catch (e) { sent = Promise.reject(e); }
        sent.then(function (res) {
            if (res.status >= 400 && res.status < 500) {
                return res.json().catch(function () { return {}; }).then(function (d) { finish(o.onRefused, res.status, detailText(d)); });
            }
            if (res.ok && !stopped && !polling) { stopTimerAndPoll(); }        // it answered: look now instead of waiting for the next tick
        }).catch(function () { /* a dropped connection is not an error: the job may be running; polling decides */ });

        function stopTimerAndPoll() { if (timer) { clearT(timer); timer = null; } poll(); }

        poll();
        return { stop: stop };
    }

    var api = { start: start, newJobId: newJobId, POLL_MS: POLL_MS, NOT_FOUND_GRACE_MS: NOT_FOUND_GRACE_MS, GIVE_UP_MS: GIVE_UP_MS };
    if (typeof module !== 'undefined' && module.exports) { module.exports = api; }
    root.GenerationFollow = api;
})(typeof window !== 'undefined' ? window : globalThis);
