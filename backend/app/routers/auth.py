# Login endpoints for the admin dashboard.
#
# Two routes only: exchange the password for a session token, and confirm a
# token is still good. The password itself is never returned, logged or stored
# anywhere by these handlers.

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import (
    AdminAuthNotConfigured,
    check_password,
    clear_failures,
    client_key,
    is_locked_out,
    issue_token,
    record_failure,
    require_admin,
    verify_token,
)
from app.schemas import LoginRequest, LoginResponse, SessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])

NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Admin access is not configured",
)

WRONG_PASSWORD = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect password",
)

TOO_MANY_ATTEMPTS = HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Too many failed attempts. Try again later.",
)


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest, request: Request) -> LoginResponse:
    """Exchange the admin password for a session token.

    A wrong password is answered 401 and counted; too many wrong ones from the
    same caller are answered 429 without even checking the password, so
    guessing costs more than one request each. When no password is configured
    the answer is 503, not 401: nobody can log in, and the administrator
    needs to see that it is the deployment at fault, not their typing.
    """
    caller = client_key(request)

    if is_locked_out(caller):
        raise TOO_MANY_ATTEMPTS

    try:
        correct = check_password(credentials.password)
    except AdminAuthNotConfigured:
        raise NOT_CONFIGURED

    if not correct:
        record_failure(caller)
        raise WRONG_PASSWORD

    clear_failures(caller)

    try:
        token, expires_at = issue_token()
    except AdminAuthNotConfigured:  # pragma: no cover - password just verified
        raise NOT_CONFIGURED

    return LoginResponse(token=token, expires_at=expires_at)


@router.get("/session", response_model=SessionResponse, dependencies=[Depends(require_admin)])
def read_session(request: Request) -> SessionResponse:
    """Confirm the caller's token is still valid and report when it expires.

    Lets the dashboard find out its session has lapsed before showing a page
    that would only fail on its first request. require_admin has already
    rejected anything invalid, so reaching the body means the token is good.
    """
    header = request.headers.get("authorization", "")
    token = header.split(" ", 1)[1] if " " in header else ""
    return SessionResponse(authenticated=True, expires_at=verify_token(token))
