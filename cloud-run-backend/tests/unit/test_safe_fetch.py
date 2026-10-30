"""The fetch guards (curated-sources design §3.6). Offline: the resolver and the opener are faked, so every guard is exercised without a network."""
import asyncio

import pytest

import safe_fetch
from safe_fetch import FetchRefused, guarded_get, is_public_address, validate_url


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def resolver_for(mapping):
    async def resolve(host, port):
        if host not in mapping:
            raise OSError("no such host")
        return mapping[host]
    return resolve


class Opener:
    """Answers from a script of (status, headers, body); records every call."""

    def __init__(self, *script):
        self.script, self.calls = list(script), []

    async def __call__(self, url, method, headers, addresses, timeout, max_bytes):
        self.calls.append({"url": url, "method": method, "headers": dict(headers), "addresses": list(addresses),
                           "timeout": timeout, "max_bytes": max_bytes})
        return self.script.pop(0)


PUBLIC = {"example.org": ["93.184.216.34"], "other.example": ["8.8.8.8"]}


def get(url, opener, resolver=None, **kw):
    return run(guarded_get(url, resolver=resolver or resolver_for(PUBLIC), opener=opener, **kw))


# --- which addresses are public -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("addr", ["93.184.216.34", "8.8.8.8", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses_are_allowed(addr):
    assert is_public_address(addr)


def test_an_ipv4_address_written_inside_ipv6_is_judged_as_the_ipv4_it_holds():
    # the judgement must not depend on how a given Python version classifies the ::ffff:0:0/96 block
    assert is_public_address("::ffff:8.8.8.8")
    assert not is_public_address("::ffff:127.0.0.1") and not is_public_address("::ffff:192.168.1.1")


@pytest.mark.parametrize("addr", [
    "127.0.0.1", "127.1.2.3", "10.0.0.5", "172.16.0.1", "172.31.255.255", "192.168.1.1", "169.254.169.254",  # metadata server
    "0.0.0.0", "100.64.0.1", "224.0.0.1", "240.0.0.1", "255.255.255.255", "192.0.2.1",
    "::1", "::", "fe80::1", "fc00::1", "fd12:3456::1", "ff02::1",
    "::ffff:127.0.0.1", "::ffff:10.0.0.1", "::ffff:169.254.169.254", "64:ff9b::7f00:1", "not an address", ""])
def test_non_public_addresses_are_refused(addr):
    assert not is_public_address(addr)


# --- the address itself ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("url,reason", [
    ("ftp://example.org/x", "scheme_not_allowed"), ("file:///etc/passwd", "scheme_not_allowed"), ("gopher://example.org", "scheme_not_allowed"),
    ("javascript:alert(1)", "scheme_not_allowed"), ("//example.org/x", "scheme_not_allowed"), ("example.org/x", "scheme_not_allowed"),
    ("https://user:pw@example.org/x", "credentials_in_url"), ("https://user@example.org/x", "credentials_in_url"),
    ("https://example.org:8443/x", "port_not_allowed"), ("http://example.org:22/x", "port_not_allowed"),
    ("http://localhost/x", "address_not_public"), ("http://app.localhost/x", "address_not_public"),
    ("http://127.0.0.1/x", "address_not_public"), ("http://[::1]/x", "address_not_public"), ("http://10.1.2.3/x", "address_not_public"),
    ("http://169.254.169.254/computeMetadata/v1/", "address_not_public"), ("http://[::ffff:127.0.0.1]/", "address_not_public"),
    ("", "bad_url"), ("https://", "bad_url"), ("https://exa mple.org/", "bad_url"), ("https://example.org/\r\nHost: x", "bad_url"),
    ("https://example.org/" + "a" * 2100, "bad_url")])
def test_addresses_refused_without_any_network(url, reason):
    with pytest.raises(FetchRefused) as e:
        validate_url(url)
    assert e.value.reason == reason


def test_a_good_address_is_accepted_and_the_default_port_is_filled_in():
    assert validate_url("https://Example.org/x") == ("https", "example.org", 443)
    assert validate_url("http://example.org:80/x") == ("http", "example.org", 80)


def test_the_host_allow_list_is_enforced_when_given():
    validate_url("https://raw.githubusercontent.com/a/b", ["raw.githubusercontent.com"])
    with pytest.raises(FetchRefused) as e:
        validate_url("https://example.org/", ["raw.githubusercontent.com"])
    assert e.value.reason == "host_not_allowed"


# --- resolution: every resolved address must be public ------------------------------------------------------------------------
def test_a_name_that_resolves_to_a_private_address_is_refused_before_any_request():
    op = Opener((200, {}, b"x"))
    with pytest.raises(FetchRefused) as e:
        get("https://evil.example/x", op, resolver_for({"evil.example": ["127.0.0.1"]}))
    assert e.value.reason == "address_not_public" and op.calls == []


def test_one_private_address_among_public_ones_refuses_the_request():
    op = Opener((200, {}, b"x"))
    with pytest.raises(FetchRefused):
        get("https://mixed.example/x", op, resolver_for({"mixed.example": ["93.184.216.34", "10.0.0.8"]}))
    assert op.calls == []


def test_an_integer_or_hex_host_that_resolves_private_is_refused():
    op = Opener((200, {}, b"x"))
    for host in ("2130706433", "0x7f000001", "017700000001"):
        with pytest.raises(FetchRefused):
            get(f"http://{host}/x", op, resolver_for({host: ["127.0.0.1"]}))
    assert op.calls == []


def test_dns_failure_is_a_refusal_not_a_crash():
    with pytest.raises(FetchRefused) as e:
        get("https://nonexistent.example/x", Opener(), resolver_for({}))
    assert e.value.reason == "dns_failed"


def test_the_connection_goes_only_to_the_addresses_that_were_checked():
    op = Opener((200, {"content-type": "text/plain"}, b"hello"))
    res = get("https://example.org/x", op)
    assert op.calls[0]["addresses"] == ["93.184.216.34"]
    assert res.status == 200 and res.body == b"hello" and res.final_url == "https://example.org/x"


# --- redirects --------------------------------------------------------------------------------------------------------------
def test_a_redirect_to_a_private_address_is_refused_and_never_requested():
    op = Opener((302, {"location": "http://169.254.169.254/computeMetadata/v1/"}, b""), (200, {}, b"secret"))
    with pytest.raises(FetchRefused) as e:
        get("https://example.org/x", op)
    assert e.value.reason == "address_not_public" and len(op.calls) == 1


def test_a_redirect_to_a_name_that_resolves_private_is_refused():
    op = Opener((301, {"location": "https://inner.example/x"}, b""), (200, {}, b"secret"))
    with pytest.raises(FetchRefused):
        get("https://example.org/x", op, resolver_for({**PUBLIC, "inner.example": ["192.168.0.10"]}))
    assert len(op.calls) == 1


def test_a_redirect_to_another_scheme_or_a_credentialed_address_is_refused():
    for loc in ("file:///etc/passwd", "ftp://example.org/x", "https://u:p@example.org/x", "https://example.org:9999/x"):
        with pytest.raises(FetchRefused):
            get("https://example.org/x", Opener((302, {"location": loc}, b"")))


def test_a_public_redirect_is_followed_and_reported():
    op = Opener((301, {"location": "https://other.example/y"}, b""), (200, {}, b"ok"))
    res = get("https://example.org/x", op)
    assert res.body == b"ok" and res.final_url == "https://other.example/y" and res.redirects == ["https://example.org/x"]


def test_a_relative_redirect_stays_on_the_same_host():
    op = Opener((302, {"location": "/y"}, b""), (200, {}, b"ok"))
    assert get("https://example.org/x", op).final_url == "https://example.org/y"


def test_too_many_redirects_are_refused():
    op = Opener(*[(302, {"location": "https://example.org/loop"}, b"")] * 10)
    with pytest.raises(FetchRefused) as e:
        get("https://example.org/x", op)
    assert e.value.reason == "too_many_redirects" and len(op.calls) == 4


def test_the_host_allow_list_applies_at_every_redirect():
    op = Opener((302, {"location": "https://example.org/y"}, b""), (200, {}, b"x"))
    with pytest.raises(FetchRefused) as e:
        get("https://other.example/x", op, allowed_hosts=["other.example"])
    assert e.value.reason == "host_not_allowed"


# --- limits and headers ---------------------------------------------------------------------------------------------------------
def test_the_size_and_time_limits_are_passed_to_the_network_layer():
    op = Opener((200, {}, b""))
    get("https://example.org/x", op)
    assert op.calls[0]["max_bytes"] == 2_000_000 and op.calls[0]["timeout"] == 15


def test_the_user_agent_is_honest_and_no_credential_header_can_be_sent():
    op = Opener((200, {}, b""))
    get("https://example.org/x", op, extra_headers={"Accept": "application/json"})
    assert "copernicus" in op.calls[0]["headers"]["User-Agent"].lower() and op.calls[0]["headers"]["Accept"] == "application/json"
    for h in ("Authorization", "Cookie", "X-Admin-API-Key", "x-subscriber-token", "Proxy-Authorization"):
        with pytest.raises(FetchRefused) as e:
            get("https://example.org/x", Opener((200, {}, b"")), extra_headers={h: "secret"})
        assert e.value.reason == "credential_header_refused"


def test_only_get_and_head_are_allowed():
    for m in ("POST", "PUT", "DELETE"):
        with pytest.raises(FetchRefused):
            run(guarded_get("https://example.org/x", method=m, resolver=resolver_for(PUBLIC), opener=Opener()))


def test_an_error_status_is_a_result_not_a_refusal():
    res = get("https://example.org/x", Opener((404, {}, b"nope")))
    assert res.status == 404


# --- the real network layer's own guard (no connection is made) ----------------------------------------------------------------
def test_the_real_opener_refuses_an_oversized_declared_length_before_reading_anything():
    class Resp:
        status, headers = 200, {"Content-Length": "9999999"}

        class content:
            @staticmethod
            def iter_chunked(n):
                raise AssertionError("body must not be read")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    class Sess:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def request(self, *a, **k):
            return Resp()
    import aiohttp
    from unittest.mock import patch
    with patch.object(aiohttp, "ClientSession", Sess):
        with pytest.raises(FetchRefused) as e:
            run(safe_fetch._aiohttp_opener("https://example.org/x", "GET", {}, ["93.184.216.34"], 5, 2_000_000))
    assert e.value.reason == "too_large"


# --- the real network layer against a local server (the opener only; the guards above sit in front of it) -------------------------
def _with_server(handler_map, scenario):
    from aiohttp import web
    from aiohttp.test_utils import TestServer

    async def main():
        app = web.Application()
        for path, h in handler_map.items():
            app.router.add_get(path, h)
        server = TestServer(app, host="127.0.0.1")
        await server.start_server()
        try:
            return await scenario(server.port)
        finally:
            await server.close()
    return run(main())


def test_the_real_opener_connects_to_the_pinned_address_not_to_whatever_the_name_resolves_to():
    from aiohttp import web

    async def hello(request):
        return web.Response(text="pinned", headers={"X-Seen-Host": request.headers.get("Host", "")})

    async def scenario(port):
        # the name can never resolve; only the pinned address can have been used
        return await safe_fetch._aiohttp_opener(f"http://pinned.invalid:{port}/hello", "GET", {"User-Agent": "t"}, ["127.0.0.1"], 5, 10_000)
    status, headers, body = _with_server({"/hello": hello}, scenario)
    assert status == 200 and body == b"pinned"


def test_the_real_opener_does_not_follow_redirects_itself():
    from aiohttp import web

    async def redirect(request):
        raise web.HTTPFound("http://169.254.169.254/")

    async def scenario(port):
        return await safe_fetch._aiohttp_opener(f"http://pinned.invalid:{port}/r", "GET", {}, ["127.0.0.1"], 5, 10_000)
    status, headers, body = _with_server({"/r": redirect}, scenario)
    assert status == 302 and headers["location"] == "http://169.254.169.254/"


def test_the_real_opener_stops_reading_a_body_past_the_cap():
    from aiohttp import web

    async def big(request):
        resp = web.StreamResponse()
        await resp.prepare(request)          # no Content-Length: only the running count can stop it
        for _ in range(100):
            await resp.write(b"x" * 10_000)
        return resp

    async def scenario(port):
        return await safe_fetch._aiohttp_opener(f"http://pinned.invalid:{port}/big", "GET", {}, ["127.0.0.1"], 5, 50_000)
    with pytest.raises(FetchRefused) as e:
        _with_server({"/big": big}, scenario)
    assert e.value.reason == "too_large"
