"""The thread pool that replaced Celery."""

import threading
import time

import pytest

import tasks


def test_plain_call_and_run_still_work():
    """collection.py calls other tasks with .run(), and epos.py calls them
    directly, so a task has to stay an ordinary function too."""

    @tasks.task(name="add")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5
    assert add.run(2, 3) == 5
    assert add.name == "add"


def test_delay_runs_in_the_background_and_reports_success():
    @tasks.task(name="slow")
    def slow():
        time.sleep(0.05)
        return {"ok": True}

    task_id = slow.delay()
    assert isinstance(task_id, str)
    assert tasks.get_status(task_id)["status"] in ("PENDING", "STARTED")

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        body = tasks.get_status(task_id)
        if body["status"] == "SUCCESS":
            break
        time.sleep(0.01)
    assert body["status"] == "SUCCESS"
    assert body["result"] == {"ok": True}
    assert body["id"] == task_id


def test_failure_keeps_the_shape_the_frontend_reads():
    @tasks.task(name="boom")
    def boom():
        raise ValueError("no records found")

    task_id = boom.delay()
    body = _wait(task_id)
    assert body["status"] == "FAILURE"
    # index.html reads result.error and result.traceback.
    assert body["result"]["error"] == "no records found"
    assert "ValueError" in body["result"]["traceback"]


def test_identical_calls_share_one_run():
    gate = threading.Event()
    runs = []

    @tasks.task(name="counted")
    def counted(x=1):
        runs.append(x)
        gate.wait(5)
        return x

    first = counted.delay(x=1)
    second = counted.delay(x=1)
    third = counted.delay(x=2)
    try:
        assert first == second, "same arguments while in flight reuse the task"
        assert third != first, "different arguments get their own task"
    finally:
        gate.set()

    _wait(first)
    _wait(third)
    assert sorted(runs) == [1, 2], "the duplicate never hit the network"


def test_a_finished_task_is_not_deduped_into_forever():
    @tasks.task(name="quick")
    def quick():
        return 1

    first = quick.delay()
    _wait(first)
    second = quick.delay()
    assert second != first, "a finished result must not pin the dedupe key"
    _wait(second)


def test_unknown_id_reads_as_pending():
    """A browser tab that outlived a restart should keep polling, not error."""
    body = tasks.get_status("does-not-exist")
    assert body == {"id": "does-not-exist", "status": "PENDING", "result": None}


def test_queue_full_is_refused_rather_than_piling_up(monkeypatch):
    monkeypatch.setattr(tasks, "MAX_QUEUED", 2)
    gate = threading.Event()

    @tasks.task(name="blocked")
    def blocked(n=0):
        gate.wait(5)
        return n

    try:
        blocked.delay(n=1)
        blocked.delay(n=2)
        with pytest.raises(tasks.TaskQueueFull):
            blocked.delay(n=3)
    finally:
        gate.set()


def test_finished_results_are_capped(monkeypatch):
    monkeypatch.setattr(tasks, "MAX_RESULTS", 3)

    @tasks.task(name="tiny")
    def tiny(n=0):
        return n

    ids = []
    for n in range(8):
        task_id = tiny.delay(n=n)
        ids.append(task_id)
        _wait(task_id)

    tiny.delay(n=99)  # triggers a prune
    stored = len(tasks._registry._entries)
    assert stored <= 4, f"registry grew to {stored} entries"
    # The newest result must still be readable -- that is the one being polled.
    assert tasks.get_status(ids[-1])["status"] == "SUCCESS"


def _wait(task_id, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = tasks.get_status(task_id)
        if body["status"] in ("SUCCESS", "FAILURE"):
            return body
        time.sleep(0.01)
    raise AssertionError(f"task {task_id} never finished")
