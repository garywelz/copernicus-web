(function () {
    'use strict';
    var API = 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app';
    var KEY_NAME = 'admin_api_key';            // the same browser-storage name the admin dashboard uses

    function $(id) { return document.getElementById(id); }

    function readKey() {
        try { return window.localStorage.getItem(KEY_NAME) || ''; } catch (e) { return ''; }
    }

    function say(text, bad) {
        var el = $('result');
        el.textContent = text;                 // text only: nothing the server or the admin typed is ever rendered as HTML
        el.className = bad ? 'error' : 'ok';
    }

    function showKeyState() {
        $('keystate').textContent = readKey() ? 'An admin key is saved in this browser.' : 'No admin key is saved in this browser yet.';
    }

    function headers() {
        return { 'X-Admin-API-Key': readKey(), 'Content-Type': 'application/json' };
    }

    $('saveKey').addEventListener('click', function () {
        var value = $('adminKey').value.trim();
        if (!value) { say('Enter the admin key first.', true); return; }
        try { window.localStorage.setItem(KEY_NAME, value); } catch (e) { say('This browser would not save the key.', true); return; }
        $('adminKey').value = '';
        showKeyState();
        say('Key saved in this browser.', false);
    });

    $('sendInvite').addEventListener('click', function () {
        var quotaRaw = $('invQuota').value.trim();
        var body = {
            engine_id: $('invEngine').value.trim(),
            email: $('invEmail').value,
            final_say: $('invFinalSay').checked,
            can_generate: $('invCanGenerate').checked,
            monthly_quota: quotaRaw === '' ? null : Number(quotaRaw),
            expires_days: Number($('invDays').value)
        };
        if (!body.engine_id || !body.email) { say('Engine id and address are required.', true); return; }
        fetch(API + '/api/admin/onboarding/invites', { method: 'POST', headers: headers(), body: JSON.stringify(body) })
            .then(function (res) { return res.json().catch(function () { return {}; }).then(function (out) { return { ok: res.ok, status: res.status, out: out }; }); })
            .then(function (r) {
                if (r.ok) {
                    $('invEmail').value = '';                       // the address is not kept on the page
                    $('invRevokeId').value = r.out.invite_id || '';
                    if (body.engine_id) { loadList(); }
                    say('Invitation ' + r.out.invite_id + ' created; expires ' + r.out.expires_at + '. Email sent: ' + (r.out.email_sent ? 'yes' : 'NO (revoke it and try again)') + '.', !r.out.email_sent);
                } else {
                    say('Not created: ' + (typeof r.out.detail === 'string' ? r.out.detail : r.status), true);
                }
            })
            .catch(function (e) { say('Not created: ' + e.message, true); });
    });

    function revoke(id) {
        if (!id) { say('Enter an invitation id.', true); return; }
        if (!window.confirm('Revoke invitation ' + id + '? If it was already accepted, the membership is removed and the account can no longer generate.')) { return; }
        fetch(API + '/api/admin/onboarding/invites/' + encodeURIComponent(id), { method: 'DELETE', headers: headers() })
            .then(function (res) { return res.json().catch(function () { return {}; }).then(function (out) { return { ok: res.ok, status: res.status, out: out }; }); })
            .then(function (r) {
                say(r.ok ? 'Revoked (' + r.out.outcome + ').' : 'Not revoked: ' + (typeof r.out.detail === 'string' ? r.out.detail : r.status), !r.ok);
                if (r.ok && $('invEngine').value.trim()) { loadList(); }
            })
            .catch(function (e) { say('Not revoked: ' + e.message, true); });
    }

    $('revokeInvite').addEventListener('click', function () { revoke($('invRevokeId').value.trim()); });

    // The list: built with createElement and textContent only, so nothing from the server is ever rendered as HTML.
    function cell(row, text) {
        var td = document.createElement('td');
        td.textContent = text === null || text === undefined ? '' : String(text);
        row.appendChild(td);
        return td;
    }

    function renderList(invites) {
        var box = $('inviteList');
        while (box.firstChild) { box.removeChild(box.firstChild); }
        if (!invites.length) { box.textContent = 'No invitations for this engine.'; return; }
        var table = document.createElement('table');
        var head = document.createElement('tr');
        ['Status', 'Final say', 'Can generate', 'Quota', 'Created', 'Expires', 'Used', 'Revoked', ''].forEach(function (h) {
            var th = document.createElement('th');
            th.textContent = h;
            head.appendChild(th);
        });
        table.appendChild(head);
        invites.forEach(function (inv) {
            var tr = document.createElement('tr');
            cell(tr, inv.status);
            cell(tr, inv.final_say ? 'yes' : 'no');
            cell(tr, inv.can_generate ? 'yes' : 'no');
            cell(tr, inv.monthly_quota === null ? 'unlimited' : inv.monthly_quota);
            cell(tr, inv.created_at);
            cell(tr, inv.expires_at);
            cell(tr, inv.used_at);
            cell(tr, inv.revoked_at);
            var td = document.createElement('td');
            if (inv.status !== 'revoked') {
                var button = document.createElement('button');
                button.type = 'button';
                button.textContent = 'Revoke';
                button.addEventListener('click', function () { revoke(inv.invite_id); });
                td.appendChild(button);
            }
            tr.appendChild(td);
            table.appendChild(tr);
        });
        box.appendChild(table);
    }

    function loadList() {
        var engine = $('invEngine').value.trim();
        if (!engine) { say('Enter the engine id first.', true); return; }
        fetch(API + '/api/admin/onboarding/invites?engine_id=' + encodeURIComponent(engine), { method: 'GET', headers: headers() })
            .then(function (res) { return res.json().catch(function () { return {}; }).then(function (out) { return { ok: res.ok, status: res.status, out: out }; }); })
            .then(function (r) {
                if (r.ok) { renderList(r.out.invites || []); }
                else { say('Could not load: ' + (typeof r.out.detail === 'string' ? r.out.detail : r.status), true); }
            })
            .catch(function (e) { say('Could not load: ' + e.message, true); });
    }

    $('loadList').addEventListener('click', loadList);

    showKeyState();
}());
