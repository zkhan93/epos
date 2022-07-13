import traceback
import sys
import logging
from flask import jsonify, request
import crawler.epos as epos
import crawler.epos.collection as collection
import crawler.kaimur_officer as kaimur_officer
from flask import Blueprint
from utils import create_celery, init_celery

# from app import app, celery

bp = Blueprint("core", __name__, url_prefix="", static_folder="../static")
celery = create_celery()
celery = init_celery(celery, bp)


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


@bp.route("/")
@bp.route("/<file>")
def index(file="index"):
    return bp.send_static_file(f"{file}.html")


@bp.route("/tasks/<task_id>", methods=["GET"])
def get_status(task_id):
    task_result = celery.AsyncResult(task_id)
    result = task_result.result

    if task_result.failed():

        result = {
            "error": str(task_result.result),
            "traceback": task_result.traceback,
        }
    return jsonify(
        {
            "id": task_id,
            "status": task_result.status,
            "result": result,
        }
    )


@bp.route("/get-sales-details")
def get_sales_details():
    logging.info("api request")
    # for shahina parveen
    # fpsid=123300100909, month=3, year=2022, dist_code=233
    fpsid = request.args["fpsid"]
    month = request.args["month"]
    year = request.args["year"]
    dist_code = request.args["dist_code"]
    try:
        task = epos.get_sales_details.delay(
            fpsid=fpsid, month=month, year=year, dist_code=dist_code
        )
        return jsonify({"task_id": task.id})
    except Exception:
        logging.exception("failed to get data")
        return error_response()


@bp.route("/get-rc-details")
def get_rc_details():
    logging.info("api request")
    # for Ramkut singh
    # rcnumber=10310060087015900034, month=3, year=2022
    rc_number = request.args["rcnumber"]
    month = request.args["month"]
    year = request.args["year"]
    cache = request.args.get("cache", "true").lower() == "true"
    try:
        task = epos.get_rc_details.delay(
            rc_number=rc_number, month=month, year=year, cache=cache
        )
        return jsonify(dict(task_id=task.id))
    except Exception:
        logging.exception("failed to get data")
        return error_response()


@bp.route("/get-stock-details")
def get_stock_details():
    logging.info("api request")
    # for shahina parveen
    # fpsid=123300100909, month=3, year=2022, dist_code=233
    fpsid = request.args["fpsid"]
    month = request.args["month"]
    year = request.args["year"]
    dist_code = request.args["dist_code"]
    try:
        task = epos.get_stock_details.delay(
            fpsid=fpsid, month=month, year=year, dist_code=dist_code
        )
        return jsonify(dict(task_id=task.id))
    except Exception:
        logging.exception("failed to get data")
        return error_response()


@bp.route("/get-kaimur-officers")
def get_kaimur_officers():
    task = kaimur_officer.get_officers.delay()
    return jsonify(dict(task_id=task.id))


@bp.route("/get-collection-summary")
def get_collection_summary():
    fpsid = request.args["fpsid"]
    dist_code = request.args["dist_code"]
    year = request.args["year"]
    month = request.args["month"]
    task = collection.get_summary.delay(
        fpsid=fpsid, dist_code=dist_code, year=year, month=month
    )
    return jsonify(dict(task_id=task.id))


@bp.route("/get-epds-rc-details")
def get_epds_rc_details():
    rc_number = request.args["rcnumber"]
    dist_code = request.args["dist_code"]
    cache = request.args.get("cache", "true").lower() == "true"
    try:
        task = epos.get_rc_details_from_epds.delay(
            rc_number=rc_number, dist_code=dist_code, cache=cache
        )
    except Exception as ex:
        logging.exception("failed to get data")
        return error_response()
    else:
        return jsonify(dict(task_id=task.id))
