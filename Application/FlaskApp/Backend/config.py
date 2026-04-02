import os


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class AppConfig:
    APP_NAME: str    = _get("APP_NAME", "todo-app")
    APP_ENV: str     = _get("APP_ENV",  "development")
    APP_PORT: int    = int(_get("APP_PORT", "5000"))
    DEBUG: bool      = _get("APP_ENV", "development") != "production"
    CORS_ORIGIN: str = _get("CORS_ORIGIN", "*")


class LogConfig:
    LOG_LEVEL: str = _get("LOG_LEVEL", "INFO")


class Config:
    app = AppConfig
    log = LogConfig
