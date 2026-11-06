/* Shared by the onboarding workspace pages (design 5.8). No third-party script and no HTML-parsing API: every piece of text, whether it came from the server or from a
   person, reaches the page only through textContent / text nodes. Pure helpers are exported for the Node tests. */
(function (root) {
    'use strict';
    var API = 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app';
    var ENGINE_RE = /^[a-z0-9][a-z0-9-]{1,40}$/;
    var SECTION_KEYS = ['scope', 'questions', 'keywords', 'seeds'];
    var SECTION_TITLES = { scope: 'Scope and use case', questions: 'Research questions', keywords: 'Keywords and horizons', seeds: 'Seed papers: confirm' };
    var REASONS = {
        not_ready: 'not ready yet', not_delegated: 'not delegated to you', already_final: 'already final', approved: 'already approved', rejected: 'sent back, so revise it first',
        unanswered: 'not answered yet', disagreed: 'an open disagreement'
    };

    // ---- pure helpers (tested in Node) ---------------------------------------------------------------------------------------------------------------
    function linesOf(text) {
        return String(text || '').split('\n').map(function (s) { return s.trim(); }).filter(function (s) { return s; });
    }

    function mergeText(theirs, mine) {
        theirs = String(theirs || ''); mine = String(mine || '');
        if (!mine.trim() || theirs.indexOf(mine) !== -1) { return theirs; }
        if (!theirs.trim() || mine.indexOf(theirs) !== -1) { return mine; }
        return theirs + '\n\n' + mine;
    }

    function mergeLists(theirs, mine) {
        var out = (theirs || []).slice();
        (mine || []).forEach(function (m) { if (out.indexOf(m) === -1) { out.push(m); } });
        return out;
    }

    function problem(out) {
        var d = out && out.data ? out.data.detail : null;
        if (typeof d === 'string') { return d; }
        if (d && typeof d.message === 'string') {
            return d.reason && REASONS[d.reason] ? d.message + ' (' + REASONS[d.reason] + ')' : d.message;
        }
        if (out && out.status === 422) { return 'Please check what you entered.'; }
        if (out && out.status === 404) { return 'Not found. Check that you are signed in with the account that was invited.'; }
        return 'Something went wrong. Please try again.';
    }

    function describe(item) {
        if (!item) { return ''; }
        var v = item.value, c = item.choice ? '[' + item.choice + '] ' : '';
        if (typeof v === 'string') { return v; }
        if (Array.isArray(v)) { return v.join('\n'); }
        if (v && typeof v === 'object') {
            var parts = [];
            if (v.wording) { parts.push(v.wording); }
            if (v.text) { parts.push(v.text); }
            if (v.reason) { parts.push('Reason: ' + v.reason); }
            if (v.comment) { parts.push(v.comment); }
            if (v.centrality) { parts.push('(' + v.centrality + ')'); }
            if (Array.isArray(v.terms) && v.terms.length) { parts.push('Terms: ' + v.terms.map(function (t) { return t.text + ' [' + t.choice + ']'; }).join(', ')); }
            return c + parts.join(' ');
        }
        return c;
    }

    function scopeText(scope) {
        if (scope === 'all') { return 'all sections'; }
        return (scope || []).map(function (k) { return SECTION_TITLES[k] || k; }).join(', ');
    }

    var pure = { linesOf: linesOf, mergeText: mergeText, mergeLists: mergeLists, problem: problem, describe: describe, scopeText: scopeText, ENGINE_RE: ENGINE_RE,
                 SECTION_KEYS: SECTION_KEYS, SECTION_TITLES: SECTION_TITLES, REASONS: REASONS };
    if (typeof module !== 'undefined' && module.exports) { module.exports = pure; }
    if (!root || !root.document) { return; }

    // ---- browser helpers -----------------------------------------------------------------------------------------------------------------------------
    var doc = root.document;

    function sessionToken() {
        try {
            var s = JSON.parse(root.localStorage.getItem('subscriber') || 'null');
            return s && typeof s.session_token === 'string' ? s.session_token : '';
        } catch (e) { return ''; }
    }

    function param(name) {
        var m = new RegExp('[?&]' + name + '=([^&#]*)').exec(root.location.search || '');
        if (!m) { return ''; }
        try { return decodeURIComponent(m[1]); } catch (e) { return ''; }
    }

    function call(method, path, body) {
        var headers = { 'X-Subscriber-Token': sessionToken() }, init = { method: method, headers: headers };
        if (body !== undefined) { headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
        return root.fetch(API + path, init).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (d) { return { status: r.status, ok: r.ok, data: d }; });
        });
    }

    var PROPS = { id: 1, type: 1, name: 1, value: 1, rows: 1, maxlength: 1, href: 1, role: 1, placeholder: 1, target: 1, rel: 1 };

    // h('div', {class: 'x', text: 'plain text', id: 'y'}, [child, 'text child', ...]): builds elements; text only ever through textContent / text nodes.
    function h(tag, attrs, kids) {
        var e = doc.createElement(tag);
        Object.keys(attrs || {}).forEach(function (k) {
            var v = attrs[k];
            if (k === 'class') { e.className = v; }
            else if (k === 'text') { e.textContent = String(v); }
            else if (k === 'disabled' || k === 'checked' || k === 'hidden' || k === 'selected') { e[k] = !!v; }
            else if (PROPS[k]) { e.setAttribute(k, String(v)); if (k === 'value') { e.value = String(v); } }
        });
        (kids || []).forEach(function (kid) {
            if (kid === null || kid === undefined) { return; }
            e.appendChild(typeof kid === 'string' ? doc.createTextNode(kid) : kid);
        });
        return e;
    }

    function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }

    function when(iso) {
        if (!iso) { return ''; }
        var d = new Date(iso);
        return isNaN(d.getTime()) ? '' : d.toLocaleString();
    }

    function engineIdOrNull() {
        var e = param('engine');
        return ENGINE_RE.test(e) && e.indexOf('__') === -1 ? e : null;
    }

    function say(node, text, isError) {
        node.textContent = text;
        node.className = isError ? 'error' : 'ok';
    }

    function poll(fn, ms) {
        var id = root.setInterval(function () { if (!doc.hidden) { fn(); } }, ms);
        return function () { root.clearInterval(id); };
    }

    root.OB = Object.assign({ API: API, call: call, h: h, clear: clear, when: when, param: param, engineId: engineIdOrNull, say: say, poll: poll, sessionToken: sessionToken }, pure);
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this)));
