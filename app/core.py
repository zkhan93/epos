import logging
import sys
import traceback

from flask import Blueprint, jsonify, request

import crawler.epos as epos
import crawler.epos.collection as collection
import crawler.kaimur_officer as kaimur_officer
import tasks

bp = Blueprint("core", __name__, url_prefix="", static_folder="../static")


def error_response():
    _, ex, exc_traceback = sys.exc_info()
    return (
        jsonify(
            dict(
                error=str(ex),
                traceback=traceback.format_tb(exc_traceback),
            )
        ),
        400,
    )


def start(task, **kwargs):
    """Queue a crawl and answer with its id -- the shape the frontend polls on."""
    try:
        task_id = task.delay(**kwargs)
    except tasks.TaskQueueFull:
        logging.warning("rejecting %s: queue full", task.name)
        return jsonify(dict(error="server busy, try again in a moment")), 503
    except Exception:
        logging.exception("failed to queue %s", task.name)
        return error_response()
    return jsonify(dict(task_id=task_id))


@bp.route("/healthz")
def healthz():
    return jsonify(dict(status="ok"))


@bp.route("/")
@bp.route("/<file>")
def index(file="index"):
    if file.endswith(".csv"):
        return bp.send_static_file(file)
    return bp.send_static_file(f"{file}.html")


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    return jsonify(tasks.get_status(task_id))


@bp.route("/get-sales-details")
def get_sales_details():
    logging.info("api request")
    return start(
        epos.get_sales_details,
        fpsid=request.args["fpsid"],
        month=request.args["month"],
        year=request.args["year"],
        dist_code=request.args["dist_code"],
    )


@bp.route("/get-rc-details")
def get_rc_details():
    logging.info("api request")
    return start(
        epos.get_rc_details,
        rc_number=request.args["rcnumber"],
        month=request.args["month"],
        year=request.args["year"],
        use_cache=request.args.get("cache", "true").lower() == "true",
    )


@bp.route("/get-stock-details")
def get_stock_details():
    logging.info("api request")
    return start(
        epos.get_stock_details,
        fpsid=request.args["fpsid"],
        month=request.args["month"],
        year=request.args["year"],
        dist_code=request.args["dist_code"],
    )


@bp.route("/get-kaimur-officers")
def get_kaimur_officers():
    return start(kaimur_officer.get_officers)


@bp.route("/get-collection-summary")
def get_collection_summary():
    return start(
        collection.get_summary,
        fpsid=request.args["fpsid"],
        dist_code=request.args["dist_code"],
        year=request.args["year"],
        month=request.args["month"],
    )


@bp.route("/get-epds-rc-details")
def get_epds_rc_details():
    return start(
        epos.get_rc_details_from_epds,
        rc_number=request.args["rcnumber"],
        dist_code=request.args["dist_code"],
        use_cache=request.args.get("cache", "true").lower() == "true",
    )
