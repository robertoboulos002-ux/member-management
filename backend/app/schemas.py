# Pydantic models for request validation and API response shapes.

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    timestamp: str


class DatabaseHealthResponse(BaseModel):
    """Response body for GET /health/database.

    Column names only - never row data. Defaults cover the cases where there is
    nothing to report: an unreachable database has no tables to list, and a
    missing `members` table has no columns.
    """

    reachable: bool
    error: Optional[str] = None
    tables: list[str] = Field(default_factory=list)
    members_columns: list[str] = Field(default_factory=list)
    expected_members_columns: list[str] = Field(default_factory=list)
    missing_members_columns: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    # No max_length: a long passphrase is a good password, and there is no
    # storage cost here - the value is compared and discarded.
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """A freshly issued session token and its expiry as a unix timestamp."""

    token: str
    expires_at: int


class SessionResponse(BaseModel):
    """Response body for GET /auth/session."""

    authenticated: bool
    expires_at: int


class MemberBase(BaseModel):
    """Shared fields for create/update requests. All fields are required and
    must be non-empty after trimming whitespace, except `comments`, which is
    free-form notes and may be omitted or left blank."""

    # The parish register number, chosen by the admin — unlike `id`, which the
    # database assigns and no one picks.
    baptism_number: str = Field(..., min_length=1, max_length=50)
    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    father_name: str = Field(..., min_length=1, max_length=100)
    mother_name: str = Field(..., min_length=1, max_length=100)
    intercessor_name: str = Field(..., min_length=1, max_length=100)
    godfather_name: str = Field(..., min_length=1, max_length=100)
    godmother_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    place_of_birth: str = Field(..., min_length=1, max_length=100)
    baptizing_priest: str = Field(..., min_length=1, max_length=100)
    place_of_baptism: str = Field(..., min_length=1, max_length=100)
    date_of_baptism: date
    comments: Optional[str] = Field(None, max_length=2000)


class MemberCreate(MemberBase):
    """Request body for creating a member."""
    pass


class MemberUpdate(MemberBase):
    """Request body for updating a member. Same required fields as create —
    this is a full replace, not a partial patch."""
    pass


class MemberResponse(MemberBase):
    """Response body representing a stored member, including its assigned ID."""

    id: int

    # Relaxed from the required base fields: members stored before these
    # columns existed come back with no value rather than failing validation.
    place_of_birth: Optional[str] = None
    baptism_number: Optional[str] = None
    godfather_name: Optional[str] = None
    godmother_name: Optional[str] = None
    baptizing_priest: Optional[str] = None
    place_of_baptism: Optional[str] = None
    date_of_baptism: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)