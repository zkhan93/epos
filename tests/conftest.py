"""Test rig: no network, no shared state between tests.

Every outbound call goes through the single pooled session in crawler.core, so
stubbing that one object is enough to run the whole app offline.
"""

import json
import pathlib
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

EPOS_SALES = "FPS_Trans_Details.jsp"
EPOS_RC = "SRC_Trans_Details.jsp"
EPOS_STOCK = "fps_stock_register.action"
EPDS_RC = "SearchByRCID.aspx"
KAIMUR = "admin-ajax.php"


def fixture(name):
    return (FIXTURES / name).read_text()


class FakeResponse:
    def __init__(self, text="", payload=None, status_code=200):
        self.text = text
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code} error")


class Upstream:
    """Canned replies keyed by a substring of the URL."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def route(self, url_fragment, response):
        self.routes[url_fragment] = response

    def _handle(self, method, url, data):
        self.calls.append((method, url, dict(data or {})))
        for fragment, response in self.routes.items():
            if fragment in url:
                return response(data) if callable(response) else response
        raise AssertionError(f"unstubbed {method} to {url}")

    def calls_to(self, url_fragment):
        return [c for c in self.calls if url_fragment in c[1]]


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Point diskcache at a throwaway directory and reset the singleton."""
    import utils

    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    utils._cache = None
    yield
    if utils._cache is not None:
        utils._cache.close()
    utils._cache = None


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Nothing in the suite is allowed to touch the real government site."""
    import crawler.core

    def blocked(url, *args, **kwargs):
        raise AssertionError(f"test tried to reach the network: {url}")

    monkeypatch.setattr(crawler.core.session, "post", blocked)
    monkeypatch.setattr(crawler.core.session, "get", blocked)


def _drain_registry(timeout=10.0):
    """Let in-flight tasks finish, then drop the pool and the results.

    Draining has to happen while the network stub is still installed. A worker
    thread that outlives its test would otherwise reach the real government
    site and block on its read timeout -- which is exactly what happened before
    this fixture was ordered after no_network.
    """
    import tasks

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with tasks._registry._lock:
            busy = any(not e.done() for e in tasks._registry._entries.values())
        if not busy:
            break
        time.sleep(0.01)
    pool, tasks._registry._pool = tasks._registry._pool, None
    if pool is not None:
        pool.shutdown(wait=False, cancel_futures=True)
    tasks._registry._entries.clear()
    tasks._registry._inflight.clear()


@pytest.fixture(autouse=True)
def clean_registry(no_network):
    """Each test gets an empty task registry and its own thread pool.

    Depends on no_network so that it tears down *before* the stub is removed.
    """
    _drain_registry()
    yield
    _drain_registry()


@pytest.fixture
def upstream(monkeypatch, no_network):
    import crawler.core

    stub = Upstream()
    monkeypatch.setattr(
        crawler.core.session,
        "post",
        lambda url, data=None, **kw: stub._handle("POST", url, data),
    )
    monkeypatch.setattr(
        crawler.core.session,
        "get",
        lambda url, **kw: stub._handle("GET", url, None),
    )
    return stub


@pytest.fixture
def epos_upstream(upstream):
    """The happy path: every government endpoint answers with a good fixture."""
    upstream.route(EPOS_SALES, FakeResponse(text=fixture("sales_details.html")))
    upstream.route(EPOS_RC, FakeResponse(text=fixture("rc_details.html")))
    upstream.route(EPOS_STOCK, FakeResponse(text=fixture("stock_details.html")))
    upstream.route(EPDS_RC, FakeResponse(text=fixture("epds_rc_details.html")))
    upstream.route(
        KAIMUR,
        FakeResponse(
            payload={
                "result": [{"name": "A Kumar", "designation": "DM"}],
                "paged": 1,
                "mp": 1,
            }
        ),
    )
    return upstream


@pytest.fixture
def client():
    from app import app

    app.config.update(TESTING=True)
    return app.test_client()


def poll(client, task_id, timeout=10.0):
    """Poll /tasks/<id> the way the browser does, and return the final payload.

    Also asserts the intermediate statuses stay inside the set the frontend
    knows how to handle.
    """
    deadline = time.monotonic() + timeout
    seen = set()
    while time.monotonic() < deadline:
        body = client.get(f"/tasks/{task_id}").get_json()
        seen.add(body["status"])
        assert body["status"] in {
            "PENDING",
            "STARTED",
            "SUCCESS",
            "FAILURE",
        }, f"unknown status {body['status']}"
        if body["status"] in ("SUCCESS", "FAILURE"):
            body["_seen"] = seen
            return body
        time.sleep(0.02)
    raise AssertionError(f"task {task_id} never finished; saw {seen}")
