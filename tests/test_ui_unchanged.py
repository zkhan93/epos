"""The people using this are not going to relearn anything, so the frontend is
untouched and served exactly as it sits in the repo. These tests fail loudly if
a container change ever alters what the browser receives."""

import pathlib
import re

import pytest

STATIC = pathlib.Path(__file__).resolve().parents[1] / "static"
PAGES = sorted(p.stem for p in STATIC.glob("*.html"))


def test_every_page_in_static_is_reachable():
    assert PAGES == ["collection", "index", "officers", "pacs", "search", "stock"]


@pytest.mark.parametrize("page", PAGES)
def test_page_is_served_byte_for_byte(client, page):
    res = client.get(f"/{page}")
    assert res.status_code == 200
    assert res.data == (STATIC / f"{page}.html").read_bytes()


def test_root_serves_index(client):
    assert client.get("/").data == (STATIC / "index.html").read_bytes()


def test_pacs_csv_is_served(client):
    """pacs.html feeds this straight into Papa.parse."""
    res = client.get("/pacs2024.csv")
    assert res.status_code == 200
    assert res.data == (STATIC / "pacs2024.csv").read_bytes()


def test_unknown_page_is_a_404(client):
    assert client.get("/not-a-page").status_code == 404


def _paths_in(text):
    """Every quoted absolute path in a page: nav links and API endpoints alike.

    The `/tasks/${task_id}` template does not match (it has a JS placeholder in
    it) and is covered by its own test below.
    """
    return set(re.findall(r"""["'`](/[a-zA-Z0-9/_.-]*)["'`]""", text))


@pytest.mark.parametrize("page", PAGES)
def test_every_path_the_page_points_at_is_routable(client, epos_upstream, page):
    """A 404 here means a page has been orphaned by a routing change. API
    endpoints answer 400 without their query args, which still proves the route
    exists."""
    paths = _paths_in((STATIC / f"{page}.html").read_text())
    assert paths, f"expected to find linked paths in {page}.html"
    for path in sorted(paths):
        status = client.get(path).status_code
        assert status != 404, f"{page}.html points at {path}, which 404s"


def test_the_api_endpoints_the_frontend_uses_are_all_present(client):
    from app import app

    routes = {r.rule for r in app.url_map.iter_rules()}
    used = set()
    for page in STATIC.glob("*.html"):
        used.update(p for p in _paths_in(page.read_text()) if p.startswith("/get-"))
    assert used == {
        "/get-sales-details",
        "/get-rc-details",
        "/get-stock-details",
        "/get-kaimur-officers",
        "/get-collection-summary",
        "/get-epds-rc-details",
    }, "the set of endpoints the UI needs has changed"
    assert used <= routes


def test_task_polling_url_still_matches_the_frontend():
    """Every page that runs a crawl polls `/tasks/${task_id}`."""
    from app import app

    assert "/tasks/<task_id>" in {r.rule for r in app.url_map.iter_rules()}
    polling = sorted(
        p.name for p in STATIC.glob("*.html") if "/tasks/${task_id}" in p.read_text()
    )
    assert polling == [
        "collection.html",
        "index.html",
        "officers.html",
        "search.html",
        "stock.html",
    ]
