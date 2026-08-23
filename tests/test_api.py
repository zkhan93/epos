"""End to end through the real Flask app: submit a job, poll it the way the
browser does, check the payload. The upstream site is stubbed, nothing else is."""

from conftest import EPOS_RC, EPOS_SALES, FakeResponse, fixture, poll


def submit(client, path, **params):
    res = client.get(path, query_string=params)
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert list(body) == ["task_id"], "the frontend reads exactly data.task_id"
    return body["task_id"]


def test_healthz():
    from app import app

    res = app.test_client().get("/healthz")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_task_status_response_shape(client, epos_upstream):
    task_id = submit(
        client, "/get-stock-details", fpsid="123300100909", month="3", year="2022",
        dist_code="233",
    )
    body = poll(client, task_id)
    assert set(body) == {"id", "status", "result", "_seen"}
    assert body["status"] == "SUCCESS"


def test_stock_details(client, epos_upstream):
    task_id = submit(
        client, "/get-stock-details", fpsid="123300100909", month="3", year="2022",
        dist_code="233",
    )
    result = poll(client, task_id)["result"]
    assert len(result) == 2
    assert result[0]["Commodity"] == "Wheat"


def test_rc_details(client, epos_upstream):
    task_id = submit(
        client, "/get-rc-details", rcnumber="10310060087015900034", month="3",
        year="2022",
    )
    result = poll(client, task_id)["result"]
    assert len(result["members"]) == 3
    assert result["transactions"][0]["Member"] == "Devanti Devi"


def test_rc_details_second_request_is_served_from_cache(client, epos_upstream):
    params = dict(rcnumber="10310060087015900034", month="3", year="2022")
    poll(client, submit(client, "/get-rc-details", **params))
    assert len(epos_upstream.calls_to(EPOS_RC)) == 1
    poll(client, submit(client, "/get-rc-details", **params))
    assert len(epos_upstream.calls_to(EPOS_RC)) == 1, "cache hit, no second fetch"


def test_rc_details_cache_false_refetches(client, epos_upstream):
    params = dict(rcnumber="10310060087015900034", month="3", year="2022")
    poll(client, submit(client, "/get-rc-details", **params))
    poll(client, submit(client, "/get-rc-details", cache="false", **params))
    assert len(epos_upstream.calls_to(EPOS_RC)) == 2


def test_sales_details_fans_out_to_rc_details(client, epos_upstream):
    task_id = submit(
        client, "/get-sales-details", fpsid="123300100909", month="3", year="2022",
        dist_code="233",
    )
    items = poll(client, task_id)["result"]
    assert len(items) == 3
    # Each sale gets the enriched block index.html renders in the modal.
    assert items[0]["extra"] == {
        "name": "Devanti Devi",
        "total": 3,
        "seeded": 2,
        "members": items[0]["extra"]["members"],
    }
    assert len(items[0]["extra"]["members"]) == 3
    assert len(epos_upstream.calls_to(EPOS_SALES)) == 1
    assert len(epos_upstream.calls_to(EPOS_RC)) == 3, "one per distinct RC number"


def test_collection_summary(client, epos_upstream):
    task_id = submit(
        client, "/get-collection-summary", fpsid="123300100909", month="3",
        year="2022", dist_code="233",
    )
    summaries = poll(client, task_id)["result"]
    by_date = {s["date"]: s for s in summaries}
    assert set(by_date) == {"05-03-2022", "06-03-2022"}
    # Two cards on the 5th, each with 2 seeded members.
    assert by_date["05-03-2022"]["cards"] == 2
    assert by_date["05-03-2022"]["units"] == 4
    assert by_date["05-03-2022"]["min"] == 64
    assert by_date["06-03-2022"]["cards"] == 1


def test_epds_rc_details(client, epos_upstream):
    task_id = submit(
        client, "/get-epds-rc-details", rcnumber="10310060087015900034",
        dist_code="233",
    )
    result = poll(client, task_id)["result"]
    assert len(result["members"]) == 2
    assert result["Scheme"] == "PHH"
    assert result["Message"] == "* Ration Card Found...!"


def test_kaimur_officers(client, epos_upstream):
    task_id = submit(client, "/get-kaimur-officers")
    officers = poll(client, task_id)["result"]
    assert officers, "one entry per officer type"
    assert {o["Type"] for o in officers}, "each officer is tagged with its type"


def test_upstream_failure_surfaces_as_a_failed_task(client, upstream):
    upstream.route(EPOS_RC, FakeResponse(text="", status_code=503))
    task_id = submit(
        client, "/get-rc-details", rcnumber="1031", month="3", year="2022",
    )
    body = poll(client, task_id)
    assert body["status"] == "FAILURE"
    assert "upstream request" in body["result"]["error"]
    assert body["result"]["traceback"]


def test_no_records_surfaces_as_a_failed_task(client, upstream):
    upstream.route(EPOS_SALES, FakeResponse(text="<html><body></body></html>"))
    task_id = submit(
        client, "/get-sales-details", fpsid="1", month="3", year="2022", dist_code="233",
    )
    body = poll(client, task_id)
    assert body["status"] == "FAILURE"
    assert body["result"]["error"]


def test_missing_query_arg_is_a_400_not_a_500(client, epos_upstream):
    res = client.get("/get-rc-details")
    assert res.status_code == 400


def test_duplicate_submits_share_one_task(client, epos_upstream):
    """Two tabs, or an impatient refresh, must not double the load upstream."""
    params = dict(
        fpsid="123300100909", month="3", year="2022", dist_code="233",
    )
    first = submit(client, "/get-stock-details", **params)
    poll(client, first)
    assert len(epos_upstream.calls_to("fps_stock_register")) == 1
