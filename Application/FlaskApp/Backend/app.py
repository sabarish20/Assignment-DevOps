import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config

logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, Config.log.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

_startup_time: float = time.time()

_todos: dict = {}


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins=Config.app.CORS_ORIGIN)

    @app.before_request
    def _log_request():
        logger.info("%s %s  [from %s]", request.method, request.path, request.remote_addr)


    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "application": Config.app.APP_NAME,
            "environment": Config.app.APP_ENV,
            "message":     "TODO API is running.",
            "timestamp":   _utc_now(),
        })


    @app.route("/health/live", methods=["GET"])
    def liveness():
        return jsonify({
            "status":         "alive",
            "uptime_seconds": round(time.time() - _startup_time, 2),
            "timestamp":      _utc_now(),
        }), 200

    @app.route("/health/ready", methods=["GET"])
    def readiness():
        return jsonify({
            "status":    "ready",
            "checks":    {"self": "ok"},
            "timestamp": _utc_now(),
        }), 200


    @app.route("/todos", methods=["GET"])
    def list_todos():
        todos = sorted(_todos.values(), key=lambda t: t["created_at"])
        return jsonify(todos), 200

    @app.route("/todos", methods=["POST"])
    def create_todo():
        body = request.get_json(silent=True) or {}
        text = (body.get("text") or "").strip()
        if not text:
            return jsonify({"error": "text is required"}), 400
        todo = {
            "id":         str(uuid.uuid4()),
            "text":       text,
            "completed":  False,
            "created_at": _utc_now(),
        }
        _todos[todo["id"]] = todo
        logger.info("Created todo %s: %s", todo["id"], text)
        return jsonify(todo), 201

    @app.route("/todos/<string:todo_id>", methods=["PUT"])
    def update_todo(todo_id: str):
        todo = _todos.get(todo_id)
        if not todo:
            return jsonify({"error": "todo not found"}), 404
        body = request.get_json(silent=True) or {}
        if "text" in body:
            text = (body["text"] or "").strip()
            if not text:
                return jsonify({"error": "text cannot be empty"}), 400
            todo["text"] = text
        if "completed" in body:
            todo["completed"] = bool(body["completed"])
        return jsonify(todo), 200

    @app.route("/todos/<string:todo_id>", methods=["DELETE"])
    def delete_todo(todo_id: str):
        if todo_id not in _todos:
            return jsonify({"error": "todo not found"}), 404
        del _todos[todo_id]
        logger.info("Deleted todo %s", todo_id)
        return jsonify({"deleted": todo_id}), 200


    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found", "path": request.path}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled exception")
        return jsonify({"error": "internal server error"}), 500

    logger.info(
        "Backend '%s' started  [env=%s  port=%d]",
        Config.app.APP_NAME, Config.app.APP_ENV, Config.app.APP_PORT,
    )
    return app


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=Config.app.APP_PORT, debug=Config.app.DEBUG)
