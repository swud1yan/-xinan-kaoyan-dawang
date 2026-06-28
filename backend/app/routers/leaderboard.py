"""Phase 4 leaderboard APIs."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import PomodoroRecord
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


def _user_payload(user: User, rank: int, value: int, label: str, extra: dict | None = None) -> dict:
    title = "本周卷王" if rank == 1 else "冲榜中"
    payload = {
        "rank": rank,
        "userId": user.id,
        "nickname": user.nickname or user.username,
        "dawangId": user.dawang_id,
        "level": user.level or 1,
        "title": title,
        "value": value,
        "label": label,
        "isSelf": False,
    }
    if extra:
        payload.update(extra)
    return payload


async def _with_self(items: list[dict], self_item: dict | None, user_id: str) -> dict:
    for item in items:
        if item["userId"] == user_id:
            item["isSelf"] = True
            self_item = item
    if self_item:
        self_item["isSelf"] = True
    return {"items": items, "self": self_item}


@router.get("/weekly-pomodoro")
async def weekly_pomodoro_leaderboard(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start = today - timedelta(days=today.weekday())
    start_dt = datetime.combine(start, datetime.min.time())
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(func.sum(PomodoroRecord.duration_minutes), 0).label("minutes"),
                func.count(PomodoroRecord.id).label("count"),
            )
            .join(PomodoroRecord, PomodoroRecord.user_id == User.id)
            .where(PomodoroRecord.status == "completed", PomodoroRecord.ended_at >= start_dt)
            .group_by(User.id)
            .order_by(func.coalesce(func.sum(PomodoroRecord.duration_minutes), 0).desc())
            .limit(50)
        )
    ).all()
    items = [
        _user_payload(u, i + 1, int(minutes or 0), "分钟", {"pomodoroCount": int(count or 0)})
        for i, (u, minutes, count) in enumerate(rows)
    ]
    self_item = next((item for item in items if item["userId"] == user.id), None)
    if self_item is None:
        mine = (
            await db.execute(
                select(func.coalesce(func.sum(PomodoroRecord.duration_minutes), 0), func.count(PomodoroRecord.id)).where(
                    PomodoroRecord.user_id == user.id,
                    PomodoroRecord.status == "completed",
                    PomodoroRecord.ended_at >= start_dt,
                )
            )
        ).first()
        self_item = _user_payload(user, len(items) + 1, int(mine[0] or 0), "分钟", {"pomodoroCount": int(mine[1] or 0)})
    payload = await _with_self(items, self_item, user.id)
    payload["range"] = {"start": start.isoformat(), "end": (start + timedelta(days=6)).isoformat()}
    payload["page"] = page
    return payload


@router.get("/total-xp")
async def total_xp_leaderboard(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    users = (
        await db.execute(select(User).order_by(User.xp.desc(), User.created_at.asc()).limit(50))
    ).scalars().all()
    items = [_user_payload(u, i + 1, u.xp or 0, "XP") for i, u in enumerate(users)]
    self_item = next((item for item in items if item["userId"] == user.id), None)
    if self_item is None:
        higher = int((await db.execute(select(func.count()).select_from(User).where(User.xp > (user.xp or 0)))).scalar() or 0)
        self_item = _user_payload(user, higher + 1, user.xp or 0, "XP")
    payload = await _with_self(items, self_item, user.id)
    payload["page"] = page
    return payload


@router.get("/streak")
async def streak_leaderboard(
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    users = (
        await db.execute(select(User).order_by(User.sign_in_streak.desc(), User.created_at.asc()).limit(50))
    ).scalars().all()
    items = [_user_payload(u, i + 1, u.sign_in_streak or 0, "天") for i, u in enumerate(users)]
    self_item = next((item for item in items if item["userId"] == user.id), None)
    if self_item is None:
        higher = int(
            (await db.execute(select(func.count()).select_from(User).where(User.sign_in_streak > (user.sign_in_streak or 0)))).scalar()
            or 0
        )
        self_item = _user_payload(user, higher + 1, user.sign_in_streak or 0, "天")
    payload = await _with_self(items, self_item, user.id)
    payload["page"] = page
    return payload
