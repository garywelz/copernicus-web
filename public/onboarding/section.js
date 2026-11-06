/* The section editor (design 5.8): one card per item, autosaved one item at a time with the revision it was based on. A stale save (409) shows the current answer and
   offers a one-click merge. Provenance and history, comments with "disagree" and resolve, question add and split, keyword entry add, and Mark final.
   Text from the server or a person reaches the page only through textContent (see common.js). Short polling, no websockets. */
(function () {
    'use strict';
    var OB = window.OB, $ = function (id) { return document.getElementById(id); }, h = OB.h;
    var DEBOUNCE_MS = 800, POLL_MS = 15000, LISTS = ['categories', 'horizons', 'mute', 'frontier', 'flagged'];
    var engine = OB.engineId(), key = OB.param('section');
    var base = '/api/onboarding/engines/' + engine;
    var cards = {}, queue = [], busy = false, ctx = { open: true, mayMark: false, section: null }, addersBuilt = false;

    function say(text, isError) { OB.say($('msg'), text, isError); }

    function fail(out) {
        $('items').hidden = true;
        if (out.status === 404 || out.status === 401) { $('signin').hidden = !OB.sessionToken(); }
        say(OB.problem(out), true);
    }

    function option(value, label, selected) {
        var o = h('option', { value: value, text: label });
        o.selected = !!selected;
        return o;
    }

    // ---- the header: status, banner, Mark final ----------------------------------------------------------------------------------------------------
    function renderHeader() {
        var s = ctx.section;
        $('title').textContent = s.title;
        $('state').textContent = 'Status: ' + s.status + ' · ' + s.answered + ' of ' + s.items + ' answered' + (s.disagreed ? ' · ' + s.disagreed + ' with an open disagreement' : '') + (s.ready ? ' · ready' : '');
        var banner = '';
        if (!ctx.open) { banner = 'This engine is not open, so answers can be read but not changed.'; }
        else if (s.status === 'final') { banner = 'This section is marked final. Editing any answer re-opens it and tells the final-say owner.'; }
        else if (s.status === 'approved') { banner = 'This section has been approved. Editing any answer starts a new draft and tells the final-say owner.'; }
        else if (s.status === 'rejected') { banner = 'This section was sent back. Revise it, and it becomes a draft again.'; }
        $('banner').hidden = !banner;
        $('banner').textContent = banner;
        $('finalRow').hidden = !(ctx.mayMark && s.status === 'draft');
        $('markFinal').disabled = !(s.ready && ctx.open);
        $('finalNote').textContent = s.ready ? '' : 'Not ready yet: ' + s.open + ' not answered, ' + s.disagreed + ' disagreement(s) open.';
    }

    // ---- pieces shared by the cards ------------------------------------------------------------------------------------------------------------------
    function contextBlock(it) {
        var c = it.context || {}, lines = [];
        if (c.original_wording) { lines.push('Original wording: ' + c.original_wording); }
        if (c.citation) { lines.push(c.citation); }
        if (c.identifier) { lines.push(String(c.identifier)); }
        if (c.added) { lines.push('Added by an owner.'); }
        if (c.split_from) { lines.push('Split from ' + c.split_from + '.'); }
        return lines.length ? h('div', { class: 'context', text: lines.join('\n') }) : null;
    }

    function touch(c) {
        c.version += 1;
        c.dirty = true;
        c.statusEl.textContent = 'Unsaved changes...';
        if (c.timer) { window.clearTimeout(c.timer); }
        if (!c.conflict) { c.timer = window.setTimeout(function () { enqueue(c); }, DEBOUNCE_MS); }
    }

    function radios(c, name, choices, current) {
        var group = h('div', {}), map = {};
        choices.forEach(function (ch) {
            var r = h('input', { type: 'radio', name: name, value: ch[0] });
            r.checked = current === ch[0];
            r.disabled = !ctx.open;
            r.addEventListener('change', function () { c.onChoice && c.onChoice(); touch(c); });
            map[ch[0]] = r;
            group.appendChild(h('label', { class: 'choice' }, [r, ' ' + ch[1]]));
        });
        return { el: group, value: function () { var k = Object.keys(map).filter(function (v) { return map[v].checked; })[0]; return k || null; } };
    }

    function textArea(c, initial, rows, max) {
        var ta = h('textarea', { rows: rows, maxlength: max });
        ta.value = initial || '';
        ta.disabled = !ctx.open;
        ta.addEventListener('input', function () { touch(c); });
        return ta;
    }

    function lineInput(c, initial, max) {
        var inp = h('input', { type: 'text', maxlength: max });
        inp.value = initial || '';
        inp.disabled = !ctx.open;
        inp.addEventListener('input', function () { touch(c); });
        return inp;
    }

    // ---- the editors, one per item type: each sets c.read() -> {value, choice} or null ---------------------------------------------------------------------
    function buildText(c, rows) {
        var ta = textArea(c, c.item.value, rows, 2000);
        c.body.appendChild(ta);
        c.read = function () { return { value: ta.value, choice: null }; };
    }

    function buildList(c) {
        var ta = textArea(c, (c.item.value || []).join('\n'), 6, 6200);
        c.body.appendChild(h('p', { class: 'note', text: 'One entry per line.' }));
        c.body.appendChild(ta);
        c.read = function () { return { value: OB.linesOf(ta.value), choice: null }; };
    }

    function buildQuestion(c) {
        var it = c.item, v = it.value || {}, orig = it.context || {};
        if (it.choice === 'split') {
            c.body.appendChild(h('p', { text: 'This question was split into: ' + ((v.split_into || []).join(', ') || 'new questions') + '. Edit those instead.' }));
            c.read = null;
            return;
        }
        var added = it.choice === 'add';
        var group = radios(c, 'choice_' + it.item_id, added ? [['add', 'Keep this question'], ['drop', 'Drop it']] : [['accept', 'Accept it as it is'], ['reword', 'Reword it'], ['drop', 'Drop it']], it.choice);
        var wording = textArea(c, v.wording || orig.original_wording || '', 3, 600);
        var wordingWrap = h('div', {}, [h('label', { text: 'Wording' }), wording]);
        var cent = h('select', {}, [option('central', 'Central to the engine', v.centrality !== 'background'), option('background', 'Background', v.centrality === 'background')]);
        cent.disabled = !ctx.open;
        cent.addEventListener('change', function () { touch(c); });
        var centWrap = h('div', {}, [h('label', { text: 'How central is it?' }), cent]);
        var reason = lineInput(c, v.reason, 500);
        var reasonWrap = h('div', {}, [h('label', { text: 'Why drop it?' }), reason]);
        var rows = [], termBox = h('div', { class: 'terms' }, [h('label', { text: 'Terms' })]);
        function addRow(t) {
            var inp = lineInput(c, t.text, 120), sel = h('select', {}, ['keep', 'reword', 'drop', 'add'].map(function (o) { return option(o, o, o === t.choice); }));
            sel.disabled = !ctx.open;
            sel.addEventListener('change', function () { touch(c); });
            rows.push({ inp: inp, sel: sel, original: t.original || '' });
            termBox.appendChild(h('div', { class: 'term' }, [inp, sel]));
        }
        (Array.isArray(v.terms) ? v.terms.map(function (t) { return { text: t.text, choice: t.choice, original: t.was || t.text }; })
            : (Array.isArray(orig.terms) ? orig.terms.map(function (t) { return { text: typeof t === 'string' ? t : t.text, choice: 'keep', original: typeof t === 'string' ? t : t.text }; }) : [])).forEach(addRow);
        var addTerm = h('button', { class: 'small', type: 'button', text: 'Add a term' });
        addTerm.disabled = !ctx.open;
        addTerm.addEventListener('click', function () { addRow({ text: '', choice: 'add', original: '' }); touch(c); });
        termBox.appendChild(addTerm);
        function show() {
            var ch = group.value();
            wordingWrap.hidden = !(ch === 'reword' || ch === 'add');
            reasonWrap.hidden = ch !== 'drop';
            centWrap.hidden = ch === 'drop';
            termBox.hidden = ch === 'drop';
        }
        c.onChoice = show;
        [group.el, wordingWrap, centWrap, reasonWrap, termBox].forEach(function (n) { c.body.appendChild(n); });
        show();
        c.read = function () {
            var ch = group.value();
            if (!ch) { return null; }
            var terms = rows.map(function (r) {
                var text = r.inp.value.trim(), t = { text: text, choice: r.sel.value };
                if (t.choice === 'reword' && r.original && r.original !== text) { t.was = r.original; }
                return text ? t : null;
            }).filter(function (t) { return t; });
            var val = { terms: terms };
            if (ch === 'drop') { val.reason = reason.value; } else { val.centrality = cent.value; }
            if (ch === 'reword' || ch === 'add') { val.wording = wording.value; }
            return { value: val, choice: ch };
        };
        if (!added && it.choice !== 'drop') { c.body.appendChild(splitBox(c)); }
    }

    function buildKeyword(c) {
        var it = c.item, v = it.value || {}, orig = it.context || {}, added = it.choice === 'add', list = v.list || orig.list || 'categories';
        c.body.appendChild(h('p', { class: 'note', text: 'List: ' + list }));
        var group = radios(c, 'choice_' + it.item_id, added ? [['add', 'Keep this entry'], ['drop', 'Drop it']] : [['keep', 'Keep it'], ['reword', 'Reword it'], ['drop', 'Drop it']], it.choice);
        var text = lineInput(c, v.text || orig.text || orig.original_text || '', 200);
        c.body.appendChild(group.el);
        c.body.appendChild(h('label', { text: 'Entry' }));
        c.body.appendChild(text);
        c.read = function () {
            var ch = group.value();
            return ch ? { value: { list: list, text: text.value }, choice: ch } : null;
        };
    }

    function buildSeed(c) {
        var it = c.item, v = it.value || {};
        var group = radios(c, 'choice_' + it.item_id, [['yes', 'Yes, this is a seed paper for the engine'], ['no', 'No'], ['unsure', 'Not sure']], it.choice);
        var comment = lineInput(c, v.comment, 1000);
        c.body.appendChild(group.el);
        c.body.appendChild(h('label', { text: 'Comment (optional)' }));
        c.body.appendChild(comment);
        c.read = function () {
            var ch = group.value();
            return ch ? { value: { comment: comment.value }, choice: ch } : null;
        };
    }

    var BUILDERS = {
        scope_statement: function (c) { buildText(c, 5); }, use_case: function (c) { buildText(c, 5); }, out_of_scope: buildList,
        question: buildQuestion, keyword_entry: buildKeyword, seed_confirm: buildSeed
    };

    // ---- splitting a question ---------------------------------------------------------------------------------------------------------------------------
    function splitBox(c) {
        var wrap = h('div', {}), parts = [];
        var open = h('button', { class: 'small', type: 'button', text: 'Split this question...' });
        open.disabled = !ctx.open;
        var form = h('div', { hidden: true });
        function addPart() {
            if (parts.length >= 5) { return; }
            var ta = h('textarea', { rows: 2, maxlength: 600 }), cent = h('select', {}, [option('central', 'Central', true), option('background', 'Background', false)]);
            parts.push({ ta: ta, cent: cent });
            form.insertBefore(h('div', {}, [h('label', { text: 'Part ' + parts.length }), ta, cent]), more);
        }
        var more = h('button', { class: 'small', type: 'button', text: 'Add another part' });
        var go = h('button', { class: 'small primary', type: 'button', text: 'Split it' });
        var out = h('span', { class: 'note' });
        form.appendChild(more);
        form.appendChild(go);
        form.appendChild(out);
        wrap.appendChild(open);
        wrap.appendChild(form);
        open.addEventListener('click', function () { form.hidden = !form.hidden; if (!parts.length) { addPart(); addPart(); } });
        more.addEventListener('click', addPart);
        go.addEventListener('click', function () {
            var questions = parts.map(function (p) { return { wording: p.ta.value, centrality: p.cent.value }; });
            go.disabled = true;
            OB.call('POST', base + '/questions', { action: 'split', from_item: c.item.item_id, questions: questions }).then(function (r) {
                go.disabled = false;
                if (r.ok) { say('The question was split. The new questions are below.', false); load(); } else { out.textContent = OB.problem(r); }
            }).catch(function () { go.disabled = false; out.textContent = 'Network error. Please try again.'; });
        });
        return wrap;
    }

    // ---- saving: debounced, one item at a time, with the revision the owner was looking at ---------------------------------------------------------------
    function enqueue(c) {
        if (queue.indexOf(c) === -1) { queue.push(c); }
        pump();
    }

    function pump() {
        if (busy) { return; }
        var c = queue.shift();
        if (!c) { return; }
        busy = true;
        save(c).then(function () { busy = false; pump(); });
    }

    function save(c) {
        if (c.conflict || !c.read) { return Promise.resolve(); }
        var payload = c.read();
        if (!payload) { c.statusEl.textContent = 'Choose an option to save this answer.'; return Promise.resolve(); }
        var sentVersion = c.version;
        c.saving = true;
        c.statusEl.textContent = 'Saving...';
        return OB.call('PUT', base + '/items/' + encodeURIComponent(c.item.item_id), { value: payload.value, choice: payload.choice, base_revision: c.rev }).then(function (out) {
            c.saving = false;
            if (out.ok) {
                c.rev = out.data.item.revision;
                c.item = out.data.item;
                updateMeta(c, out.data.item);
                updateComments(c, out.data.item);
                if (c.version === sentVersion) { c.dirty = false; c.statusEl.textContent = 'Saved'; } else { enqueue(c); }
                load();
                return;
            }
            var d = out.data && out.data.detail;
            if (out.status === 409 && d && d.stale) { return showConflict(c, payload, d.current); }
            c.statusEl.textContent = 'Not saved: ' + OB.problem(out);
        }).catch(function () {
            c.saving = false;
            c.statusEl.textContent = 'Network error. Trying again shortly.';
            window.setTimeout(function () { enqueue(c); }, 5000);
        });
    }

    function showConflict(c, mine, theirs) {
        c.conflict = true;
        var box = c.conflictEl, mergeable = ['scope_statement', 'use_case', 'out_of_scope'].indexOf(c.item.type) !== -1;
        OB.clear(box);
        box.hidden = false;
        box.appendChild(h('strong', { text: 'Someone changed this answer while you were editing it.' }));
        box.appendChild(h('div', { class: 'note', text: 'Their version (' + (theirs.author || 'other owner') + ', ' + OB.when(theirs.updated_at) + '):' }));
        box.appendChild(h('pre', { text: OB.describe(theirs) }));
        box.appendChild(h('div', { class: 'note', text: 'Your version:' }));
        box.appendChild(h('pre', { text: OB.describe({ value: mine.value, choice: mine.choice }) }));
        function settle(item, dirty) {
            c.conflict = false;
            box.hidden = true;
            OB.clear(box);
            rebuild(c, item, dirty);
        }
        var useTheirs = h('button', { type: 'button', text: 'Use theirs' }), keepMine = h('button', { type: 'button', text: 'Keep mine' });
        useTheirs.addEventListener('click', function () { settle(theirs, false); });
        keepMine.addEventListener('click', function () { settle(Object.assign({}, theirs, { value: mine.value, choice: mine.choice }), true); });
        box.appendChild(useTheirs);
        box.appendChild(keepMine);
        if (mergeable) {
            var both = h('button', { class: 'primary', type: 'button', text: 'Merge both' });
            both.addEventListener('click', function () {
                var merged = Array.isArray(theirs.value) ? OB.mergeLists(theirs.value, mine.value) : OB.mergeText(theirs.value, mine.value);
                settle(Object.assign({}, theirs, { value: merged }), true);
            });
            box.appendChild(both);
        }
        c.statusEl.textContent = 'Not saved: it needs your decision above.';
    }

    // ---- provenance, history, comments (updated on every refresh, even while a card has unsaved edits) ---------------------------------------------------
    function updateMeta(c, it) {
        var sig = JSON.stringify([it.author, it.updated_at, it.revision, (it.history || []).length]);
        if (c.metaSig === sig) { return; }
        c.metaSig = sig;
        OB.clear(c.metaEl);
        c.metaEl.appendChild(h('div', { class: 'note', text: it.author ? 'Last changed by ' + it.author + ' on ' + OB.when(it.updated_at) + ' (revision ' + it.revision + ')' : 'Not answered yet' }));
        if ((it.history || []).length) {
            var list = h('ul', { class: 'hist' });
            it.history.slice().reverse().forEach(function (e) {
                list.appendChild(h('li', { text: 'Revision ' + e.revision + ' by ' + e.author + ', ' + OB.when(e.at) + ':\n' + OB.describe(e) }));
            });
            c.metaEl.appendChild(h('details', {}, [h('summary', { text: 'History (' + it.history.length + ' earlier version' + (it.history.length === 1 ? '' : 's') + ')' }), list]));
        }
    }

    function updateComments(c, it) {
        var sig = JSON.stringify(it.comments || []);
        c.el.className = 'card' + (it.disagreed ? ' disagreed' : '');
        if (c.commentSig === sig) { return; }
        c.commentSig = sig;
        OB.clear(c.commentsEl);
        (it.comments || []).forEach(function (cm) {
            var line = (cm.kind === 'disagree' ? 'Disagrees' : 'Comment') + ' · ' + cm.author + ' · ' + OB.when(cm.created_at) + (cm.resolved ? ' · resolved by ' + cm.resolved_by : '');
            var node = h('div', { class: 'comment' + (cm.kind === 'disagree' ? ' disagree' : '') + (cm.resolved ? ' resolved' : '') }, [h('div', { class: 'by', text: line }), h('div', { text: cm.body })]);
            if (!cm.resolved) {
                var b = h('button', { class: 'small', type: 'button', text: 'Resolve' });
                b.addEventListener('click', function () {
                    b.disabled = true;
                    OB.call('POST', base + '/comments/' + encodeURIComponent(cm.comment_id) + '/resolve').then(function (r) { if (!r.ok) { say(OB.problem(r), true); } load(); })
                        .catch(function () { b.disabled = false; say('Network error. Please try again.', true); });
                });
                node.appendChild(b);
            }
            c.commentsEl.appendChild(node);
        });
    }

    function commentForm(c) {
        var ta = h('textarea', { rows: 2, maxlength: 4000 }), dis = h('input', { type: 'checkbox' }), post = h('button', { class: 'small', type: 'button', text: 'Add comment' });
        var out = h('span', { class: 'note' });
        post.addEventListener('click', function () {
            if (!ta.value.trim()) { return; }
            post.disabled = true;
            OB.call('POST', base + '/items/' + encodeURIComponent(c.item.item_id) + '/comments', { body: ta.value, kind: dis.checked ? 'disagree' : 'comment' }).then(function (r) {
                post.disabled = false;
                if (r.ok) { ta.value = ''; dis.checked = false; out.textContent = ''; load(); } else { out.textContent = OB.problem(r); }
            }).catch(function () { post.disabled = false; out.textContent = 'Network error. Please try again.'; });
        });
        return h('div', {}, [h('label', { text: 'Comment' }), ta, h('label', { class: 'choice' }, [dis, ' I disagree with this answer (it blocks marking the section final until someone resolves it)']), post, out]);
    }

    // ---- cards --------------------------------------------------------------------------------------------------------------------------------------------
    function buildBody(c) {
        OB.clear(c.body);
        c.read = null;
        c.onChoice = null;
        var ctxBlock = contextBlock(c.item);
        if (ctxBlock) { c.body.appendChild(ctxBlock); }
        (BUILDERS[c.item.type] || function (cc) { cc.body.appendChild(h('p', { text: 'This kind of item cannot be edited here.' })); })(c);
    }

    function rebuild(c, item, dirty) {
        c.item = item;
        c.rev = item.revision;
        c.dirty = false;
        buildBody(c);
        if (dirty) { touch(c); if (c.timer) { window.clearTimeout(c.timer); } enqueue(c); }
    }

    function newCard(it) {
        var c = { item: it, rev: it.revision, dirty: false, saving: false, conflict: false, version: 0, timer: null, read: null, onChoice: null, metaSig: '', commentSig: '' };
        c.body = h('div', {});
        c.statusEl = h('div', { class: 'status' });
        c.conflictEl = h('div', { class: 'conflict', hidden: true });
        c.metaEl = h('div', {});
        c.commentsEl = h('div', { class: 'comments' });
        c.el = h('div', { class: 'card' }, [h('div', { class: 'head' }, [h('strong', { text: it.item_id })]), c.body, c.statusEl, c.conflictEl, c.metaEl, c.commentsEl, commentForm(c)]);
        buildBody(c);
        updateMeta(c, it);
        updateComments(c, it);
        return c;
    }

    function reconcile(items) {
        items.forEach(function (it) {
            var c = cards[it.item_id];
            if (!c) { c = cards[it.item_id] = newCard(it); $('items').appendChild(c.el); return; }
            updateMeta(c, it);
            updateComments(c, it);
            var editing = c.el.contains(document.activeElement);
            if (!c.dirty && !c.saving && !c.conflict && !editing && it.revision !== c.rev) { rebuild(c, it, false); c.statusEl.textContent = ''; }
            else if (it.revision !== c.rev && c.dirty && !c.conflict) { c.statusEl.textContent = 'Another owner changed this answer. Your next save will ask what to keep.'; }
        });
    }

    // ---- adding a question or an entry ------------------------------------------------------------------------------------------------------------------
    function buildAdders() {
        if (addersBuilt || !ctx.section) { return; }
        addersBuilt = true;
        var box = $('adders');
        if (key === 'questions') {
            var w = h('textarea', { rows: 2, maxlength: 600 }), cent = h('select', {}, [option('central', 'Central', true), option('background', 'Background', false)]);
            var go = h('button', { type: 'button', text: 'Add this question' }), out = h('span', { class: 'note' });
            go.addEventListener('click', function () {
                go.disabled = true;
                OB.call('POST', base + '/questions', { action: 'add', questions: [{ wording: w.value, centrality: cent.value }] }).then(function (r) {
                    go.disabled = false;
                    if (r.ok) { w.value = ''; out.textContent = 'Added.'; load(); } else { out.textContent = OB.problem(r); }
                }).catch(function () { go.disabled = false; out.textContent = 'Network error. Please try again.'; });
            });
            box.appendChild(h('details', {}, [h('summary', { text: 'Add a question' }), h('label', { text: 'Wording' }), w, cent, go, out]));
        }
        if (key === 'keywords') {
            var sel = h('select', {}, LISTS.map(function (l) { return option(l, l, l === 'horizons'); })), t = h('input', { type: 'text', maxlength: 200 });
            var add = h('button', { type: 'button', text: 'Add this entry' }), res = h('span', { class: 'note' });
            add.addEventListener('click', function () {
                add.disabled = true;
                OB.call('POST', base + '/entries', { list: sel.value, text: t.value }).then(function (r) {
                    add.disabled = false;
                    if (r.ok) { t.value = ''; res.textContent = 'Added.'; load(); } else { res.textContent = OB.problem(r); }
                }).catch(function () { add.disabled = false; res.textContent = 'Network error. Please try again.'; });
            });
            box.appendChild(h('details', {}, [h('summary', { text: 'Add a keyword, horizon or mute entry' }), h('label', { text: 'List' }), sel, h('label', { text: 'Entry' }), t, add, res]));
        }
    }

    // ---- loading, marking final, starting ---------------------------------------------------------------------------------------------------------------
    function load() {
        return Promise.all([OB.call('GET', base), OB.call('GET', base + '/sections/' + encodeURIComponent(key))]).then(function (r) {
            if (!r[0].ok) { return fail(r[0]); }
            if (!r[1].ok) { return fail(r[1]); }
            ctx.open = r[0].data.state === 'open';
            ctx.mayMark = !!(r[0].data.may_mark && r[0].data.may_mark.indexOf(key) !== -1);
            ctx.section = r[1].data.section;
            $('back').setAttribute('href', 'engine.html?engine=' + encodeURIComponent(engine));
            renderHeader();
            buildAdders();
            reconcile(r[1].data.items);
        }).catch(function () { say('Network error. Retrying shortly.', true); });
    }

    function markFinal() {
        var b = $('markFinal');
        b.disabled = true;
        OB.call('POST', base + '/sections/' + encodeURIComponent(key) + '/final').then(function (out) {
            say(out.ok ? 'This section is now marked final. Gary will review it.' : OB.problem(out), !out.ok);
            load();
        }).catch(function () { b.disabled = false; say('Network error. Please try again.', true); });
    }

    function start() {
        if (!engine || OB.SECTION_KEYS.indexOf(key) === -1) { return say('This page needs the link from the engine page, which names the engine and the section.', true); }
        if (!OB.sessionToken()) { $('signin').hidden = false; return; }
        $('markFinal').addEventListener('click', markFinal);
        load();
        OB.poll(load, POLL_MS);
    }
    start();
}());
