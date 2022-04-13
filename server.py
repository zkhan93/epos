import traceback
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import crawler
import logging
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logging.info("Log initialized !!")

app = Flask("app")
CORS(app)


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/get-sales-details")
def get_sales_details():
    logging.info("api request")
    # for shahina parveen
    # fpsid=123300100909, month=3, year=2022, dist_code=233
    fpsid = request.args["fpsid"]
    month = request.args["month"]
    year = request.args["year"]
    dist_code = request.args["dist_code"]
    try:
        items = crawler.get_sales_details(
            fpsid=fpsid, month=month, year=year, dist_code=dist_code
        )
        return jsonify(items)
    except Exception as ex:
        logging.exception("failed to get data")
        _, _, exc_traceback = sys.exc_info()
        return (
            jsonify(
                dict(
                    error=str(ex),
                    traceback=traceback.format_tb(exc_traceback),
                )
            ),
            400,
        )
