"""
Frontend Configuration
======================
Minimal config for the frontend Flask server.
The only critical value is BACKEND_URL — inject it via ConfigMap in K8s.
"""

import os


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class Config:
    PORT: int = int(_get("FRONTEND_PORT", "8080"))

    BACKEND_URL: str = _get("BACKEND_URL", "http://localhost:5000")

    APP_ENV: str     = _get("APP_ENV", "development")
    DEBUG: bool      = APP_ENV != "production"

    LOG_LEVEL: str   = _get("LOG_LEVEL", "INFO")
