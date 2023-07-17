from flask_cors import CORS
from flask import Flask
import logging

from utils import create_celery, init_celery


def init_app():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logging.info("Log initialized !!")

    app = Flask(__name__)
    CORS(app)
    celery = create_celery()
    celery = init_celery(celery, app)
    from . import core

    app.register_blueprint(core.bp)
    return app, celery


app, celery = init_app()
