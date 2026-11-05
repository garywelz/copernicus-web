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
                    say('Invitation ' + r.out.invite_id + ' created; expires ' + r.out.expires_at + '. Email sent: ' + (r.out.email_sent ? 'yes' : 'NO (revoke it and try again)') + '.', !r.out.email_sent);
                } else {
                    say('Not created: ' + (typeof r.out.detail === 'string' ? r.out.detail : r.status), true);
                }
            })
            .catch(function (e) { say('Not created: ' + e.message, true); });
    });

    $('revokeInvite').addEventListener('click', function () {
        var id = $('invRevokeId').value.trim();
        if (!id) { say('Enter an invitation id.', true); return; }
        if (!window.confirm('Revoke invitation ' + id + '? If it was already accepted, the membership is removed and the account can no longer generate.')) { return; }
        fetch(API + '/api/admin/onboarding/invites/' + encodeURIComponent(id), { method: 'DELETE', headers: headers() })
            .then(function (res) { return res.json().catch(function () { return {}; }).then(function (out) { return { ok: res.ok, status: res.status, out: out }; }); })
            .then(function (r) { say(r.ok ? 'Revoked (' + r.out.outcome + ').' : 'Not revoked: ' + (typeof r.out.detail === 'string' ? r.out.detail : r.status), !r.ok); })
            .catch(function (e) { say('Not revoked: ' + e.message, true); });
    });

    showKeyState();
}());
