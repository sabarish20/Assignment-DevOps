"""
Frontend — Flask Template Server
==================================
Serves the single-page dashboard (index.html) and injects
the backend API URL so the browser knows where to fetch data from.

The frontend and backend are fully decoupled:
  - This server owns zero business logic.
  - All data comes from the backend API via browser-side fetch() calls.
  - BACKEND_URL is the only coupling point — supplied by a K8s ConfigMap.
"""

import logging
import sys

from flask import Flask, render_template

from config import Config

logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    @app.route("/<path:_>", methods=["GET"])
    def index(_=None):
        return render_template(
            "index.html",
            backend_url=Config.BACKEND_URL,
            app_env=Config.APP_ENV,
        )

    logger.info(
        "Frontend started  [env=%s  port=%d  backend=%s]",
        Config.APP_ENV, Config.PORT, Config.BACKEND_URL,
    )
    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
