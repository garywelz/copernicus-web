"""The test suite never creates a real Firestore client (onboarding PR 4b-1, asked for by Gary 2026-11-10).

config/database.py creates a client at import, and on a signed-in machine that client is real and points at the production database. tests/conftest.py now
replaces the client classes with a stand-in that refuses to be created. These tests fail if that guard is removed, if a module finds another way to a real
client, or if any loaded module holds one."""
import importlib
import sys

import google.cloud.firestore as firestore
import google.cloud.firestore_v1 as firestore_v1
import pytest

from tests import conftest


def test_the_guard_is_installed_and_creating_a_client_is_refused_and_counted():
    for module in (firestore, firestore_v1):
        assert module.Client is conftest._NoRealFirestore and module.AsyncClient is conftest._NoRealFirestore
    assert all(isinstance(c, type) and c is not conftest._NoRealFirestore for c in conftest.REAL_FIRESTORE_CLASSES)
    before = len(conftest.FIRESTORE_ATTEMPTS)
    with pytest.raises(conftest.RealFirestoreRefused):
        firestore.Client(project="any-project", database="any-database")
    with pytest.raises(conftest.RealFirestoreRefused):
        firestore_v1.AsyncClient()
    assert len(conftest.FIRESTORE_ATTEMPTS) == before + 2


def test_importing_the_onboarding_routes_and_the_database_module_leaves_no_real_client():
    import config.database
    from endpoints.onboarding import routes
    importlib.reload(config.database)                           # import it again, as a fresh process would: the client it asks for is refused
    assert config.database.db is None, "config/database.py asked for a client, was refused, and fell back to None"
    assert not isinstance(routes.db, conftest.REAL_FIRESTORE_CLASSES)
    assert {"project", "database"} <= set(conftest.FIRESTORE_ATTEMPTS[-1]), "the attempt that was refused is the one config/database.py makes"


def test_no_loaded_module_holds_a_real_firestore_client():
    """Capable of failing: with the guard removed from tests/conftest.py, config.database.db is a real client on a signed-in machine, and this test names it."""
    held = []
    for name, module in list(sys.modules.items()):
        if module is None or name.startswith(("google.", "grpc", "proto", "_pytest", "pytest")):
            continue
        for attr, value in list(getattr(module, "__dict__", {}).items()):
            if isinstance(value, conftest.REAL_FIRESTORE_CLASSES):
                held.append(f"{name}.{attr}")
    assert held == [], held


def test_the_control_a_real_client_object_would_be_caught():
    """The check above is not vacuous: an object of the real client class, made without connecting to anything, is recognised."""
    real = object.__new__(conftest.REAL_FIRESTORE_CLASSES[0])    # no __init__: no credentials, no network, no project
    assert isinstance(real, conftest.REAL_FIRESTORE_CLASSES)
    module = type(sys)("a_module_holding_a_client")
    module.db = real
    assert [a for a, v in module.__dict__.items() if isinstance(v, conftest.REAL_FIRESTORE_CLASSES)] == ["db"]
