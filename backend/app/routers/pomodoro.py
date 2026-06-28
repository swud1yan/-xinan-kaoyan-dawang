"""Pomodoro, focus stats, and lightweight study-room APIs."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import PomodoroRecord
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.xp_service import add_xp

router = APIRouter(prefix="/pomodoro", tags=["番茄钟"])


class PomodoroStartRequest(BaseModel):
    subject: str = Field(default="考研复习", max_length=100)
    subject_id: str | None = None
    duration_minutes: int = Field(default=25, ge=1, le=180)


def _date_of(value: datetime | None) -> date | None:
    return value.date() if value else None


async def _completed_records(db: AsyncSession, user_id: str) -> list[PomodoroRecord]:
    result = await db.execute(
        select(PomodoroRecord).where(
            PomodoroRecord.user_id == user_id,
            PomodoroRecord.status == "completed",
        )
    )
    return list(result.scalars().all())


async def _assert_duration_allowed(db: AsyncSession, user: User, duration: int) -> None:
    vip = user.vip_level or 0
    if duration == 25:
        if vip in (0, 17):
            today = date.today()
            records = await _completed_records(db, user.id)
            today_count = sum(1 for r in records if _date_of(r.ended_at) == today)
            if today_count >= 4:
                raise HTTPException(status_code=403, detail="免费用户每天最多完成4个标准番茄")
        return
    if duration in (45, 60):
        if vip < 1 and vip != 99:
            raise HTTPException(status_code=403, detail="长专注需要银卡及以上VIP")
        return
    if vip not in (3, 99):
        raise HTTPException(status_code=403, detail="自定义时长需要黑卡或研王爷")


@router.post("/start")
async def start_pomodoro(
    req: PomodoroStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_duration_allowed(db, user, req.duration_minutes)
    record = PomodoroRecord(
        user_id=user.id,
        subject=req.subject,
        subject_id=req.subject_id,
        planned_minutes=req.duration_minutes,
        status="running",
        started_at=datetime.now(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {"record_id": record.id, "started_at": record.started_at.isoformat()}


@router.post("/{record_id}/complete")
async def complete_pomodoro(
    record_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(PomodoroRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="番茄记录不存在")
    if record.status != "running":
        raise HTTPException(status_code=400, detail="该记录已完成或已放弃")

    now = datetime.now()
    elapsed = max(1, int((now - record.started_at).total_seconds() // 60))
    record.status = "completed"
    record.ended_at = now
    record.duration_minutes = max(record.planned_minutes or 0, elapsed)

    action = "pomodoro_45" if (record.planned_minutes or 0) >= 45 else "pomodoro_25"
    xp_result = await add_xp(db, user.id, action, record.id)
    user.pomodoro_count = (user.pomodoro_count or 0) + 1
    await db.commit()

    return {
        "duration_minutes": record.duration_minutes,
        "xp_earned": xp_result.get("xp_added", 0),
        "total_xp": xp_result.get("total_xp", user.xp or 0),
        "leveled_up": xp_result.get("leveled_up", False),
        "new_level": xp_result.get("new_level"),
        "new_title": xp_result.get("new_title"),
    }


@router.post("/{record_id}/abandon")
async def abandon_pomodoro(
    record_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(PomodoroRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="番茄记录不存在")
    record.status = "abandoned"
    record.ended_at = datetime.now()
    record.duration_minutes = max(0, int((record.ended_at - record.started_at).total_seconds() // 60))
    await db.commit()
    return {"message": "已放弃", "duration_minutes": record.duration_minutes}


@router.get("/stats/today")
async def today_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    records = [r for r in await _completed_records(db, user.id) if _date_of(r.ended_at) == today]
    return _stats_payload(records)


@router.get("/stats/weekly")
async def weekly_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    start = today - timedelta(days=today.weekday())
    records = [r for r in await _completed_records(db, user.id) if _date_of(r.ended_at) and start <= _date_of(r.ended_at) <= today]
    return _range_stats(records)


@router.get("/stats/monthly")
async def monthly_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    today = date.today()
    start = today.replace(day=1)
    records = [r for r in await _completed_records(db, user.id) if _date_of(r.ended_at) and start <= _date_of(r.ended_at) <= today]
    return _range_stats(records)


@router.get("/streak")
async def pomodoro_streak(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    records = await _completed_records(db, user.id)
    days = sorted({_date_of(r.ended_at) for r in records if r.ended_at}, reverse=True)
    if not days:
        return {"streak": 0}
    today = date.today()
    if days[0] not in (today, today - timedelta(days=1)):
        return {"streak": 0}
    streak = 1
    for i in range(len(days) - 1):
        if (days[i] - days[i + 1]).days == 1:
            streak += 1
        else:
            break
    return {"streak": streak}


@router.get("/study-room/online")
async def study_room_online(user: User = Depends(get_current_user)):
    return {
        "online": [
            {"nickname": user.nickname, "subject": "我的专注", "remainingSeconds": 0, "self": True},
            {"nickname": "西南研友", "subject": "408 数据结构", "remainingSeconds": 1280, "self": False},
            {"nickname": "上岸搭子", "subject": "英语阅读", "remainingSeconds": 2140, "self": False},
        ],
        "cheers": ["加油", "稳住", "今天也要推进一点"],
    }


def _stats_payload(records: list[PomodoroRecord]) -> dict:
    by_subject: dict[str, int] = {}
    for r in records:
        subject = r.subject or "未分类"
        by_subject[subject] = by_subject.get(subject, 0) + (r.duration_minutes or 0)
    return {
        "count": len(records),
        "total_minutes": sum(r.duration_minutes or 0 for r in records),
        "by_subject": [{"subject": k, "minutes": v} for k, v in by_subject.items()],
        "timeline": [
            {
                "id": r.id,
                "subject": r.subject,
                "minutes": r.duration_minutes,
                "startedAt": r.started_at.isoformat() if r.started_at else None,
                "endedAt": r.ended_at.isoformat() if r.ended_at else None,
            }
            for r in sorted(records, key=lambda x: x.started_at or datetime.min, reverse=True)
        ],
    }


def _range_stats(records: list[PomodoroRecord]) -> dict:
    by_date: dict[str, int] = {}
    for r in records:
        d = _date_of(r.ended_at)
        if not d:
            continue
        key = d.isoformat()
        by_date[key] = by_date.get(key, 0) + (r.duration_minutes or 0)
    payload = _stats_payload(records)
    payload["by_date"] = [{"date": k, "minutes": v} for k, v in sorted(by_date.items())]
    return payload
