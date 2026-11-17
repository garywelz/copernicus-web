/* The review of the hold list (design 2.5, 5.8; PR 4b-2b): one card per paper, with its decision (keep, drop or unsure), a comment, the flags from the hold list,
   and the abstract with the registry it came from. A paper whose identifier may point at a different paper (title_mismatch) shows the registry's own title
   beside the abstract and a plain warning. Filters by group, likely keep and unresolved; bulk marking of the papers shown, all or nothing, through
   POST .../review/bulk. One decision is saved like any answer, with the revision it was based on; a stale save is refused and shown, never merged silently.
   Abstracts, titles and every other piece of registry text reach the page only through textContent (see common.js). Short polling, no websockets. */
(function (root) {
    'use strict';
    var CHOICES = ['keep', 'drop', 'unsure'], CHOICE_WORDS = { keep: 'Keep', drop: 'Drop', unsure: 'Unsure' };
    var COMMENT_CAP = 1000, BULK_MAX = 100, DEBOUNCE_MS = 800, POLL_MS = 20000;
    var REGISTRY = { crossref: 'Crossref', openalex: 'OpenAlex', arxiv: 'arXiv', s2: 'Semantic Scholar' };
    var STATE_WORDS = {
        found: 'Abstract found.', no_abstract: 'The registry has this paper but gave no abstract.', title_mismatch: 'The registry\'s record may be a different paper.',
        not_found: 'Not found in the registries when last looked up. This does not mean the paper does not exist.',
        unavailable: 'The registries could not be reached when last looked up.'
    };

    // ---- pure helpers (tested in Node) ---------------------------------------------------------------------------------------------------------------
    function matches(p, f) {
        if (f.group && p.group !== f.group) { return false; }
        if (f.likely && !p.likely_keep) { return false; }
        if (f.unresolved && !p.unresolved) { return false; }
        return true;
    }

    function visible(papers, f) { return (papers || []).filter(function (p) { return matches(p, f || {}); }); }

    // The body of POST .../review/bulk for these papers: each with the revision the page last saw.
    function bulkBody(choice, papers, revs) {
        return { choice: choice, papers: papers.map(function (p) { return { item_id: p.item_id, base_revision: revs && p.item_id in revs ? revs[p.item_id] : p.revision }; }) };
    }

    function stateLine(p) {
        if (!p.lookup_state) { return 'Not looked up yet.'; }
        return STATE_WORDS[p.lookup_state] || '';
    }

    function abstractSource(p) {
        return p.abstract_source ? 'Abstract from ' + (REGISTRY[p.abstract_source] || p.abstract_source) : 'Abstract';
    }

    var pure = { matches: matches, visible: visible, bulkBody: bulkBody, stateLine: stateLine, abstractSource: abstractSource, CHOICES: CHOICES, COMMENT_CAP: COMMENT_CAP,
                 BULK_MAX: BULK_MAX };
    if (typeof module !== 'undefined' && module.exports) { module.exports = pure; }
    if (!root || !root.document || !root.OB) { return; }

    // ---- the page --------------------------------------------------------------------------------------------------------------------------------------
    var OB = root.OB, document = root.document, $ = function (id) { return document.getElementById(id); }, h = OB.h;
    var engine = OB.engineId(), base = '/api/onboarding/engines/' + engine, SECTION = 'review';
    var cards = {}, order = [], queue = [], busy = false, ctx = { open: true, owner: false, mayMark: false, section: null, papers: [], groups: [] };

    function say(text, isError) { OB.say($('msg'), text, isError); }

    function fail(out) {
        $('review').hidden = true;
        if (out.status === 404 || out.status === 401) { $('signin').hidden = !OB.sessionToken(); }
        say(out.status === 404 && OB.sessionToken() ? 'This engine has no hold list to review, or you are not signed in with the account that was invited.' : OB.problem(out), true);
    }

    function filters() { return { group: $('fGroup').value, likely: $('fLikely').checked, unresolved: $('fUnresolved').checked }; }

    function editable() { return ctx.open && ctx.owner; }

    // ---- the header ----------------------------------------------------------------------------------------------------------------------------------
    function renderHeader() {
        var s = ctx.section;
        $('title').textContent = s.title;
        $('state').textContent = 'Status: ' + s.status + ' · ' + s.answered + ' of ' + s.items + ' decided' + (s.disagreed ? ' · ' + s.disagreed + ' with an open disagreement' : '') + (s.ready ? ' · ready' : '');
        var banner = '';
        if (!ctx.open) { banner = 'This engine is not open, so decisions can be read but not changed.'; }
        else if (!ctx.owner) { banner = 'You can read this review but not change it.'; }
        else if (s.status === 'final') { banner = 'This section is marked final. Changing any decision re-opens it and tells the final-say owner.'; }
        else if (s.status === 'approved') { banner = 'This section has been approved. Changing any decision starts a new draft and tells the final-say owner.'; }
        $('banner').hidden = !banner;
        $('banner').textContent = banner;
        $('sentBack').hidden = !s.rejection_note;
        $('sentBackNote').textContent = s.rejection_note || '';
        $('approval').hidden = s.status !== 'approved';
        $('approvalLine').textContent = s.status === 'approved' ? 'Approved' + (s.approved_at ? ' ' + OB.when(s.approved_at) : '') + (s.approved_revision ? ' (revision ' + s.approved_revision + ')' : '') : '';
        $('approvalNote').textContent = s.status === 'approved' && s.approver_note ? s.approver_note : '';
        $('finalRow').hidden = !(ctx.mayMark && s.status === 'draft');
        $('markFinal').disabled = !(s.ready && ctx.open);
        $('finalNote').textContent = s.ready ? '' : 'Not ready yet: ' + s.open + ' paper(s) without a decision, ' + s.disagreed + ' disagreement(s) open.';
    }

    function renderCounts(c) {
        $('counts').textContent = c.papers + ' papers: ' + c.keep + ' keep, ' + c.drop + ' drop, ' + c.unsure + ' unsure, ' + c.unanswered + ' not decided yet. ' +
            c.likely_keep + ' flagged as likely keep; ' + c.unresolved + ' unresolved.';
    }

    function renderGroups(groups) {
        var sel = $('fGroup'), keep = sel.value;
        if (sel.children.length === groups.length + 1 && groups.every(function (g, i) { return sel.children[i + 1].textContent === g; })) { return; }
        OB.clear(sel);
        sel.appendChild(h('option', { value: '', text: 'All groups' }));
        groups.forEach(function (g) { var o = h('option', { value: g, text: g }); o.selected = g === keep; sel.appendChild(o); });
        if (keep && groups.indexOf(keep) !== -1) { sel.value = keep; }
    }

    // ---- one card per paper ----------------------------------------------------------------------------------------------------------------------------
    function meta(p) {
        var bits = [p.identifier ? String(p.identifier) : '', p.group ? 'Group: ' + p.group : '', p.reason ? 'Reason held: ' + p.reason : '',
                    typeof p.cited_by === 'number' ? 'Cited by ' + p.cited_by + ' of the engine\'s papers' : ''];
        return bits.filter(function (b) { return b; }).join(' · ');
    }

    function fillPaperText(c) {
        var p = c.paper, box = c.textEl;
        OB.clear(box);
        box.appendChild(h('div', { class: 'note', text: meta(p) }));
        if (p.likely_keep) { box.appendChild(h('div', { class: 'likely', text: 'Flagged by a reviewer as likely keep' })); }
        if (p.warning) {
            box.appendChild(h('div', { class: 'conflict' }, [h('strong', { text: p.warning }),
                h('div', { class: 'note', text: 'Title in the hold list: ' + (p.title || '') }),
                h('div', { class: 'note', text: 'Title the registry gives for this identifier: ' + ((p.registry && p.registry.title) || 'none') })]));
        }
        if (p.registry && !p.warning && (p.registry.authors && p.registry.authors.length || p.registry.year)) {
            box.appendChild(h('div', { class: 'note', text: ((p.registry.authors || []).join(', ') || 'Authors not given') + (p.registry.year ? ' (' + p.registry.year + ')' : '') }));
        }
        if (p.abstract) {
            box.appendChild(h('div', { class: 'note', text: abstractSource(p) + (p.abstract_fetched_at ? ', ' + OB.when(p.abstract_fetched_at) : '') + ':' }));
            box.appendChild(h('div', { class: 'context', text: p.abstract }));
        } else {
            box.appendChild(h('div', { class: 'note', text: 'No abstract. ' + stateLine(p) }));
        }
        if (p.unresolved && p.abstract && !p.warning) { box.appendChild(h('div', { class: 'note', text: stateLine(p) })); }
    }

    function setChoice(c, choice) {
        c.radios.forEach(function (r) { r.checked = r.getAttribute('value') === choice; });
    }

    function current(c) {
        var chosen = c.radios.filter(function (r) { return r.checked; })[0];
        return { choice: chosen ? chosen.getAttribute('value') : null, comment: c.comment.value };
    }

    function updateMeta(c) {
        var p = c.paper;
        c.byEl.textContent = p.answered ? 'Decided: ' + (CHOICE_WORDS[p.choice] || p.choice) + (p.author ? ' by ' + p.author : '') + (p.updated_at ? ', ' + OB.when(p.updated_at) : '') +
            (p.comment_count ? ' · ' + p.comment_count + ' comment(s) on the section page thread' : '') : 'Not decided yet';
        c.el.className = 'card' + (p.disagreed ? ' disagreed' : '');
    }

    function makeCard(p) {
        var c = { paper: p, rev: p.revision, dirty: false, saving: false, version: 0, timer: null };
        c.textEl = h('div', {});
        c.byEl = h('div', { class: 'note' });
        c.statusEl = h('div', { class: 'status' });
        c.conflictEl = h('div', { class: 'conflict', hidden: true });
        c.radios = CHOICES.map(function (ch) { return h('input', { type: 'radio', name: 'd_' + p.item_id, value: ch }); });
        c.comment = h('textarea', { rows: 2, maxlength: COMMENT_CAP, placeholder: 'A comment for the other owner and the reviewer (not published)' });
        var choices = h('div', {}, c.radios.map(function (r, i) { return h('label', { class: 'choice' }, [r, ' ' + CHOICE_WORDS[CHOICES[i]]]); }));
        c.el = h('div', { class: 'card' }, [h('div', { class: 'head' }, [h('strong', { text: p.title || p.item_id }), c.byEl]), c.textEl, choices,
                                          h('label', { text: 'Comment' }), c.comment, c.statusEl, c.conflictEl]);
        c.radios.forEach(function (r) { r.addEventListener('change', function () { touched(c, true); }); });
        c.comment.addEventListener('input', function () { touched(c, false); });
        show(c, p);
        return c;
    }

    function show(c, p) {
        c.paper = p;
        c.rev = p.revision;
        fillPaperText(c);
        setChoice(c, p.choice);
        c.comment.value = p.comment || '';
        updateMeta(c);
        var ro = !editable();
        c.radios.forEach(function (r) { r.disabled = ro; });
        c.comment.disabled = ro;
    }

    function touched(c, now) {
        c.dirty = true;
        c.version += 1;
        if (c.timer) { root.clearTimeout(c.timer); }
        if (now) { enqueue(c); } else { c.statusEl.textContent = 'Not saved yet'; c.timer = root.setTimeout(function () { c.timer = null; enqueue(c); }, DEBOUNCE_MS); }
    }

    function enqueue(c) {
        if (queue.indexOf(c) === -1) { queue.push(c); }
        pump();
    }

    function pump() {
        if (busy || !queue.length) { return; }
        busy = true;
        var c = queue.shift();
        save(c).then(function () { busy = false; pump(); });
    }

    function save(c) {
        if (c.conflict) { return Promise.resolve(); }
        var mine = current(c);
        if (!mine.choice) { c.statusEl.textContent = 'Choose keep, drop or unsure to save this paper.'; return Promise.resolve(); }
        var sentVersion = c.version;
        c.saving = true;
        c.statusEl.textContent = 'Saving...';
        return OB.call('PUT', base + '/items/' + encodeURIComponent(c.paper.item_id), { value: { comment: mine.comment }, choice: mine.choice, base_revision: c.rev }).then(function (out) {
            c.saving = false;
            if (out.ok) {
                var it = out.data.item;
                c.rev = it.revision;
                c.paper = Object.assign({}, c.paper, { choice: it.choice, comment: (it.value || {}).comment || '', revision: it.revision, answered: it.answered, author: it.author,
                                                       updated_at: it.updated_at });
                updateMeta(c);
                if (c.version === sentVersion) { c.dirty = false; c.statusEl.textContent = 'Saved'; } else { enqueue(c); }
                load();
                return;
            }
            var d = out.data && out.data.detail;
            if (out.status === 409 && d && d.stale) { return showConflict(c, mine, d.current); }
            c.statusEl.textContent = 'Not saved: ' + OB.problem(out);
        }).catch(function () {
            c.saving = false;
            c.statusEl.textContent = 'Network error. Trying again shortly.';
            root.setTimeout(function () { enqueue(c); }, 5000);
        });
    }

    // A stale save: the other owner changed this paper first. Nothing was written. Both versions are shown and the owner chooses; nothing is merged for them.
    function showConflict(c, mine, theirs) {
        c.conflict = true;
        var box = c.conflictEl, theirComment = (theirs.value || {}).comment || '';
        OB.clear(box);
        box.hidden = false;
        box.appendChild(h('strong', { text: 'Someone changed this paper while you were deciding it. Your change was not saved.' }));
        box.appendChild(h('div', { class: 'note', text: 'Their decision (' + (theirs.author || 'other owner') + ', ' + OB.when(theirs.updated_at) + '): ' + (CHOICE_WORDS[theirs.choice] || 'none') +
                                                       (theirComment ? '. Comment: ' + theirComment : '') }));
        box.appendChild(h('div', { class: 'note', text: 'Yours: ' + (CHOICE_WORDS[mine.choice] || 'none') + (mine.comment ? '. Comment: ' + mine.comment : '') }));
        var useTheirs = h('button', { type: 'button', text: 'Use theirs' }), keepMine = h('button', { type: 'button', text: 'Keep mine' });
        function settle(keep) {
            c.conflict = false;
            box.hidden = true;
            OB.clear(box);
            var p = Object.assign({}, c.paper, { choice: theirs.choice, comment: theirComment, revision: theirs.revision, answered: theirs.answered, author: theirs.author,
                                                 updated_at: theirs.updated_at });
            show(c, p);
            c.dirty = false;
            c.statusEl.textContent = '';
            if (keep) { setChoice(c, mine.choice); c.comment.value = mine.comment; touched(c, true); }
        }
        useTheirs.addEventListener('click', function () { settle(false); });
        keepMine.addEventListener('click', function () { settle(true); });
        box.appendChild(h('div', {}, [useTheirs, keepMine]));
        c.statusEl.textContent = 'Not saved: changed by someone else';
    }

    // ---- the list, the filters and polling ------------------------------------------------------------------------------------------------------------
    function reconcile(papers) {
        var list = $('papers');
        papers.forEach(function (p) {
            var c = cards[p.item_id];
            if (!c) { cards[p.item_id] = makeCard(p); order.push(p.item_id); return; }
            if (c.dirty || c.saving || c.conflict || c.comment === document.activeElement) { return; }     // never overwrite what is being typed or saved
            if (p.revision < c.rev) { return; }                                  // an answer older than the one this card holds: never move backwards
            if (p.revision !== c.rev || p.lookup_state !== c.paper.lookup_state || p.abstract !== c.paper.abstract) { show(c, p); }
            else { c.paper = p; updateMeta(c); }
            var ro = !editable();
            c.radios.forEach(function (r) { r.disabled = ro; });
            c.comment.disabled = ro;
        });
        applyFilters(list);
    }

    function applyFilters() {
        var list = $('papers'), f = filters(), shown = visible(ctx.papers, f), ids = {};
        shown.forEach(function (p) { ids[p.item_id] = true; });
        OB.clear(list);
        order.forEach(function (id) { if (ids[id] && cards[id]) { list.appendChild(cards[id].el); } });
        $('shown').textContent = 'Showing ' + shown.length + ' of ' + ctx.papers.length + ' papers.';
        if (!shown.length) { list.appendChild(h('p', { class: 'note', text: 'No paper matches these filters.' })); }
        $('bulkBox').hidden = !editable();
        $('bulkApply').disabled = !shown.length || !editable();
        $('bulkApply').textContent = 'Mark the ' + shown.length + ' paper' + (shown.length === 1 ? '' : 's') + ' shown';
    }

    function load() {
        return Promise.all([OB.call('GET', base), OB.call('GET', base + '/review')]).then(function (r) {
            if (!r[0].ok) { return fail(r[0]); }
            if (!r[1].ok) { return fail(r[1]); }
            ctx.open = r[0].data.state === 'open';
            ctx.owner = r[0].data.role === 'owner';
            ctx.mayMark = !!(r[0].data.may_mark && r[0].data.may_mark.indexOf(SECTION) !== -1);
            ctx.section = r[1].data.section;
            ctx.papers = r[1].data.papers || [];
            $('back').setAttribute('href', 'engine.html?engine=' + encodeURIComponent(engine));
            $('review').hidden = false;
            $('signin').hidden = true;
            renderHeader();
            renderCounts(r[1].data.counts);
            renderGroups(r[1].data.groups || []);
            reconcile(ctx.papers);
        }).catch(function () { say('Network error. Retrying shortly.', true); });
    }

    // ---- bulk marking ----------------------------------------------------------------------------------------------------------------------------------
    function bulk() {
        var res = $('bulkResult'), choice = $('bulkChoice').value, shown = visible(ctx.papers, filters());
        OB.clear(res);
        if (!shown.length) { return OB.say(res, 'No paper is shown, so nothing was marked.', true); }
        if (shown.length > BULK_MAX) { return OB.say(res, shown.length + ' papers are shown. Narrow the filters to ' + BULK_MAX + ' or fewer, then try again. Nothing was marked.', true); }
        var busyCards = shown.filter(function (p) { var c = cards[p.item_id]; return c && (c.dirty || c.saving || c.conflict); });
        if (busyCards.length) { return OB.say(res, 'Some of these papers have an unsaved change. Wait for it to save, then try again. Nothing was marked.', true); }
        if (!root.confirm('Mark all ' + shown.length + ' papers shown as "' + CHOICE_WORDS[choice] + '"? Their comments are kept.')) { return; }
        var revs = {};
        shown.forEach(function (p) { if (cards[p.item_id]) { revs[p.item_id] = cards[p.item_id].rev; } });
        $('bulkApply').disabled = true;
        OB.say(res, 'Working...', false);
        OB.call('POST', base + '/review/bulk', bulkBody(choice, shown, revs)).then(function (out) {
            OB.clear(res);
            if (out.ok) {
                var n = out.data.marked.length, same = out.data.unchanged.length;
                OB.say(res, 'Marked ' + n + ' paper' + (n === 1 ? '' : 's') + ' "' + CHOICE_WORDS[choice] + '".' + (same ? ' ' + same + ' already had that decision and were left as they were.' : ''), false);
                return load();
            }
            var d = out.data && out.data.detail;
            if (out.status === 409 && d && d.reason === 'stale') {
                res.className = 'error';
                res.appendChild(h('p', { text: d.message }));
                res.appendChild(h('p', { text: 'Changed by someone else since you opened the page:' }));
                res.appendChild(h('ul', {}, (d.stale || []).map(function (s) { return h('li', { text: s.title || s.item_id }); })));
                return load();
            }
            OB.say(res, OB.problem(out) + ' Nothing was marked.', true);
            applyFilters();
        }).catch(function () { OB.say(res, 'Network error. Nothing is known to have been marked; the page will reload the list.', true); load(); });
    }

    function markFinal() {
        var b = $('markFinal');
        b.disabled = true;
        OB.call('POST', base + '/sections/' + SECTION + '/final').then(function (out) {
            say(out.ok ? 'This section is now marked final. Gary will review it.' : OB.problem(out), !out.ok);
            load();
        }).catch(function () { b.disabled = false; say('Network error. Please try again.', true); });
    }

    function start() {
        if (!engine) { return say('This page needs the link from the engine page, which names the engine.', true); }
        if (!OB.sessionToken()) { $('signin').hidden = false; return; }
        CHOICES.forEach(function (ch) { $('bulkChoice').appendChild(h('option', { value: ch, text: CHOICE_WORDS[ch] })); });
        ['fGroup', 'fLikely', 'fUnresolved'].forEach(function (id) { $(id).addEventListener('change', applyFilters); });
        $('bulkApply').addEventListener('click', bulk);
        $('markFinal').addEventListener('click', markFinal);
        load();
        OB.poll(load, POLL_MS);
    }
    start();
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this)));
