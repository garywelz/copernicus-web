"""Guarded fetching of URLs the backend is asked to read (curated-sources design §3.6).

Every fetch of an address someone supplied goes through `guarded_get`. It allows `http` and `https` only, on the standard ports, with
no credentials in the address; resolves the host itself and refuses the request if ANY resolved address is not a public one
(private, loopback, link-local, multicast, reserved and unspecified ranges, and IPv4 addresses written inside IPv6); connects only to
the addresses it checked (so a second, different DNS answer cannot be used); follows at most three redirects and applies every check
again at each one; caps the body (2 MB) and the time (15 s); sends an honest user-agent; and never sends a credential.

Nothing here reads robots.txt; that belongs to commentary retrieval (design §5), which will call this function.
The network layer is injectable (`resolver`, `opener`) so the checks are tested without a network.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlsplit

USER_AGENT = "copernicus-podcast-api/curated-sources (+https://www.copernicusai.fyi)"
MAX_BYTES = 2_000_000
TIMEOUT_S = 15
MAX_REDIRECTS = 3
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {None, 80, 443}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class FetchRefused(Exception):
    """The fetch was refused by a guard (not a network failure). `reason` is a short stable code."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason, self.detail = reason, detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass
class FetchResult:
    status: int
    headers: Dict[str, str]
    body: bytes
    final_url: str
    redirects: List[str] = field(default_factory=list)


Resolver = Callable[[str, int], Awaitable[Sequence[str]]]
# opener(url, method, headers, addresses, timeout, max_bytes) -> (status, headers, body); it must not follow redirects
Opener = Callable[[str, str, Dict[str, str], Sequence[str], float, int], Awaitable[Tuple[int, Dict[str, str], bytes]]]


def is_public_address(address: str) -> bool:
    """True only for a globally routable unicast address. IPv4-mapped IPv6 addresses are judged as the IPv4 they hold."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        ip = mapped
    sixtofour = getattr(ip, "sixtofour", None)
    if sixtofour is not None and not sixtofour.is_global:
        return False
    return bool(ip.is_global and not (ip.is_multicast or ip.is_private or ip.is_loopback or ip.is_link_local
                                      or ip.is_reserved or ip.is_unspecified))


def validate_url(url: str, allowed_hosts: Optional[Sequence[str]] = None) -> Tuple[str, str, int]:
    """Check the parts of an address that need no network. Returns (scheme, host, port); raises FetchRefused."""
    if not isinstance(url, str) or not url or len(url) > 2000 or any(c in url for c in "\r\n\t "):
        raise FetchRefused("bad_url")
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise FetchRefused("scheme_not_allowed", scheme or "none")
    if parts.username is not None or parts.password is not None or "@" in (parts.netloc or ""):
        raise FetchRefused("credentials_in_url")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise FetchRefused("bad_url")
    try:
        port = parts.port
    except ValueError:
        raise FetchRefused("bad_port")
    if port not in ALLOWED_PORTS:
        raise FetchRefused("port_not_allowed", str(port))
    if allowed_hosts is not None and host not in {h.lower() for h in allowed_hosts}:
        raise FetchRefused("host_not_allowed", host)
    if host == "localhost" or host.endswith(".localhost"):
        raise FetchRefused("address_not_public", host)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # a name: its addresses are checked after resolution
    else:
        if not is_public_address(host):
            raise FetchRefused("address_not_public", host)
    return scheme, host, port or (443 if scheme == "https" else 80)


async def _default_resolver(host: str, port: int) -> Sequence[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return sorted({i[4][0] for i in infos})


async def resolve_public(host: str, port: int, resolver: Optional[Resolver] = None) -> List[str]:
    """Resolve a host and require EVERY address to be public. Returns the checked addresses."""
    try:
        addrs = list(await (resolver or _default_resolver)(host, port))
    except FetchRefused:
        raise
    except Exception as e:
        raise FetchRefused("dns_failed", type(e).__name__)
    if not addrs:
        raise FetchRefused("dns_failed", "no address")
    bad = [a for a in addrs if not is_public_address(a)]
    if bad:
        raise FetchRefused("address_not_public", host)
    return addrs


async def _aiohttp_opener(url: str, method: str, headers: Dict[str, str], addresses: Sequence[str], timeout: float,
                          max_bytes: int) -> Tuple[int, Dict[str, str], bytes]:
    """One request, no redirects, connecting only to `addresses`, with the body capped."""
    import aiohttp
    from aiohttp.abc import AbstractResolver

    class _Pinned(AbstractResolver):
        async def resolve(self, host, port=0, family=socket.AF_INET):
            out = []
            for a in addresses:
                fam = socket.AF_INET6 if ":" in a else socket.AF_INET
                out.append({"hostname": host, "host": a, "port": port, "family": fam, "proto": 0, "flags": socket.AI_NUMERICHOST})
            return out

        async def close(self):
            return None

    connector = aiohttp.TCPConnector(resolver=_Pinned(), use_dns_cache=False, force_close=True)
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout_cfg, headers=headers, auto_decompress=True) as session:
        async with session.request(method, url, allow_redirects=False) as resp:
            declared = resp.headers.get("Content-Length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise FetchRefused("too_large", declared)
            body = bytearray()
            if method != "HEAD":
                async for chunk in resp.content.iter_chunked(65536):
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise FetchRefused("too_large", f">{max_bytes}")
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, bytes(body)


async def guarded_get(url: str, *, method: str = "GET", allowed_hosts: Optional[Sequence[str]] = None,
                      extra_headers: Optional[Dict[str, str]] = None, max_bytes: int = MAX_BYTES, timeout: float = TIMEOUT_S,
                      max_redirects: int = MAX_REDIRECTS, resolver: Optional[Resolver] = None,
                      opener: Optional[Opener] = None) -> FetchResult:
    """Fetch `url` under every guard above. Raises FetchRefused for a guard; other network errors propagate as they are.
    Any HTTP status is returned to the caller (a 404 is a result, not a refusal)."""
    if method not in ("GET", "HEAD"):
        raise FetchRefused("method_not_allowed", method)
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    for k, v in (extra_headers or {}).items():
        if k.lower() in ("authorization", "cookie", "proxy-authorization", "x-admin-api-key", "x-subscriber-token"):
            raise FetchRefused("credential_header_refused", k)
        headers[k] = v
    visited: List[str] = []
    current = url
    for _ in range(max_redirects + 1):
        _scheme, host, port = validate_url(current, allowed_hosts)
        addrs = await resolve_public(host, port, resolver)
        status, resp_headers, body = await (opener or _aiohttp_opener)(current, method, headers, addrs, timeout, max_bytes)
        if status in REDIRECT_STATUSES and resp_headers.get("location"):
            visited.append(current)
            current = urljoin(current, resp_headers["location"])
            continue
        return FetchResult(status=status, headers=resp_headers, body=body, final_url=current, redirects=visited)
    raise FetchRefused("too_many_redirects", str(max_redirects))
