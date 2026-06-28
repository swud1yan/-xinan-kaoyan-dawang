"""Phase 4 daily fortune APIs."""
import random
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import FortuneRecord
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/fortune", tags=["Fortune"])

LEVELS = ["大吉", "小吉", "平稳", "蓄力"]
COLORS = ["青竹绿", "桂花金", "晴空蓝", "朱砂红", "米白"]
GOOD = ["背单词", "做真题", "整理错题", "复盘计划", "联系导师"]
BAD = ["熬夜硬扛", "临时换资料", "边学边刷短视频", "只收藏不开始"]
QUOTES = [
    "今天向前一小步，焦虑就后退一小步。",
    "把任务切小，胜率会变高。",
    "稳定不是天赋，是一次次重新开始。",
    "先完成，再完美。",
]


def _fortune_payload(item: FortuneRecord) -> dict:
    return {
        "id": item.id,
        "date": item.date.isoformat(),
        "level": item.level,
        "color": item.color,
        "number": item.number,
        "good": item.good,
        "bad": item.bad,
        "quote": item.quote,
        "score": item.score,
        "sharedCount": item.shared_count,
        "createdAt": item.created_at.isoformat() if item.created_at else None,
    }


async def _today_record(db: AsyncSession, user: User) -> FortuneRecord:
    today = date.today()
    existing = (
        await db.execute(select(FortuneRecord).where(FortuneRecord.user_id == user.id, FortuneRecord.date == today))
    ).scalar_one_or_none()
    if existing:
        return existing
    seed = f"{user.id}-{today.isoformat()}"
    rnd = random.Random(seed)
    score = rnd.randint(62, 99)
    item = FortuneRecord(
        user_id=user.id,
        date=today,
        level=LEVELS[min(len(LEVELS) - 1, (100 - score) // 12)],
        color=rnd.choice(COLORS),
        number=rnd.randint(1, 99),
        good=rnd.choice(GOOD),
        bad=rnd.choice(BAD),
        quote=rnd.choice(QUOTES),
        score=score,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/today")
async def today_fortune(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return _fortune_payload(await _today_record(db, user))


@router.post("/bless")
async def bless(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await _today_record(db, user)
    item.score = min(100, (item.score or 0) + 1)
    await db.commit()
    return {"success": True, "message": "已为今天加一份上岸好运", "fortune": _fortune_payload(item)}


@router.get("/stats")
async def fortune_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            select(func.count(FortuneRecord.id), func.coalesce(func.avg(FortuneRecord.score), 0)).where(
                FortuneRecord.user_id == user.id
            )
        )
    ).first()
    return {"days": int(row[0] or 0), "avgScore": round(float(row[1] or 0), 1)}


@router.post("/share")
async def share_fortune(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await _today_record(db, user)
    item.shared_count = (item.shared_count or 0) + 1
    await db.commit()
    return {"success": True, "shareText": f"今日考研运势：{item.level}，宜{item.good}，忌{item.bad}。"}


@router.get("/share-image")
async def share_image(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await _today_record(db, user)
    return {"type": "text-card", "title": "西南大王今日运势", "fortune": _fortune_payload(item)}
