"""
Backend — K8s-Ready Flask REST API
====================================
Pure JSON API. No HTML. Designed to run as a separate K8s Deployment.

Endpoints
---------
  GET  /              →  app identity
  GET  /health/live   →  liveness  probe  (K8s livenessProbe)
  GET  /health/ready  →  readiness probe  (K8s readinessProbe)
  GET  /info          →  redacted config dump (verify ConfigMap/Secret injection)
  GET  /metrics       →  lightweight metrics  (ENABLE_METRICS=true)
  GET  /debug         →  env dump, dev/staging only  (ENABLE_DEBUG_ROUTE=true)
"""

import logging
import socket
import sys
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_FORMATS = {
    "json": '{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    "text": "%(asctime)s  %(levelname)-8s  %(message)s",
}

logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, Config.log.LOG_LEVEL.upper(), logging.INFO),
    format=_LOG_FORMATS.get(Config.log.LOG_FORMAT, _LOG_FORMATS["text"]),
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_startup_time: float = time.time()
_ready: bool = False


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"]         = Config.security.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.app.MAX_CONTENT_LENGTH

    CORS(app, origins=Config.app.CORS_ORIGIN)

    # ── Request logging ──────────────────────────────────────────────────────

    @app.before_request
    def _log_request():
        logger.info("%s %s  [from %s]", request.method, request.path, request.remote_addr)

    # ── Home ─────────────────────────────────────────────────────────────────

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "application": Config.app.APP_NAME,
            "version":     Config.app.APP_VERSION,
            "environment": Config.app.APP_ENV,
            "message":     "API is running.",
            "timestamp":   _utc_now(),
        })

    # ── Liveness probe ───────────────────────────────────────────────────────
    # K8s restarts the pod only when this returns non-2xx.
    # Keep it cheap — just confirm the process is alive.

    @app.route("/health/live", methods=["GET"])
    def liveness():
        return jsonify({
            "status":         "alive",
            "uptime_seconds": round(time.time() - _startup_time, 2),
            "timestamp":      _utc_now(),
        }), 200

    # ── Readiness probe ──────────────────────────────────────────────────────
    # K8s stops sending traffic when this returns non-2xx.
    # Optionally TCP-checks READINESS_CHECK_HOST (e.g. DB service).

    @app.route("/health/ready", methods=["GET"])
    def readiness():
        global _ready
        checks: dict = {"self": "ok"}
        all_ok = True

        if Config.app.READINESS_CHECK_HOST:
            ok, detail = _tcp_reachable(
                Config.app.READINESS_CHECK_HOST,
                Config.app.READINESS_CHECK_PORT,
            )
            checks["upstream"] = "ok" if ok else f"unreachable — {detail}"
            if not ok:
                all_ok = False

        _ready = all_ok
        return jsonify({
            "status":    "ready" if all_ok else "not_ready",
            "checks":    checks,
            "timestamp": _utc_now(),
        }), (200 if all_ok else 503)

    # ── Config info ──────────────────────────────────────────────────────────
    # Call after deploy to confirm ConfigMap/Secret values were injected.

    @app.route("/info", methods=["GET"])
    def info():
        return jsonify({
            "config":    Config.as_dict(),
            "hostname":  socket.gethostname(),
            "timestamp": _utc_now(),
        })

    # ── Metrics ──────────────────────────────────────────────────────────────

    @app.route("/metrics", methods=["GET"])
    def metrics():
        if not Config.app.ENABLE_METRICS:
            return jsonify({"error": "metrics endpoint is disabled"}), 404
        return jsonify({
            "uptime_seconds": round(time.time() - _startup_time, 2),
            "app_name":       Config.app.APP_NAME,
            "app_version":    Config.app.APP_VERSION,
            "environment":    Config.app.APP_ENV,
            "ready":          _ready,
            "timestamp":      _utc_now(),
        })

    # ── Debug ────────────────────────────────────────────────────────────────

    @app.route("/debug", methods=["GET"])
    def debug_info():
        if not Config.app.ENABLE_DEBUG_ROUTE:
            return jsonify({"error": "debug route is disabled"}), 403
        if Config.app.APP_ENV == "production":
            return jsonify({"error": "debug route is not available in production"}), 403

        import os
        safe_env = {
            k: ("***" if any(s in k.upper() for s in ("SECRET", "PASSWORD", "KEY", "TOKEN")) else v)
            for k, v in os.environ.items()
        }
        return jsonify({
            "environment_variables": safe_env,
            "hostname":              socket.gethostname(),
            "timestamp":             _utc_now(),
        })

    # ── Error handlers ───────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found", "path": request.path}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled exception")
        return jsonify({"error": "internal server error"}), 500

    logger.info(
        "Backend '%s' v%s started  [env=%s  port=%d]",
        Config.app.APP_NAME, Config.app.APP_VERSION,
        Config.app.APP_ENV,  Config.app.APP_PORT,
    )
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tcp_reachable(host: str, port: int, timeout: int = 3) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except socket.timeout:
        return False, f"timed out after {timeout}s"
    except OSError as exc:
        return False, str(exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    application = create_app()
    application.run(
        host="0.0.0.0",
        port=Config.app.APP_PORT,
        debug=Config.app.DEBUG,
    )
