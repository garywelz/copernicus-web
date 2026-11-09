/* Gary's review panel (onboarding PR 3b-1, design 5.1): the engines and their sections, a section's proposed-vs-current diff, the owners' history and comment
   threads, and Approve / Send back with a note. Admin key in the X-Admin-API-Key header, as the other admin pages do.
   TEXT ONLY: nothing the server or an owner wrote is ever parsed as HTML. Every element is built with createElement and every string goes in through textContent. */
(function () {
    'use strict';
    var API = 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app';
    var KEY_NAME = 'admin_api_key';
    var current = null;          // {engine, section, diff} for the section being reviewed: the revision and hash sent with a decision are the ones the diff showed

    function $(id) { return document.getElementById(id); }
    function readKey() { try { return window.localStorage.getItem(KEY_NAME) || ''; } catch (e) { return ''; } }
    function clear(el) { while (el.firstChild) { el.removeChild(el.firstChild); } }

    function h(tag, props, kids) {
        var el = document.createElement(tag);
        Object.keys(props || {}).forEach(function (k) {
            if (k === 'text') { el.textContent = props[k] === null || props[k] === undefined ? '' : String(props[k]); }
            else if (k === 'class') { el.className = props[k]; }
            else if (k === 'checked') { el.checked = !!props[k]; }
            else { el.setAttribute(k, props[k]); }
        });
        (kids || []).forEach(function (kid) { el.appendChild(typeof kid === 'string' ? document.createTextNode(kid) : kid); });
        return el;
    }

    function say(text, bad) {
        var el = $('reviewResult');
        el.textContent = text;
        el.className = bad ? 'error' : 'ok';
    }

    function call(method, path, body) {
        var headers = { 'X-Admin-API-Key': readKey() };
        if (body !== undefined) { headers['Content-Type'] = 'application/json'; }
        return fetch(API + path, { method: method, headers: headers, body: body === undefined ? undefined : JSON.stringify(body) })
            .then(function (res) { return res.json().catch(function () { return {}; }).then(function (out) { return { ok: res.ok, status: res.status, data: out }; }); });
    }

    function problem(r) {
        var d = r.data && r.data.detail;
        if (typeof d === 'string') { return d; }
        if (d && typeof d.message === 'string') { return d.message; }
        if (r.status === 401) { return 'The admin key is missing or wrong.'; }
        if (r.status === 404) { return 'Not found.'; }
        return 'Something went wrong (' + r.status + ').';
    }

    function age(seconds) {
        if (seconds === null || seconds === undefined) { return ''; }
        if (seconds < 3600) { return Math.floor(seconds / 60) + ' min'; }
        if (seconds < 172800) { return Math.floor(seconds / 3600) + ' h'; }
        return Math.floor(seconds / 86400) + ' days';
    }

    function valueText(v, choice) {
        var c = choice ? '[' + choice + '] ' : '';
        if (v === null || v === undefined) { return c + '(not answered)'; }
        return c + (typeof v === 'string' ? v : JSON.stringify(v));
    }

    // ---- the engines panel ---------------------------------------------------------------------------------------------------------------------------
    function renderEngines(engines) {
        var box = $('engineList');
        clear(box);
        if (!engines.length) { box.textContent = 'No engines.'; return; }
        engines.forEach(function (e) {
            var rows = e.sections.map(function (s) {
                var open = h('button', { type: 'button', class: 'small', text: s.status === 'final' ? 'Review' : 'View' });
                open.addEventListener('click', function () { openSection(e.engine_id, s.key); });
                return h('tr', {}, [h('td', { text: s.title }), h('td', { text: s.status }), h('td', { text: s.revision }), h('td', { text: s.items + ' items' + (s.ready ? ', ready' : '') }),
                                    h('td', { text: s.waiting_on.label }), h('td', { text: age(s.age_seconds) }), h('td', {}, [open])]);
            });
            box.appendChild(h('h3', { text: (e.label || e.engine_id) + ' (' + e.engine_id + ') · ' + e.state + ' · ' + (e.repo || 'no repository') + (e.awaiting_review ? ' · ' + e.awaiting_review + ' awaiting review' : '') }));
            box.appendChild(h('table', {}, [h('tr', {}, ['Section', 'Status', 'Revision', 'Items', 'Waiting on', 'In this status', ''].map(function (t) { return h('th', { text: t }); }))].concat(rows)));
        });
    }

    function loadEngines() {
        if (!readKey()) { say('Save the admin key first.', true); return; }
        call('GET', '/api/admin/onboarding/engines').then(function (r) {
            if (r.ok) { renderEngines(r.data.engines || []); } else { say('Could not load engines: ' + problem(r), true); }
        }).catch(function (e) { say('Could not load engines: ' + e.message, true); });
    }

    // ---- one section ---------------------------------------------------------------------------------------------------------------------------------
    function renderDiff(d) {
        var box = $('diffBox');
        clear(box);
        box.appendChild(h('p', { class: 'note', text: d.no_repo ? 'This engine has no repository: every file is shown as an add against an empty tree.'
            : 'Against ' + d.repo + ' main, commit ' + (d.base.commit_sha ? d.base.commit_sha.slice(0, 12) : '(could not be read)') + '.' }));
        if (d.note && !d.no_repo) { box.appendChild(h('p', { class: 'note', text: d.note })); }
        d.files.forEach(function (f) {
            var state = f.base_state === 'unavailable' ? ' · current file unavailable (the whole proposed file is shown)' : f.base_state === 'missing' ? ' · not in the repository yet' : '';
            box.appendChild(h('h4', { text: f.path + ' · ' + f.action + state + ' · +' + f.added + ' -' + f.removed }));
            f.notes.forEach(function (n) { box.appendChild(h('p', { class: 'error', text: n })); });
            var pre = h('div', { class: 'diff' });
            f.lines.forEach(function (l) {
                pre.appendChild(h('div', { class: l.t === '+' ? 'dadd' : l.t === '-' ? 'ddel' : l.t === '@' ? 'dhunk' : 'dctx', text: (l.t === '@' ? '' : l.t) + l.text }));
            });
            if (f.truncated) { pre.appendChild(h('div', { class: 'dhunk', text: '(the diff is cut off here)' })); }
            if (!f.lines.length) { pre.appendChild(h('div', { class: 'dctx', text: '(no differences)' })); }
            box.appendChild(pre);
        });
    }

    function renderDetail(section) {
        var box = $('historyBox');
        clear(box);
        section.items.forEach(function (it) {
            var kids = [h('div', { text: valueText(it.value, it.choice) })];
            (it.history || []).forEach(function (hs) { kids.push(h('div', { class: 'note', text: 'Revision ' + hs.revision + ' by ' + hs.author + ': ' + valueText(hs.value, hs.choice) })); });
            (it.comments || []).forEach(function (c) {
                kids.push(h('div', { class: 'comment', text: c.author + (c.kind === 'disagree' ? ' (disagrees)' : '') + (c.resolved ? ' (resolved)' : '') + ': ' + c.body }));
            });
            box.appendChild(h('details', {}, [h('summary', { text: it.item_id + ' · revision ' + it.revision }), h('div', {}, kids)]));
        });
    }

    function openSection(engine, section) {
        current = null;
        if (!$('bundleEngine').value) { $('bundleEngine').value = engine; }
        $('review').hidden = false;
        $('decideBox').hidden = true;
        clear($('diffBox')); clear($('historyBox'));
        $('reviewTitle').textContent = engine + ' · ' + section;
        $('reviewState').textContent = 'Loading...';
        call('GET', '/api/admin/onboarding/engines/' + encodeURIComponent(engine)).then(function (r) {
            if (!r.ok) { $('reviewState').textContent = 'Could not load: ' + problem(r); return null; }
            var det = r.data.details.filter(function (d) { return d.section.key === section; })[0];
            var s = det.section;
            $('reviewTitle').textContent = (r.data.label || engine) + ' · ' + s.title;
            $('reviewState').textContent = 'Status: ' + s.status + ' · revision ' + s.revision + (s.rejection_note ? ' · sent back earlier: ' + s.rejection_note : '');
            renderDetail(det);
            if (s.status !== 'final' && s.status !== 'approved') { $('diffBox').appendChild(h('p', { class: 'note', text: 'Only a final or approved section has a diff.' })); return null; }
            return call('GET', '/api/admin/onboarding/engines/' + encodeURIComponent(engine) + '/diff?section=' + encodeURIComponent(section)).then(function (d) {
                if (!d.ok) { $('diffBox').appendChild(h('p', { class: 'error', text: 'No diff: ' + problem(d) })); return; }
                renderDiff(d.data);
                current = { engine: engine, section: section, diff: d.data };
                $('decideBox').hidden = d.data.section_status !== 'final';
                $('decisionNote').value = '';
            });
        }).catch(function (e) { $('reviewState').textContent = 'Could not load: ' + e.message; });
    }

    function decide(what) {
        if (!current) { say('Open a final section first.', true); return; }
        var note = $('decisionNote').value;
        if (what === 'reject' && !note.trim()) { say('A note is required to send a section back.', true); return; }
        if (!window.confirm(what === 'approve' ? 'Approve this section at revision ' + current.diff.revision + '?' : 'Send this section back to draft with your note?')) { return; }
        var c = current;
        $('approve').disabled = true; $('reject').disabled = true;
        call('POST', '/api/admin/onboarding/engines/' + encodeURIComponent(c.engine) + '/sections/' + encodeURIComponent(c.section) + '/' + what,
             { note: note, expected_revision: c.diff.revision, expected_content_sha256: c.diff.content_sha256 }).then(function (r) {
            $('approve').disabled = false; $('reject').disabled = false;
            if (r.ok) {
                say((what === 'approve' ? 'Approved' : 'Sent back to draft') + '. ' + r.data.mail_sent + ' email(s) sent (no note in them).', false);
                loadEngines();
                openSection(c.engine, c.section);
            } else {
                say((what === 'approve' ? 'Not approved: ' : 'Not sent back: ') + problem(r) + (r.status === 409 ? ' Reload the section to see its latest state.' : ''), true);
            }
        }).catch(function (e) { $('approve').disabled = false; $('reject').disabled = false; say('Failed: ' + e.message, true); });
    }

    // ---- change bundles (PR 3b-2) --------------------------------------------------------------------------------------------------------------------
    var sectionBoxes = [];       // [{section, box}] kept as we build the checkboxes: never read back from the DOM (a real HTMLCollection has no forEach, and elements have tagName, not tag)
    var CHECK_NAMES = { no_email: 'no email address', no_not_yet_public: 'nothing marked not yet public', names_ok: 'no name beyond an owner\'s choice', schema_ok: 'files parse (schema)' };

    function bmsg(text, bad) { var el = $('bundleMsg'); el.textContent = text; el.className = bad ? 'error' : 'ok'; }

    function renderChecks(box, checks, problems) {
        clear(box);
        Object.keys(CHECK_NAMES).forEach(function (k) {
            var bad = checks && checks[k] === false;
            box.appendChild(h('div', { class: bad ? 'error' : 'ok', text: (bad ? 'FAILED: ' : 'passed: ') + CHECK_NAMES[k] + (bad && problems && problems[k] ? ' (' + problems[k].join('; ') + ')' : '') }));
        });
    }

    function saveText(text, name) {
        var url = window.URL.createObjectURL(new window.Blob([text], { type: 'application/json' }));
        var a = h('a', { href: url, download: name });
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    function downloadBundle(engine, id) {
        fetch(API + '/api/admin/onboarding/engines/' + encodeURIComponent(engine) + '/bundles/' + encodeURIComponent(id), { method: 'GET', headers: { 'X-Admin-API-Key': readKey() } })
            .then(function (res) {
                if (res.ok) { return res.text().then(function (t) { saveText(t, 'bundle-' + engine + '-' + id.slice(0, 8) + '.json'); bmsg('Downloaded. Give it to the agent to re-verify; do not edit it.', false); loadBundles(); }); }
                return res.json().catch(function () { return {}; }).then(function (d) { bmsg('Not downloaded: ' + problem({ status: res.status, data: d }), true); });
            }).catch(function (e) { bmsg('Not downloaded: ' + e.message, true); });
    }

    function bundleAction(engine, id, what, body) {
        call('POST', '/api/admin/onboarding/engines/' + encodeURIComponent(engine) + '/bundles/' + encodeURIComponent(id) + '/' + what, body).then(function (r) {
            bmsg(r.ok ? (what === 'merged' ? 'Marked merged; ' + r.data.mail_sent + ' owner(s) told (no content).' : 'Marked superseded. Create a new bundle.') : 'Failed: ' + problem(r), !r.ok);
            if (r.ok) { loadBundles(); }
        }).catch(function (e) { bmsg('Failed: ' + e.message, true); });
    }

    function renderBundles(engine, list) {
        var box = $('bundleList');
        clear(box);
        if (!list.length) { box.appendChild(h('p', { class: 'note', text: 'No bundles yet.' })); return; }
        list.forEach(function (b) {
            var kids = [h('strong', { text: b.status.toUpperCase() + ' · ' + b.created_at + ' · ' + b.sections.join(', ') + ' · base ' + (b.base_commit_sha ? b.base_commit_sha.slice(0, 12) : 'none (no repository)') })];
            var cbox = h('div', {});
            renderChecks(cbox, b.checks, b.problems);
            kids.push(cbox);
            var row = h('div', {});
            if (b.status === 'created' || b.status === 'exported') {
                var dl = h('button', { type: 'button', class: 'small', text: 'Download' });
                dl.addEventListener('click', function () { downloadBundle(engine, b.bundle_id); });
                var url = h('input', { type: 'text', maxlength: '200', placeholder: 'address of the merged pull request', autocomplete: 'off' });
                var mm = h('button', { type: 'button', class: 'small', text: 'Mark merged' });
                mm.addEventListener('click', function () { bundleAction(engine, b.bundle_id, 'merged', { pr_url: url.value.trim() }); });
                row.appendChild(dl); row.appendChild(url); row.appendChild(mm);
            }
            if (b.status !== 'merged' && b.status !== 'superseded') {
                var sp = h('button', { type: 'button', class: 'small', text: 'Main moved: supersede' });
                sp.addEventListener('click', function () { bundleAction(engine, b.bundle_id, 'supersede'); });
                row.appendChild(sp);
            }
            if (b.pr_url) { row.appendChild(h('span', { class: 'note', text: ' merged by ' + b.pr_url })); }
            kids.push(row);
            box.appendChild(h('div', { class: 'bundle' }, kids));
        });
    }

    function loadBundles() {
        var engine = $('bundleEngine').value.trim();
        if (!engine) { bmsg('Enter the engine id first.', true); return; }
        call('GET', '/api/admin/onboarding/engines/' + encodeURIComponent(engine)).then(function (e) {
            if (!e.ok) { bmsg('Could not load: ' + problem(e), true); return null; }
            var box = $('bundleSections');
            clear(box);
            var approved = e.data.sections.filter(function (s) { return s.status === 'approved'; });
            sectionBoxes = [];
            approved.forEach(function (s) {
                var cb = h('input', { type: 'checkbox', checked: 'checked', 'data-section': s.key });
                sectionBoxes.push({ section: s.key, box: cb });
                box.appendChild(h('label', { class: 'choice' }, [cb, ' ' + s.title + ' (approved revision ' + s.approved_revision + ')']));
            });
            if (!approved.length) { box.appendChild(h('p', { class: 'note', text: 'No section is approved yet.' })); }
            $('createBundle').disabled = !approved.length;
            return call('GET', '/api/admin/onboarding/engines/' + encodeURIComponent(engine) + '/bundles').then(function (b) {
                if (b.ok) { renderBundles(engine, b.data.bundles || []); } else { bmsg('Could not load bundles: ' + problem(b), true); }
            });
        }).catch(function (e) { bmsg('Could not load: ' + e.message, true); });
    }

    function createBundle() {
        var engine = $('bundleEngine').value.trim();
        var picked = sectionBoxes.filter(function (b) { return b.box.checked; }).map(function (b) { return b.section; });
        if (!picked.length) { bmsg('Choose at least one approved section.', true); return; }
        $('createBundle').disabled = true;
        call('POST', '/api/admin/onboarding/engines/' + encodeURIComponent(engine) + '/bundles', { sections: picked }).then(function (r) {
            $('createBundle').disabled = false;
            if (!r.ok) { bmsg('No bundle: ' + problem(r), true); return; }
            renderChecks($('bundleChecks'), r.data.checks, r.data.problems);
            var d = $('bundleDiff');
            clear(d);
            (r.data.preview || []).forEach(function (f) {
                d.appendChild(h('h4', { text: f.path + ' · ' + f.action + ' · +' + f.added + ' -' + f.removed }));
                var pre = h('div', { class: 'diff' });
                f.lines.forEach(function (l) { pre.appendChild(h('div', { class: l.t === '+' ? 'dadd' : l.t === '-' ? 'ddel' : l.t === '@' ? 'dhunk' : 'dctx', text: (l.t === '@' ? '' : l.t) + l.text })); });
                d.appendChild(pre);
            });
            (r.data.notes || []).forEach(function (n) { d.appendChild(h('p', { class: 'note', text: n })); });
            bmsg(r.data.status === 'blocked' ? 'The bundle is BLOCKED by a failed check above and cannot be downloaded as ready.' : 'Bundle created. It passed every check; download it below.', r.data.status === 'blocked');
            loadBundles();
        }).catch(function (e) { $('createBundle').disabled = false; bmsg('No bundle: ' + e.message, true); });
    }

    $('loadBundles').addEventListener('click', loadBundles);
    $('createBundle').addEventListener('click', createBundle);

    $('loadEngines').addEventListener('click', loadEngines);
    $('approve').addEventListener('click', function () { decide('approve'); });
    $('reject').addEventListener('click', function () { decide('reject'); });
    if (readKey()) { loadEngines(); }
}());
