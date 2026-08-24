# CRUD and search endpoints for members.

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Member
from app.schemas import MemberCreate, MemberUpdate, MemberResponse

# Every route here reads or writes personal data, so the whole router sits
# behind the admin session check - there is no public member endpoint to
# forget to guard later.
router = APIRouter(
    prefix="/members",
    tags=["members"],
    dependencies=[Depends(require_admin)],
    responses={401: {"description": "Missing or invalid admin session"}},
)


@router.post("", response_model=MemberResponse, status_code=201)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    """Create a new member. The member ID is assigned automatically."""
    db_member = Member(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.get("", response_model=List[MemberResponse])
def list_or_search_members(
    firstname: Optional[str] = Query(None, description="Filter by first name (partial match)"),
    lastname: Optional[str] = Query(None, description="Filter by last name (partial match)"),
    intercessor_name: Optional[str] = Query(None, description="Filter by intercessor name (partial match)"),
    db: Session = Depends(get_db),
):
    """List all members, or search by first name, last name and/or intercessor
    name. Filters that are provided are combined with AND; blank or omitted
    filters are ignored, so no filters at all returns the full list."""
    query = db.query(Member)

    for column, term in (
        (Member.firstname, firstname),
        (Member.lastname, lastname),
        (Member.intercessor_name, intercessor_name),
    ):
        if term and term.strip():
            query = query.filter(column.ilike(f"%{term.strip()}%"))

    return query.all()


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: int, db: Session = Depends(get_db)):
    """Retrieve a single member by ID."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member_update: MemberUpdate, db: Session = Depends(get_db)):
    """Update an existing member's details (full replace of editable fields)."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    for field, value in member_update.model_dump().items():
        setattr(member, field, value)

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """Delete a member by ID."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return None