(function () {
    'use strict';
    var API = 'https://copernicus-podcast-api-phzp4ie2sq-uc.a.run.app';

    // The token travels in the URL fragment (a browser never sends it to a server). Keep it in memory and take it out of the address bar and history.
    var match = /(?:^#|&)token=([^&]+)/.exec(window.location.hash || '');
    var token = '';
    if (match) {
        try { token = decodeURIComponent(match[1]); } catch (e) { token = ''; }
        window.history.replaceState(null, '', window.location.pathname);
    }

    var form = document.getElementById('acceptForm');
    var result = document.getElementById('result');
    var submit = document.getElementById('submit');

    function say(text, isError) {
        result.textContent = text;                 // text only: nothing the server or the user wrote is ever rendered as HTML
        result.className = isError ? 'error' : 'ok';
    }

    if (!token) {
        document.getElementById('notoken').hidden = false;
        form.hidden = true;
        return;
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var naming = form.querySelector('input[name="naming"]:checked');
        var body = {
            token: token,
            email: document.getElementById('email').value,
            name: document.getElementById('name').value,
            password: document.getElementById('password').value,
            consent: {
                naming: naming ? naming.value : 'role',
                licence_confirmed: document.getElementById('licenceConfirmed').checked,
                licence_other: document.getElementById('licenceOther').value || null,
                lookups: document.getElementById('lookups').checked,
                acknowledged: document.getElementById('acknowledged').checked
            }
        };
        submit.disabled = true;
        say('Working...', false);
        fetch(API + '/api/onboarding/invites/accept', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (data) { return { ok: response.ok, data: data }; });
        }).then(function (out) {
            if (out.ok) {
                token = '';
                body.password = '';
                form.hidden = true;
                say(String(out.data.message || 'Invitation accepted.'), false);
                document.getElementById('next').hidden = false;
            } else {
                submit.disabled = false;
                say(typeof out.data.detail === 'string' ? out.data.detail : 'This invitation could not be accepted.', true);
            }
        }).catch(function () {
            submit.disabled = false;
            say('Network error. Please try again.', true);
        });
    });
}());
