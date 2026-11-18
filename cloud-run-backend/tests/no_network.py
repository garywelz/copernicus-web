"""NO TEST MAY REACH THE NETWORK. Installed by tests/conftest.py before any test module is imported, and in every Python subprocess a test starts (through
tests/no_network_site/sitecustomize.py, which conftest.py puts first on PYTHONPATH).

Found on 2026-11-18 by a record-only probe of the full suite on main 0bf6e1362:
  - the tests read real production secrets from Secret Manager with the machine's own sign-in: the ElevenLabs key (43 times, at the import of
    services/podcast_generation_service.py) and the admin API key (utils/auth.py, which then also copies it into os.environ);
  - each such read refreshed a Google OAuth token at oauth2.googleapis.com, and two tests in tests/unit/test_curated_generation.py took 8.5 hours and
    1.9 hours on one evening;
  - tests/integration/test_live_description_validation.py listed every production episode over Firestore's REST API.

What is refused, each recorded in ATTEMPTS:
  - a DNS lookup or a socket connection to anything but loopback (Python's socket module: requests, urllib, httpx, aiohttp, asyncio);
  - google.auth.default(): a Google client never gets the machine's credentials;
  - a gRPC channel to anything but a local address (gRPC's own sockets are not Python's, so they need their own refusal).
A refusal raises RealNetworkRefused, an OSError, so code that already treats a network failure as "unavailable" goes on doing so. conftest.py fails any
test during which a refusal happened, unless the test is marked `live` (opt-in: run with --run-live) or expected it (refusals_expected()).
"""
import contextlib
import os
import socket
import sys
import threading

ENV_FLAG = "COPERNICUS_TESTS_NO_NETWORK"
ATTEMPTS = []                                    # [{"kind", "target", "expected"}], in order
_state = {"allowed": False, "expected": 0, "installed": False}
_lock = threading.Lock()
_LOCAL = ("127.", "::1", "localhost", "0:0:0:0:0:0:0:1")


class RealNetworkRefused(OSError):
    """Raised instead of a DNS lookup, a connection, a Google sign-in or a gRPC channel inside the test suite."""


def is_local(host) -> bool:
    if host is None:
        return True
    h = host.decode() if isinstance(host, bytes) else str(host)
    h = h.strip("[]").lower()
    return h == "" or h.startswith(_LOCAL)


def grpc_host(target) -> str:
    """The host of a gRPC target: 'secretmanager.googleapis.com:443', 'dns:///x:443', 'ipv4:1.2.3.4:5', '[::1]:50051', 'unix:/path' (local)."""
    t = str(target)
    if t.startswith("unix:"):
        return "localhost"
    for prefix in ("dns:///", "dns:", "ipv4:", "ipv6:"):
        if t.startswith(prefix):
            t = t[len(prefix):]
            break
    if t.startswith("["):
        return t[1:t.index("]")] if "]" in t else t
    return t.rsplit(":", 1)[0] if t.count(":") == 1 else t


def _refuse(kind: str, target) -> None:
    with _lock:
        ATTEMPTS.append({"kind": kind, "target": str(target), "expected": _state["expected"] > 0})
    raise RealNetworkRefused(f"the test suite must never reach the network ({kind} {target}); use a fake, or mark the test `live`")


def _allowed() -> bool:
    return _state["allowed"]


@contextlib.contextmanager
def refusals_expected():
    """For tests of this guard: refusals inside the block are recorded as expected and do not fail the test."""
    _state["expected"] += 1
    try:
        yield
    finally:
        _state["expected"] -= 1


@contextlib.contextmanager
def network_allowed():
    """For tests marked `live` only (conftest.py uses it). Nothing else should call this."""
    _state["allowed"] = True
    try:
        yield
    finally:
        _state["allowed"] = False


def install() -> None:
    if _state["installed"]:
        return
    _state["installed"] = True
    real_connect, real_connect_ex, real_getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def _host(address):
        return address[0] if isinstance(address, tuple) and address else address

    def connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _allowed() and not is_local(_host(address)):
            _refuse("connect", address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _allowed() and not is_local(_host(address)):
            _refuse("connect", address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not _allowed() and not is_local(host):
            _refuse("dns", host)
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, getaddrinfo

    try:
        import google.auth
        import google.auth._default
        real_default = google.auth.default

        def default(*args, **kwargs):
            if _allowed():
                return real_default(*args, **kwargs)
            _refuse("google-auth", "default credentials")
        google.auth.default = default
        google.auth._default.default = default
    except ImportError:
        pass

    try:
        import grpc
        import grpc.aio

        def _target_local(target) -> bool:
            return is_local(grpc_host(target))

        for module, name in ((grpc, "secure_channel"), (grpc, "insecure_channel"), (grpc.aio, "secure_channel"), (grpc.aio, "insecure_channel")):
            real = getattr(module, name)

            def make(real, name):
                def channel(target, *args, **kwargs):
                    if not _allowed() and not _target_local(target):
                        _refuse("grpc", target)
                    return real(target, *args, **kwargs)
                return channel
            setattr(module, name, make(real, name))
    except ImportError:
        pass


def install_for_subprocesses(environ, site_dir: str) -> None:
    """Every Python subprocess a test starts inherits the guard: the flag, and the folder holding sitecustomize.py first on PYTHONPATH."""
    environ[ENV_FLAG] = "1"
    parts = [p for p in environ.get("PYTHONPATH", "").split(os.pathsep) if p and os.path.abspath(p) != os.path.abspath(site_dir)]
    environ["PYTHONPATH"] = os.pathsep.join([site_dir, *parts])


def report_to_stderr() -> None:
    """In a subprocess: say on stderr what was refused, so the test that started it can show it."""
    if ATTEMPTS:
        print(f"[no_network] refused {len(ATTEMPTS)} network attempt(s): " + "; ".join(f"{a['kind']} {a['target']}" for a in ATTEMPTS[:10]), file=sys.stderr)
