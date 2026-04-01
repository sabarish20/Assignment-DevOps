"""
Backend Configuration
=====================
All values are driven by environment variables.

  ConfigMap  →  non-sensitive runtime config (APP_NAME, APP_ENV, DB_HOST …)
  Secret     →  sensitive values (DB_PASSWORD, SECRET_KEY, API_KEY)
  Env Vars   →  surfaced via envFrom / env in the K8s Pod spec
"""

import os


def _get(key: str, default: str = "", required: bool = False) -> str:
    value = os.environ.get(key, default)
    if required and not value:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value


# ---------------------------------------------------------------------------
# Application  (ConfigMap)
# ---------------------------------------------------------------------------

class AppConfig:
    APP_NAME: str    = _get("APP_NAME",    "devops-app")
    APP_ENV: str     = _get("APP_ENV",     "development")  # development | staging | production
    APP_VERSION: str = _get("APP_VERSION", "1.0.0")
    APP_PORT: int    = int(_get("APP_PORT", "5000"))
    DEBUG: bool      = _get("APP_ENV", "development") != "production"

    # CORS — frontend origin allowed to call this API
    CORS_ORIGIN: str = _get("CORS_ORIGIN", "*")

    # Feature flags
    ENABLE_METRICS: bool     = _get("ENABLE_METRICS",     "true").lower()  == "true"
    ENABLE_DEBUG_ROUTE: bool = _get("ENABLE_DEBUG_ROUTE", "false").lower() == "true"

    # Readiness check — upstream host:port to TCP-probe (e.g. DB)
    READINESS_CHECK_HOST: str = _get("READINESS_CHECK_HOST", "")
    READINESS_CHECK_PORT: int = int(_get("READINESS_CHECK_PORT", "80"))

    # Tuning
    REQUEST_TIMEOUT: int    = int(_get("REQUEST_TIMEOUT",    "30"))
    MAX_CONTENT_LENGTH: int = int(_get("MAX_CONTENT_LENGTH", str(16 * 1024 * 1024)))


# ---------------------------------------------------------------------------
# Database  (host/name/user → ConfigMap  |  password → Secret)
# ---------------------------------------------------------------------------

class DatabaseConfig:
    DB_HOST: str     = _get("DB_HOST", "localhost")
    DB_PORT: int     = int(_get("DB_PORT", "5432"))
    DB_NAME: str     = _get("DB_NAME", "appdb")
    DB_USER: str     = _get("DB_USER", "appuser")
    DB_PASSWORD: str = _get("DB_PASSWORD", "", required=False)   # Secret

    @classmethod
    def connection_string(cls) -> str:
        return (
            f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )


# ---------------------------------------------------------------------------
# Security  (Secret / Sealed Secret)
# ---------------------------------------------------------------------------

class SecurityConfig:
    SECRET_KEY: str = _get("SECRET_KEY", "change-me-in-production", required=False)
    API_KEY: str    = _get("API_KEY",    "", required=False)
    JWT_SECRET: str = _get("JWT_SECRET", "", required=False)


# ---------------------------------------------------------------------------
# Logging  (ConfigMap)
# ---------------------------------------------------------------------------

class LogConfig:
    LOG_LEVEL: str  = _get("LOG_LEVEL",  "INFO")   # DEBUG | INFO | WARNING | ERROR
    LOG_FORMAT: str = _get("LOG_FORMAT", "json")    # json | text


# ---------------------------------------------------------------------------
# Aggregated
# ---------------------------------------------------------------------------

class Config:
    app      = AppConfig
    db       = DatabaseConfig
    security = SecurityConfig
    log      = LogConfig

    @classmethod
    def as_dict(cls) -> dict:
        """Return a safe (redacted) snapshot — safe to expose via /info."""
        return {
            "app": {
                "name":                 cls.app.APP_NAME,
                "env":                  cls.app.APP_ENV,
                "version":              cls.app.APP_VERSION,
                "port":                 cls.app.APP_PORT,
                "debug":                cls.app.DEBUG,
                "cors_origin":          cls.app.CORS_ORIGIN,
                "enable_metrics":       cls.app.ENABLE_METRICS,
                "enable_debug_route":   cls.app.ENABLE_DEBUG_ROUTE,
                "request_timeout":      cls.app.REQUEST_TIMEOUT,
                "readiness_check_host": cls.app.READINESS_CHECK_HOST,
                "readiness_check_port": cls.app.READINESS_CHECK_PORT,
            },
            "database": {
                "host":     cls.db.DB_HOST,
                "port":     cls.db.DB_PORT,
                "name":     cls.db.DB_NAME,
                "user":     cls.db.DB_USER,
                "password": "***REDACTED***",
            },
            "security": {
                "secret_key": "***REDACTED***",
                "api_key":    "***REDACTED***" if cls.security.API_KEY    else "(not set)",
                "jwt_secret": "***REDACTED***" if cls.security.JWT_SECRET else "(not set)",
            },
            "log": {
                "level":  cls.log.LOG_LEVEL,
                "format": cls.log.LOG_FORMAT,
            },
        }
