/* The engine page (design 5.8): the progress tracker, the section list, Mark all ready, delegation, and the owner's own notification switch.
   Text from the server or a person reaches the page only through textContent (see common.js). Short polling, no websockets. */
(function () {
    'use strict';
    var OB = window.OB, $ = function (id) { return document.getElementById(id); }, h = OB.h;
    var engine = OB.engineId();
    var base = '/api/onboarding/engines/' + engine;
    var holder = false, picked = [];

    function say(id, text, isError) { OB.say($(id), text, isError); }

    function fail(out) {
        $('workspace').hidden = true;
        if (out.status === 404 || out.status === 401) { $('signin').hidden = !OB.sessionToken(); }
        say('msg', OB.problem(out), true);
    }

    function sectionLink(key, text) {
        return h('a', { href: 'section.html?engine=' + encodeURIComponent(engine) + '&section=' + encodeURIComponent(key), text: text });
    }

    function renderProgress(p) {
        $('waiting').textContent = p.waiting_on.line;
        // Gary's send-back notes (PR 3b-1): shown until the section is next marked final. Text only.
        var sent = p.sections.filter(function (s) { return s.rejection_note; }), sentList = $('sentBackList');
        OB.clear(sentList);
        $('sentBackBox').hidden = !sent.length;
        sent.forEach(function (s) { sentList.appendChild(h('li', {}, [sectionLink(s.key, s.title), ': ' + s.rejection_note])); });
        var rows = $('sectionRows');
        OB.clear(rows);
        p.sections.forEach(function (s) {
            rows.appendChild(h('tr', {}, [
                h('td', { text: s.title }), h('td', { text: s.status + (s.ready && s.status === 'draft' ? ' (ready)' : '') }), h('td', { text: s.items }), h('td', { text: s.open }),
                h('td', { text: s.answered }), h('td', { text: s.disagreed }), h('td', { text: s.final }), h('td', { text: s.approved }), h('td', {}, [sectionLink(s.key, 'Open')])
            ]));
        });
        var left = $('left');
        OB.clear(left);
        p.left.forEach(function (l) {
            left.appendChild(h('li', {}, [sectionLink(l.section, (OB.SECTION_TITLES[l.section] || l.section) + ': ' + l.item_id), ' (' + (OB.REASONS[l.reason] || l.reason) + ')']));
        });
        if (!p.left.length) { left.appendChild(h('li', { text: 'Nothing is left to answer.' })); }
        $('leftMore').hidden = p.left_total <= p.left.length;
        if (p.left_total > p.left.length) { $('leftMore').textContent = 'Showing ' + p.left.length + ' of ' + p.left_total + '.'; }
    }

    function renderDelegations(list) {
        var mine = list.filter(function (d) { return d.active && d.to === 'you'; })[0];
        $('delegateBox').hidden = !mine;
        if (mine) { $('delegateText').textContent = 'The advisor has delegated final say to you for: ' + OB.scopeText(mine.scope) + '.'; }
        if (!holder) { return; }
        var table = $('delegations'), rows = $('delegationRows');
        OB.clear(rows);
        table.hidden = !list.length;
        list.forEach(function (d) {
            var cell = h('td', {});
            if (d.active) {
                var b = h('button', { class: 'small', type: 'button', text: 'Revoke' });
                b.addEventListener('click', function () { revoke(d.delegation_id); });
                cell.appendChild(b);
            }
            rows.appendChild(h('tr', {}, [h('td', { text: d.to }), h('td', { text: OB.scopeText(d.scope) }), h('td', { text: OB.when(d.created_at) }),
                                          h('td', { text: d.active ? 'active' : (d.revoked_at ? 'revoked ' + OB.when(d.revoked_at) : 'ended') }), cell]));
        });
    }

    function load() {
        return OB.call('GET', base).then(function (out) {
            if (!out.ok) { return fail(out); }
            var e = out.data;
            holder = !!e.final_say;
            $('workspace').hidden = false;
            $('signin').hidden = true;
            $('msg').textContent = '';
            $('title').textContent = e.label || engine;
            $('who').textContent = 'You are an owner of this engine' + (holder ? ' with the final say' : '') + '. The engine is ' + (e.state || 'open') + '.';
            renderProgress(e.progress);
            // The status of approved changes on their way to the repository (PR 3b-2): read only, text only, no file and no address.
            var blist = $('bundleList');
            OB.clear(blist);
            $('bundleBox').hidden = !(e.bundles || []).length;
            (e.bundles || []).forEach(function (b) {
                blist.appendChild(h('li', { text: (b.status === 'merged' ? 'Merged into the repository' : 'Prepared for the repository') + ' ' + OB.when(b.at) + ': ' + b.sections.join(', ') }));
            });
            $('finalBox').hidden = !e.can_mark_final;
            $('delegationBox').hidden = !holder;
            if (document.activeElement !== $('notifyEmail')) { $('notifyEmail').checked = !!e.notifications_email; }
            showEmailsOff();
            return OB.call('GET', base + '/delegations').then(function (d) { if (d.ok) { renderDelegations(d.data.delegations || []); } });
        }).catch(function () { say('msg', 'Network error. Retrying shortly.', true); });
    }

    function markAll() {
        var b = $('markAll');
        b.disabled = true;
        say('markAllResult', 'Working...', false);
        OB.call('POST', base + '/sections/final-all').then(function (out) {
            b.disabled = false;
            if (!out.ok) { return say('markAllResult', OB.problem(out), true); }
            var left = out.data.skipped.map(function (s) { return (OB.SECTION_TITLES[s.section] || s.section) + ' (' + (OB.REASONS[s.reason] || s.reason) + ')'; });
            var done = out.data.marked.map(function (k) { return OB.SECTION_TITLES[k] || k; });
            say('markAllResult', (done.length ? 'Marked final: ' + done.join(', ') + '. ' : 'Nothing was ready to mark. ') + (left.length ? 'Left as they were: ' + left.join('; ') + '.' : ''), false);
            load();
        }).catch(function () { b.disabled = false; say('markAllResult', 'Network error. Please try again.', true); });
    }

    function revoke(id) {
        OB.call('DELETE', base + '/delegations/' + encodeURIComponent(id)).then(function (out) {
            say('delegateResult', out.ok ? 'The delegation was revoked. It stops working at once.' : OB.problem(out), !out.ok);
            load();
        }).catch(function () { say('delegateResult', 'Network error. Please try again.', true); });
    }

    // F1: no scope is preselected. Delegate is enabled only once the holder has chosen "All sections", or "Only the sections I choose" with at least one section ticked.
    function delegateReady() {
        return $('dscopeAll').checked || ($('dscopeSome').checked && picked.some(function (k) { return $('d_' + k).checked; }));
    }
    function syncDelegate() { $('delegate').disabled = !delegateReady(); }

    function delegate() {
        if (!delegateReady()) { return; }
        var scope = $('dscopeAll').checked ? 'all' : picked.filter(function (k) { return $('d_' + k).checked; });
        if (scope !== 'all' && !scope.length) { return say('delegateResult', 'Choose at least one section, or delegate all.', true); }
        $('delegate').disabled = true;
        OB.call('PUT', base + '/delegations', { to: 'other_owner', scope: scope }).then(function (out) {
            syncDelegate();
            say('delegateResult', out.ok ? 'Delegated to the other owner for: ' + OB.scopeText(out.data.scope) + '. A new delegation replaces any earlier one.' : OB.problem(out), !out.ok);
            load();
        }).catch(function () { syncDelegate(); say('delegateResult', 'Network error. Please try again.', true); });
    }

    // F2: while the emails are off, a visible line says so near the top of the page.
    function showEmailsOff() { $('emailsOff').hidden = $('notifyEmail').checked; }

    // F2: switching the emails OFF asks first; switching them ON does not.
    function notifications() {
        var on = $('notifyEmail').checked;
        if (!on && !confirm("Stop these emails? You won't be told when a section is ready or re-opened.")) { $('notifyEmail').checked = true; showEmailsOff(); return; }
        OB.call('PUT', base + '/notifications', { email: on }).then(function (out) {
            if (out.ok) { say('notifyResult', on ? 'You will get these emails.' : 'You will not get these emails.', false); }
            else { $('notifyEmail').checked = !on; say('notifyResult', OB.problem(out), true); }
            showEmailsOff();
        }).catch(function () { $('notifyEmail').checked = !on; say('notifyResult', 'Network error. Please try again.', true); showEmailsOff(); });
    }

    function start() {
        if (!engine) { return say('msg', 'This page needs the link from your email, which names the engine.', true); }
        if (!OB.sessionToken()) { $('signin').hidden = false; return; }
        var box = $('dsections');
        OB.SECTION_KEYS.forEach(function (k) {
            picked.push(k);
            box.appendChild(h('label', { class: 'choice' }, [h('input', { id: 'd_' + k, type: 'checkbox' }), ' ' + OB.SECTION_TITLES[k]]));
        });
        $('markAll').addEventListener('click', markAll);
        $('delegate').addEventListener('click', delegate);
        ['dscopeAll', 'dscopeSome'].concat(picked.map(function (k) { return 'd_' + k; })).forEach(function (id) { $(id).addEventListener('change', syncDelegate); });
        syncDelegate();
        $('notifyEmail').addEventListener('change', notifications);
        load();
        OB.poll(load, 20000);
    }
    start();
}());
