import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=False)


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return default


def _list(name: str, default: str) -> list[str]:
    return [v.strip().rstrip("/") for v in (os.getenv(name) or default).split(",") if v.strip()]


def _str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class Settings:
    app_env: str = _str("APP_ENV", "development")
    secret_key: str = _str("SECRET_KEY", "dev-insecure-secret-key")
    access_token_expire_minutes: int = _int("ACCESS_TOKEN_EXPIRE_MINUTES", 720)
    frontend_origins: list[str] = field(
        default_factory=lambda: _list(
            "FRONTEND_ORIGINS",
            "http://localhost:5173,https://movpick.netlify.app,https://movpick.onrender.com,https://fsclass-n.github.io",
        )
    )
    frontend_url: str = _str("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    backend_url: str = _str("BACKEND_URL", "http://localhost:8000").rstrip("/")

    database_url: str = _str("DATABASE_URL")
    tidb_host: str = _str("TIDB_HOST")
    tidb_port: int = _int("TIDB_PORT", 4000)
    tidb_user: str = _str("TIDB_USER")
    tidb_password: str = _str("TIDB_PASSWORD")
    tidb_db_name: str = _str("TIDB_DB_NAME", "movpick")
    tidb_ssl_ca: str = _str("TIDB_SSL_CA")

    google_client_id: str = _str("GOOGLE_CLIENT_ID")
    google_client_secret: str = _str("GOOGLE_CLIENT_SECRET")
    naver_client_id: str = _str("NAVER_CLIENT_ID")
    naver_client_secret: str = _str("NAVER_CLIENT_SECRET")
    kakao_client_id: str = _str("KAKAO_CLIENT_ID")
    kakao_client_secret: str = _str("KAKAO_CLIENT_SECRET")

    demo_login_enabled: bool = _bool("DEMO_LOGIN_ENABLED", True)
    admin_email: str = _str("ADMIN_EMAIL")
    admin_password: str = _str("ADMIN_PASSWORD")
    admin_name: str = _str("ADMIN_NAME", "관리자")

    rpa_enabled: bool = _bool("RPA_ENABLED", True)
    rpa_mode: str = _str("RPA_MODE", "auto").lower()
    rpa_headless: bool = _bool("RPA_HEADLESS", True)
    rpa_timeout_seconds: int = _int("RPA_TIMEOUT_SECONDS", 20)
    crawl_interval_minutes: int = _int("CRAWL_INTERVAL_MINUTES", 30)
    seat_monitor_interval_seconds: int = _int("SEAT_MONITOR_INTERVAL_SECONDS", 20)
    seat_simulation: bool = _bool("SEAT_SIMULATION", True)
    rpa_proxy_url: str = _str("RPA_PROXY_URL")
    rpa_ingest_token: str = _str("RPA_INGEST_TOKEN")
    rpa_remote_chains: list[str] = field(default_factory=lambda: [c.lower() for c in _list("RPA_REMOTE_CHAINS", "")])
    rpa_mock_chains: list[str] = field(default_factory=lambda: [c.lower() for c in _list("RPA_MOCK_CHAINS", "")])
    rpa_real_ttl_minutes: int = _int("RPA_REAL_TTL_MINUTES", 180)

    telegram_bot_token: str = _str("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = _str("TELEGRAM_CHAT_ID")
    discord_webhook_url: str = _str("DISCORD_WEBHOOK_URL")
    smtp_host: str = _str("SMTP_HOST")
    smtp_port: int = _int("SMTP_PORT", 587)
    smtp_user: str = _str("SMTP_USER")
    smtp_password: str = _str("SMTP_PASSWORD")
    smtp_from: str = _str("SMTP_FROM")


settings = Settings()
