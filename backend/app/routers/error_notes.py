"""Error notebook APIs."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import ErrorNote, Question
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(tags=["错题本"])


class ReviewRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=200)


async def _note_payload(db: AsyncSession, note: ErrorNote) -> dict:
    q = await db.get(Question, note.question_id)
    return {
        "id": note.id,
        "source": note.source,
        "wrongAnswer": note.wrong_answer,
        "wrongCount": note.wrong_count,
        "isMastered": note.is_mastered,
        "nextReviewAt": note.next_review_at.isoformat() if note.next_review_at else None,
        "question": {
            "id": q.id if q else note.question_id,
            "subject": q.subject if q else "",
            "subSubject": q.sub_subject if q else None,
            "content": q.content if q else "",
            "answer": q.answer if q else "",
            "explanation": q.explanation if q else "",
        },
    }


@router.get("/error-notes")
async def list_error_notes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    subject: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    stmt = select(ErrorNote).where(ErrorNote.user_id == user.id)
    if status == "mastered":
        stmt = stmt.where(ErrorNote.is_mastered == True)  # noqa: E712
    elif status == "todo":
        stmt = stmt.where(ErrorNote.is_mastered == False)  # noqa: E712
    notes = list((await db.execute(stmt.order_by(ErrorNote.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all())
    if subject:
        filtered = []
        for n in notes:
            q = await db.get(Question, n.question_id)
            if q and q.subject == subject:
                filtered.append(n)
        notes = filtered
    return {"items": [await _note_payload(db, n) for n in notes], "page": page, "pageSize": page_size}


@router.get("/error-notes/stats")
async def error_note_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    notes = list((await db.execute(select(ErrorNote).where(ErrorNote.user_id == user.id))).scalars().all())
    by_subject: dict[str, int] = {}
    for n in notes:
        q = await db.get(Question, n.question_id)
        subject = q.subject if q else "unknown"
        by_subject[subject] = by_subject.get(subject, 0) + 1
    due = sum(1 for n in notes if not n.is_mastered and (not n.next_review_at or n.next_review_at <= datetime.now()))
    return {
        "total": len(notes),
        "mastered": sum(1 for n in notes if n.is_mastered),
        "todo": sum(1 for n in notes if not n.is_mastered),
        "due": due,
        "bySubject": [{"subject": k, "count": v} for k, v in by_subject.items()],
    }


@router.get("/error-notes/review-queue")
async def review_queue(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    notes = list(
        (await db.execute(
            select(ErrorNote)
            .where(ErrorNote.user_id == user.id, ErrorNote.is_mastered == False)  # noqa: E712
            .order_by(ErrorNote.next_review_at.asc())
            .limit(20)
        )).scalars().all()
    )
    due = [n for n in notes if not n.next_review_at or n.next_review_at <= now]
    return {"items": [await _note_payload(db, n) for n in due]}


@router.post("/error-notes/{note_id}/review")
async def review_error_note(
    note_id: str,
    req: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(ErrorNote, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="错题不存在")
    q = await db.get(Question, note.question_id)
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    correct = req.answer.strip().upper() == q.answer.strip().upper()
    note.last_reviewed_at = datetime.now()
    if correct:
        note.is_mastered = True
        note.mastered_at = datetime.now()
        note.next_review_at = datetime.now() + timedelta(days=7)
    else:
        note.wrong_answer = req.answer.strip().upper()
        note.wrong_count = (note.wrong_count or 0) + 1
        note.next_review_at = datetime.now() + timedelta(days=1)
    await db.commit()
    return {"is_correct": correct, "answer": q.answer, "explanation": q.explanation, "is_mastered": note.is_mastered}


@router.post("/error-notes/{note_id}/master")
async def mark_mastered(note_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    note = await db.get(ErrorNote, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=404, detail="错题不存在")
    note.is_mastered = True
    note.mastered_at = datetime.now()
    await db.commit()
    return {"success": True}
