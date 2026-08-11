# CRUD and search endpoints for members.

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Member
from app.schemas import MemberCreate, MemberUpdate, MemberResponse

router = APIRouter(prefix="/members", tags=["members"])


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
    firstname: Optional[str] = Query(None, description="Filter by firstname (partial match)"),
    lastname: Optional[str] = Query(None, description="Filter by lastname (partial match)"),
    intercessor_name: Optional[str] = Query(None, description="Filter by intercessor name (partial match)"),
    db: Session = Depends(get_db),
):
    """List all members, or search by firstname/lastname/intercessor_name if provided.
    If several are given, members matching any of them are returned."""
    query = db.query(Member)

    if firstname or lastname or intercessor_name:
        filters = []
        if firstname:
            filters.append(Member.firstname.ilike(f"%{firstname}%"))
        if lastname:
            filters.append(Member.lastname.ilike(f"%{lastname}%"))
        if intercessor_name:
            filters.append(Member.intercessor_name.ilike(f"%{intercessor_name}%"))
        query = query.filter(or_(*filters))

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