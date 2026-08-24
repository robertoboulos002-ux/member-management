# Admin authentication: password check, signed session tokens, and the
# dependency that guards the member endpoints.
#
# Member records are personal data (names, parents, dates and places of birth),
# so the API must not serve them to anonymous callers. A gate that lived only
# in the frontend would be decoration - anyone could call /members directly -
# so the check belongs here, and every /members route depends on it.
#
# One shared password, no user accounts: the app has a single administrator.
# Environment variables read here (all optional except the first):
#   ADMIN_PASSWORD        - the admin password. Without it, nobody can log in.
#   ADMIN_SESSION_SECRET  - HMAC key for session tokens. Defaults to a value
#                           derived from ADMIN_PASSWORD, so changing the
#                           password also invalidates existing sessions.
#   ADMIN_SESSION_HOURS   - how long a session lasts. Default 12.

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

DEFAULT_SESSION_HOURS = 12

# Brute-forcing a single password is the obvious attack on a login with no
# username, so failures are throttled per client address.
MAX_FAILED_ATTEMPTS = 10
LOCKOUT_WINDOW_SECONDS = 15 * 60

# auto_error=False so a missing header produces our own 401 with the same
# wording as a wrong one - which header is absent is not the caller's business.
_bearer = HTTPBearer(auto_error=False)

# Per-process failure log: {client_ip: [timestamp, ...]}. Deliberately in
# memory - it costs nothing and needs no schema. On a multi-worker or
# multi-instance deployment each process throttles separately, which weakens
# the limit but never blocks a legitimate login; a shared store (Redis) would
# be the fix if that ever matters.
_failed_attempts: dict[str, list[float]] = {}


class AdminAuthNotConfigured(Exception):
    """Raised when ADMIN_PASSWORD is unset, so no login can succeed."""


def get_admin_password() -> Optional[str]:
    """Return the configured admin password, or None if there isn't one."""
    password = os.getenv("ADMIN_PASSWORD")
    return password if password else None


def get_session_secret() -> bytes:
    """Return the HMAC key used to sign session tokens.

    Falls back to a key derived from the password so a deployment needs only
    ADMIN_PASSWORD set to work. The derivation is one-way, so a token never
    leaks the password, and rotating the password invalidates every token.
    """
    configured = os.getenv("ADMIN_SESSION_SECRET")
    if configured:
        return configured.encode("utf-8")

    password = get_admin_password()
    if password is None:
        raise AdminAuthNotConfigured

    seed = f"member-management:session:{password}".encode("utf-8")
    return hashlib.sha256(seed).digest()


def get_session_seconds() -> int:
    """Session lifetime in seconds, from ADMIN_SESSION_HOURS."""
    raw = os.getenv("ADMIN_SESSION_HOURS")
    try:
        hours = float(raw) if raw else DEFAULT_SESSION_HOURS
    except ValueError:
        hours = DEFAULT_SESSION_HOURS

    if hours <= 0:
        hours = DEFAULT_SESSION_HOURS

    return int(hours * 3600)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(body: str) -> str:
    digest = hmac.new(get_session_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_token() -> tuple[str, int]:
    """Mint a signed session token. Returns (token, expiry as a unix time).

    The token carries only its own expiry - there is nothing else to say about
    a single-administrator session, and no personal data belongs in something
    the browser stores.
    """
    now = int(time.time())
    expires_at = now + get_session_seconds()

    claims = json.dumps({"iat": now, "exp": expires_at}, separators=(",", ":"))
    body = _b64url_encode(claims.encode("utf-8"))
    return f"{body}.{_sign(body)}", expires_at


def verify_token(token: str) -> int:
    """Return the token's expiry if it is validly signed and unexpired.

    Raises ValueError otherwise. Every failure looks the same to the caller:
    a malformed token and a forged one are both simply not valid.
    """
    body, separator, signature = token.partition(".")
    if not separator or not body or not signature:
        raise ValueError("malformed token")

    # compare_digest, not ==, so the comparison time does not reveal how much
    # of a guessed signature was correct.
    if not hmac.compare_digest(signature, _sign(body)):
        raise ValueError("bad signature")

    try:
        payload = json.loads(_b64url_decode(body))
        expires_at = int(payload["exp"])
    except (ValueError, KeyError, TypeError):
        raise ValueError("malformed payload")

    if expires_at <= int(time.time()):
        raise ValueError("expired")

    return expires_at


def client_key(request: Request) -> str:
    """Identify the caller for throttling purposes."""
    # Render and most hosts put the real address first in X-Forwarded-For; the
    # direct peer address is every caller behind a proxy, which would throttle
    # them all as one. Neither is spoof-proof, but this is a speed bump.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def _recent_failures(key: str, now: float) -> list[float]:
    attempts = [
        stamp for stamp in _failed_attempts.get(key, [])
        if now - stamp < LOCKOUT_WINDOW_SECONDS
    ]
    if attempts:
        _failed_attempts[key] = attempts
    else:
        _failed_attempts.pop(key, None)
    return attempts


def is_locked_out(key: str) -> bool:
    """True when this caller has failed too many times too recently."""
    return len(_recent_failures(key, time.time())) >= MAX_FAILED_ATTEMPTS


def record_failure(key: str) -> None:
    """Log a failed attempt against this caller."""
    now = time.time()
    _failed_attempts[key] = _recent_failures(key, now) + [now]


def clear_failures(key: str) -> None:
    """Forget a caller's failures - called on a successful login."""
    _failed_attempts.pop(key, None)


def reset_throttle() -> None:
    """Drop all recorded failures. For tests and local troubleshooting."""
    _failed_attempts.clear()


def check_password(candidate: str) -> bool:
    """Constant-time comparison against the configured admin password."""
    password = get_admin_password()
    if password is None:
        raise AdminAuthNotConfigured

    return secrets.compare_digest(candidate, password)


UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    """Dependency that rejects any request without a valid session token.

    Answers 401 for a missing, malformed, expired or forged token alike, and
    also when no password is configured at all - a caller learns only that it
    is not authenticated, never why.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UNAUTHORIZED

    try:
        verify_token(credentials.credentials)
    except (ValueError, AdminAuthNotConfigured):
        raise UNAUTHORIZED
