# Tests for admin login and the gate in front of the member endpoints.
#
# The point of these is that the gate is real: no token, a tampered token or an
# expired one must all be refused by the API itself, not merely by the frontend.

import json
import time

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.auth import issue_token, verify_token
from app.main import app
from tests.conftest import TEST_ADMIN_PASSWORD

# No default Authorization header: these tests decide per request whether to
# send one.
client = TestClient(app)

MEMBER_REQUESTS = [
    ("get", "/members"),
    ("get", "/members/1"),
    ("post", "/members"),
    ("put", "/members/1"),
    ("delete", "/members/1"),
]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---- Login ----


def test_login_with_correct_password_returns_a_token():
    response = client.post("/auth/login", json={"password": TEST_ADMIN_PASSWORD})
    assert response.status_code == 200

    data = response.json()
    assert data["token"]
    assert data["expires_at"] > time.time()
    # The password must never come back in the response.
    assert TEST_ADMIN_PASSWORD not in response.text


def test_login_with_wrong_password_returns_401():
    response = client.post("/auth/login", json={"password": "not-the-password"})
    assert response.status_code == 401
    assert "token" not in response.json()


def test_login_with_blank_password_is_rejected():
    response = client.post("/auth/login", json={"password": ""})
    assert response.status_code == 422


def test_login_without_a_configured_password_returns_503(monkeypatch):
    """A deployment that forgot ADMIN_PASSWORD lets nobody in."""
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_SESSION_SECRET", raising=False)

    response = client.post("/auth/login", json={"password": "anything"})
    assert response.status_code == 503


def test_repeated_failures_are_throttled():
    for _ in range(auth.MAX_FAILED_ATTEMPTS):
        assert client.post("/auth/login", json={"password": "wrong"}).status_code == 401

    # Further attempts are refused outright - including the correct password,
    # so a lockout cannot be probed for a hit.
    assert client.post("/auth/login", json={"password": "wrong"}).status_code == 429
    assert client.post("/auth/login", json={"password": TEST_ADMIN_PASSWORD}).status_code == 429


def test_a_successful_login_clears_earlier_failures():
    for _ in range(auth.MAX_FAILED_ATTEMPTS - 1):
        client.post("/auth/login", json={"password": "wrong"})

    assert client.post("/auth/login", json={"password": TEST_ADMIN_PASSWORD}).status_code == 200

    # The near-lockout is forgotten, so a later typo is not the last straw.
    assert client.post("/auth/login", json={"password": "wrong"}).status_code == 401


# ---- The gate on /members ----


@pytest.mark.parametrize("method,path", MEMBER_REQUESTS)
def test_member_endpoints_reject_anonymous_callers(method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": "Bearer a.b"},
        {"Authorization": f"Basic {TEST_ADMIN_PASSWORD}"},
        # The password is not a token: the browser holds a signed session, and
        # the password itself is never a credential the API accepts twice.
        {"Authorization": f"Bearer {TEST_ADMIN_PASSWORD}"},
    ],
)
def test_member_endpoints_reject_bad_credentials(header):
    assert client.get("/members", headers=header).status_code == 401


def test_member_endpoints_accept_a_token_from_login():
    token = client.post("/auth/login", json={"password": TEST_ADMIN_PASSWORD}).json()["token"]
    assert client.get("/members", headers=auth_header(token)).status_code == 200


def test_a_tampered_payload_is_rejected():
    """Extending the expiry by hand breaks the signature it was minted with."""
    token, expires_at = issue_token()
    body, _, signature = token.partition(".")

    # A session the holder tried to stretch by a year. Only the body changes -
    # the signature is the genuine one, which is exactly the attack.
    claims = json.loads(auth._b64url_decode(body))
    claims["exp"] = expires_at + 365 * 24 * 3600
    forged_body = auth._b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))

    assert forged_body != body
    assert client.get("/members", headers=auth_header(f"{forged_body}.{signature}")).status_code == 401
    # The untouched token still works, so the rejection is the edit, not the test.
    assert client.get("/members", headers=auth_header(token)).status_code == 200


def test_an_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv("ADMIN_SESSION_HOURS", "1")
    token, expires_at = issue_token()

    # Rather than waiting an hour, move the clock past the expiry.
    monkeypatch.setattr(auth.time, "time", lambda: expires_at + 1)
    assert client.get("/members", headers=auth_header(token)).status_code == 401


def test_a_token_signed_with_another_secret_is_rejected(monkeypatch):
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "some-other-secret")
    token, _ = issue_token()

    monkeypatch.setenv("ADMIN_SESSION_SECRET", "test-session-secret")
    assert client.get("/members", headers=auth_header(token)).status_code == 401


def test_changing_the_password_invalidates_existing_sessions(monkeypatch):
    """With no explicit secret, the signing key follows the password."""
    monkeypatch.delenv("ADMIN_SESSION_SECRET", raising=False)
    token, _ = issue_token()
    assert client.get("/members", headers=auth_header(token)).status_code == 200

    monkeypatch.setenv("ADMIN_PASSWORD", "a-rotated-password")
    assert client.get("/members", headers=auth_header(token)).status_code == 401


# ---- Session check ----


def test_session_reports_a_valid_token():
    token, expires_at = issue_token()
    response = client.get("/auth/session", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "expires_at": expires_at}


def test_session_rejects_a_missing_token():
    assert client.get("/auth/session").status_code == 401


# ---- Public endpoints stay public ----


@pytest.mark.parametrize("path", ["/", "/health", "/health/database"])
def test_diagnostics_do_not_require_a_session(path):
    """These carry no member data, and are needed when login is what is broken."""
    assert client.get(path).status_code == 200


def test_session_lifetime_falls_back_to_the_default(monkeypatch):
    for bad_value in ["", "not-a-number", "0", "-3"]:
        monkeypatch.setenv("ADMIN_SESSION_HOURS", bad_value)
        assert auth.get_session_seconds() == auth.DEFAULT_SESSION_HOURS * 3600


def test_issued_tokens_verify_and_carry_the_configured_lifetime(monkeypatch):
    monkeypatch.setenv("ADMIN_SESSION_HOURS", "2")
    before = int(time.time())
    token, expires_at = issue_token()

    assert verify_token(token) == expires_at
    assert 2 * 3600 - 5 <= expires_at - before <= 2 * 3600 + 5
