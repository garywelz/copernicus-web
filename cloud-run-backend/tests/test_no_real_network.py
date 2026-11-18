"""The suite's network guard (tests/no_network.py, installed by tests/conftest.py). Every test here fails if the guard is removed or stops refusing. Nothing
here reaches the network: each refusal happens before a packet is sent, and the addresses are reserved documentation addresses (RFC 5737, RFC 3849) and
the reserved .invalid domain."""
import os
import socket
import subprocess
import sys
import textwrap

import pytest

from tests import conftest
from tests import no_network as nn

DOC_V4 = ("192.0.2.1", 443)             # TEST-NET-1: never routed
DOC_V6 = ("2001:db8::1", 443, 0, 0)     # the IPv6 documentation prefix


def test_the_guard_is_installed_before_any_test_and_in_the_environment_of_subprocesses():
    assert socket.socket.connect.__module__ == nn.__name__ and socket.getaddrinfo.__module__ == nn.__name__
    assert os.environ[nn.ENV_FLAG] == "1" and os.environ["PYTHONPATH"].split(os.pathsep)[0].endswith("no_network_site")


@pytest.mark.parametrize("family,address", [(socket.AF_INET, DOC_V4), (socket.AF_INET6, DOC_V6)])
def test_a_connection_to_a_real_address_is_refused_and_recorded(family, address):
    s = socket.socket(family, socket.SOCK_STREAM)
    try:
        with nn.refusals_expected(), pytest.raises(nn.RealNetworkRefused):
            s.connect(address)
        with nn.refusals_expected():
            with pytest.raises(nn.RealNetworkRefused):
                s.connect_ex(address)
    finally:
        s.close()
    assert nn.ATTEMPTS[-1]["kind"] == "connect" and nn.ATTEMPTS[-1]["expected"] is True


def test_a_dns_lookup_is_refused_and_a_refusal_is_an_oserror_so_existing_fallbacks_still_apply():
    with nn.refusals_expected(), pytest.raises(OSError):
        socket.getaddrinfo("registry.example.invalid", 443)
    assert nn.ATTEMPTS[-1] == {"kind": "dns", "target": "registry.example.invalid", "expected": True}


def test_requests_and_urllib_are_refused_before_any_packet_is_sent():
    import requests
    import urllib.request
    with nn.refusals_expected():
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get("https://registry.example.invalid/x", timeout=2)
        with pytest.raises(OSError):
            urllib.request.urlopen("https://registry.example.invalid/x", timeout=2)


def test_google_sign_in_and_a_grpc_channel_to_a_real_host_are_refused():
    import google.auth
    import grpc
    with nn.refusals_expected():
        with pytest.raises(nn.RealNetworkRefused):
            google.auth.default()
        with pytest.raises(nn.RealNetworkRefused):
            grpc.secure_channel("secretmanager.googleapis.com:443", grpc.ssl_channel_credentials())
        with pytest.raises(nn.RealNetworkRefused):
            grpc.insecure_channel("dns:///firestore.googleapis.com:443")
    grpc.insecure_channel("localhost:50051").close()                                    # a local channel (an emulator) is allowed


def test_a_real_secret_manager_client_cannot_be_created():
    from google.cloud import secretmanager
    before = len(conftest.SECRET_MANAGER_ATTEMPTS)
    with pytest.raises(conftest.RealSecretManagerRefused):
        secretmanager.SecretManagerServiceClient()
    assert len(conftest.SECRET_MANAGER_ATTEMPTS) == before + 1


def test_the_service_code_falls_back_when_no_secret_can_be_read(monkeypatch):
    from utils import auth
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    assert auth.get_admin_api_key() is None and "ADMIN_API_KEY" not in os.environ        # nothing real is copied into the environment


def test_loopback_is_allowed():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(server.getsockname())
        assert socket.getaddrinfo("localhost", 80)
    finally:
        client.close()
        server.close()


@pytest.mark.parametrize("target,host", [("secretmanager.googleapis.com:443", "secretmanager.googleapis.com"), ("dns:///x.example:443", "x.example"),
                                         ("ipv4:192.0.2.1:5", "192.0.2.1"), ("[::1]:50051", "::1"), ("unix:/tmp/s", "localhost"), ("localhost", "localhost")])
def test_grpc_targets_are_read_for_their_host(target, host):
    assert nn.grpc_host(target) == host


def test_a_python_subprocess_started_by_a_test_is_refused_the_network_too():
    code = textwrap.dedent("""
        import socket, sys
        try:
            socket.getaddrinfo("registry.example.invalid", 443)
        except OSError as e:
            print(type(e).__name__); sys.exit(0)
        print("NOT REFUSED"); sys.exit(1)
    """)
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and p.stdout.strip() == "RealNetworkRefused", p.stdout + p.stderr
    assert "[no_network] refused 1 network attempt(s): dns registry.example.invalid" in p.stderr


def test_a_test_that_reaches_for_the_network_fails(pytester):
    """The autouse fixture fails a test in which a refusal happened, even when the code under test swallowed the error."""
    pytester.makeconftest("from tests.conftest import *  # noqa\nfrom tests.conftest import _no_real_network  # noqa\n")
    pytester.makepyfile(test_reach=textwrap.dedent("""
        import socket
        def test_swallows_the_error():
            try:
                socket.getaddrinfo("registry.example.invalid", 443)
            except OSError:
                pass
    """))
    start = len(nn.ATTEMPTS)
    result = pytester.runpytest_inprocess("-p", "no:cacheprovider", "-q")
    for a in nn.ATTEMPTS[start:]:
        a["expected"] = True                                                               # the inner run's refusal is this test's subject, not its failure
    result.assert_outcomes(passed=1, errors=1)                                           # the test body passed; the guard's check failed it
    result.stdout.fnmatch_lines(["*tried to reach the network*dns registry.example.invalid*"])


def test_a_live_test_is_skipped_by_default(pytester):
    pytester.makeconftest("from tests.conftest import *  # noqa\nfrom tests.conftest import _no_real_network, pytest_addoption, pytest_collection_modifyitems  # noqa\n")
    pytester.makeini("[pytest]\nmarkers =\n    live: live\n")
    pytester.makepyfile(test_live="import pytest\n@pytest.mark.live\ndef test_reads_a_real_service():\n    assert False\n")
    pytester.runpytest_inprocess("-p", "no:cacheprovider", "-q").assert_outcomes(skipped=1)
