"""Loaded by every Python subprocess a test starts (tests/conftest.py puts this folder first on PYTHONPATH): the same network guard as the test process
(tests/no_network.py). It does nothing unless COPERNICUS_TESTS_NO_NETWORK=1, which only conftest.py sets."""
import atexit
import os
import sys

if os.environ.get("COPERNICUS_TESTS_NO_NETWORK") == "1":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import no_network
    sys.path.pop(0)
    no_network.install()
    atexit.register(no_network.report_to_stderr)
