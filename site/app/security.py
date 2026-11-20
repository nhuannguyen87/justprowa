"""Password hashing (stdlib PBKDF2), admin session helpers and CSRF tokens."""
import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

ITERATIONS = 390_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
    except ValueError:
        return False
    test = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters)).hex()
    return hmac.compare_digest(test, digest)


def csrf_token(request: Request) -> str:
    tok = request.session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(24)
        request.session["csrf"] = tok
    return tok


def check_csrf(request: Request, token: str) -> None:
    if not token or not hmac.compare_digest(token, request.session.get("csrf", "")):
        raise HTTPException(status_code=400, detail="Form expired – please go back, refresh and try again.")


def current_admin(request: Request) -> str | None:
    return request.session.get("admin")


class AdminRequired(Exception):
    """Raised when an admin page is opened without logging in (redirects to login)."""
