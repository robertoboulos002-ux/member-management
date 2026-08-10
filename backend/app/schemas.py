# Pydantic models for request validation and API response shapes.

from datetime import date, datetime, timezone

from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    timestamp: str


class MemberBase(BaseModel):
    """Shared fields for create/update requests. All fields are required and
    must be non-empty after trimming whitespace."""

    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    father_name: str = Field(..., min_length=1, max_length=100)
    mother_name: str = Field(..., min_length=1, max_length=100)
    intercessor_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date


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

    model_config = ConfigDict(from_attributes=True)