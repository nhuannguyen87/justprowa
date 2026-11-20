"""App settings, read from environment variables (or a .env file)."""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # General
    SITE_NAME = "Just Professional Services"
    SITE_URL = os.getenv("SITE_URL", "http://localhost:8000").rstrip("/")
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)  # set in production!
    DEBUG = _bool("DEBUG", False)
    # Set by build_static.py (GitHub Pages): no server, so forms are shown but switched off
    STATIC_SITE = _bool("STATIC_SITE", False)
    TIMEZONE = "Australia/Perth"

    # Database (SQLite by default; use postgresql+psycopg://... in production if wanted)
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'jps.db'}")

    # Uploaded photos/files from customers (kept private, served only to admins)
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "data" / "uploads"))
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
    MAX_FILES = int(os.getenv("MAX_FILES", "8"))
    ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".pdf", ".mp4", ".mov"}

    # Email (Gmail: smtp.gmail.com / 587 / app password). Leave SMTP_HOST empty to only log emails.
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM") or os.getenv("SMTP_USER", "")
    NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")  # where new requests are emailed; empty = no notification

    # Stripe (optional – payments stay switched off until STRIPE_SECRET_KEY is set)
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_BRONZE = os.getenv("STRIPE_PRICE_BRONZE", "")
    STRIPE_PRICE_SILVER = os.getenv("STRIPE_PRICE_SILVER", "")
    STRIPE_PRICE_GOLD = os.getenv("STRIPE_PRICE_GOLD", "")

    # Business details shown on the site
    BUSINESS = {
        "name": "Just Professional Services",
        "abn": "71 878 748 716",
        "phones": [("Ben", "0424 595 086"), ("Ash", "0473 634 321")],
        "area": "Perth metro, Western Australia",
    }


settings = Settings()
