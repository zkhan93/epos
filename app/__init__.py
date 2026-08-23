import logging
import os

from flask import Flask
from flask_cors import CORS


def init_app():
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.info("Log initialized !!")

    app = Flask(__name__)
    CORS(app)

    from . import core

    app.register_blueprint(core.bp)
    return app


app = init_app()
