"""Phase 4 diary APIs."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import DiaryEntry, PomodoroRecord, UserAnswer, UserCardProgress
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(tags=["Diary"])


class DiaryRequest(BaseModel):
    date: str | None = None
    content: str = Field("", max_length=2000)
    mood: str | None = Field(None, max_length=20)
    is_public: bool = False


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        raise HTTPException(status_code=400, detail="invalid date")


async def _day_stats(db: AsyncSession, user_id: str, day: date) -> dict:
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    pomo = (
        await db.execute(
            select(func.count(PomodoroRecord.id), func.coalesce(func.sum(PomodoroRecord.duration_minutes), 0)).where(
                PomodoroRecord.user_id == user_id,
                PomodoroRecord.status == "completed",
                PomodoroRecord.ended_at >= start,
                PomodoroRecord.ended_at < end,
            )
        )
    ).first()
    correct = (
        await db.execute(
            select(func.count()).select_from(UserAnswer).where(
                UserAnswer.user_id == user_id,
                UserAnswer.is_correct == True,  # noqa: E712
                UserAnswer.answered_at >= start,
                UserAnswer.answered_at < end,
            )
        )
    ).scalar() or 0
    cards = (
        await db.execute(
            select(func.count()).select_from(UserCardProgress).where(
                UserCardProgress.user_id == user_id,
                UserCardProgress.last_reviewed_at >= start,
                UserCardProgress.last_reviewed_at < end,
            )
        )
    ).scalar() or 0
    return {
        "pomodoro_count": int(pomo[0] or 0),
        "pomodoro_minutes": int(pomo[1] or 0),
        "daily_question_correct": bool(correct),
        "flashcards_reviewed": int(cards or 0),
    }


def _ai_reply(content: str, mood: str | None, stats: dict) -> str:
    if not content.strip() and not any(stats.values()):
        return "今天也可以从一个很小的行动开始。写下一句话，就是重新掌控节奏。"
    mood_text = {"happy": "开心", "anxious": "焦虑", "tired": "疲惫", "motivated": "有动力", "neutral": "平静"}.get(mood or "", "平稳")
    return f"今天状态{mood_text}，完成了{stats['pomodoro_count']}个番茄钟。保持记录很重要，明天继续推进一个最小任务。"


def _payload(item: DiaryEntry) -> dict:
    return {
        "id": item.id,
        "date": item.date.isoformat() if item.date else None,
        "content": item.content,
        "mood": item.mood,
        "isPublic": item.is_public,
        "pomodoroCount": item.pomodoro_count,
        "pomodoroMinutes": item.pomodoro_minutes,
        "dailyQuestionCorrect": item.daily_question_correct,
        "flashcardsReviewed": item.flashcards_reviewed,
        "aiReply": item.ai_reply,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
        "updatedAt": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.post("/diary")
async def save_diary(req: DiaryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    day = _parse_date(req.date)
    stats = await _day_stats(db, user.id, day)
    existing = (
        await db.execute(select(DiaryEntry).where(DiaryEntry.user_id == user.id, DiaryEntry.date == day))
    ).scalar_one_or_none()
    entry = existing or DiaryEntry(user_id=user.id, date=day)
    entry.content = req.content.strip()
    entry.mood = req.mood
    entry.is_public = req.is_public
    entry.pomodoro_count = stats["pomodoro_count"]
    entry.pomodoro_minutes = stats["pomodoro_minutes"]
    entry.daily_question_correct = stats["daily_question_correct"]
    entry.flashcards_reviewed = stats["flashcards_reviewed"]
    entry.ai_reply = _ai_reply(entry.content, entry.mood, stats)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _payload(entry)


@router.get("/diary")
async def list_diary(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user.id)
            .order_by(DiaryEntry.date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {"items": [_payload(r) for r in rows], "page": page, "pageSize": page_size}


@router.get("/diary/{date_str}")
async def get_diary_by_date(date_str: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    day = _parse_date(date_str)
    entry = (
        await db.execute(select(DiaryEntry).where(DiaryEntry.user_id == user.id, DiaryEntry.date == day))
    ).scalar_one_or_none()
    if not entry:
        return {"date": day.isoformat(), "entry": None, "stats": await _day_stats(db, user.id, day)}
    return {"entry": _payload(entry), "stats": await _day_stats(db, user.id, day)}


@router.delete("/diary/{diary_id}")
async def delete_diary(diary_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entry = await db.get(DiaryEntry, diary_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="diary not found")
    await db.delete(entry)
    await db.commit()
    return {"success": True}
