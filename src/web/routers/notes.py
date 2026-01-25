"""Notes API router."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.db.repository import NoteRepository, PaperRepository
from src.web.dependencies import get_note_repo, get_paper_repo
from src.web.schemas.common import MessageResponse

router = APIRouter()


class NoteCreate(BaseModel):
    """Request to create/update a note."""
    content: str


class NoteRead(BaseModel):
    """Response for a note."""
    id: int
    bibcode: str
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteListResponse(BaseModel):
    """Response for note list."""
    notes: list[NoteRead]
    total: int


@router.get("/", response_model=NoteListResponse)
async def list_notes(
    limit: int = Query(default=100, ge=1, le=1000),
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """List all notes."""
    notes = note_repo.get_all(limit=limit)
    return NoteListResponse(
        notes=[NoteRead.model_validate(n) for n in notes],
        total=len(notes),
    )


@router.get("/{bibcode}", response_model=Optional[NoteRead])
async def get_note(
    bibcode: str,
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """Get note for a paper."""
    note = note_repo.get(bibcode)
    if not note:
        return None
    return NoteRead.model_validate(note)


@router.put("/{bibcode}", response_model=NoteRead)
async def create_or_update_note(
    bibcode: str,
    request: NoteCreate,
    replace: bool = Query(default=True, description="If true, replace existing note. If false, append."),
    note_repo: NoteRepository = Depends(get_note_repo),
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Create or update a note for a paper."""
    # Check if paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    if replace:
        # Delete existing note first if replacing
        existing = note_repo.get(bibcode)
        if existing:
            note_repo.delete(bibcode)

    note = note_repo.add(bibcode, request.content)
    return NoteRead.model_validate(note)


@router.delete("/{bibcode}", response_model=MessageResponse)
async def delete_note(
    bibcode: str,
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """Delete note for a paper."""
    success = note_repo.delete(bibcode)
    if not success:
        raise HTTPException(status_code=404, detail=f"Note not found for paper: {bibcode}")

    return MessageResponse(message=f"Note for paper {bibcode} deleted")


@router.get("/search/text")
async def search_notes(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """Search notes by content."""
    notes = note_repo.search_by_text(query, limit=limit)
    return {
        "query": query,
        "notes": [NoteRead.model_validate(n) for n in notes],
        "count": len(notes),
    }
