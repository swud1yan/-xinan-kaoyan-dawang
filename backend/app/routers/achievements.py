"""Phase 4 achievements APIs."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import Achievement, UserAchievement, UserAnswer, UserCardProgress
from app.models.post import Post
from app.models.social import Friend
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.xp_service import get_level_info

router = APIRouter(tags=["Achievements"])


ACHIEVEMENTS = [
    ("first_pomodoro", "专注初体验", "完成第一个番茄钟", "study", "🍅", "pomodoro_count", 1, 10, False, 10),
    ("pomodoro_100", "番茄农夫", "累计完成100个番茄钟", "study", "🍅🍅", "pomodoro_count", 100, 80, False, 20),
    ("pomodoro_500", "番茄园主", "累计完成500个番茄钟", "study", "🍅🍅🍅", "pomodoro_count", 500, 200, False, 30),
    ("streak_7", "七日修行", "连续签到7天", "persistence", "🔥", "sign_in_streak", 7, 30, False, 40),
    ("streak_30", "三十日功", "连续签到30天", "persistence", "🔥🔥", "sign_in_streak", 30, 120, False, 50),
    ("first_post", "初次发声", "发布第一篇帖子", "social", "✍", "post_count", 1, 15, False, 60),
    ("likes_100", "一呼百应", "累计收到100个点赞", "social", "📣", "post_likes", 100, 100, False, 70),
    ("daily_correct_1", "答题初体验", "答对第一道每日一题", "study", "✅", "daily_question_correct", 1, 10, False, 80),
    ("daily_correct_100", "刷题机器", "答对100道每日一题", "study", "⚙", "daily_question_correct", 100, 120, False, 90),
    ("flashcard_100", "记忆大师", "掌握100张闪卡", "study", "🧠", "flashcard_mastered", 100, 100, False, 100),
    ("friend_1", "人脉初建", "添加第一个好友", "social", "🤝", "friend_count", 1, 10, False, 110),
    ("friend_20", "社交达人", "添加20个好友", "social", "🤝🤝", "friend_count", 20, 100, False, 120),
    ("xp_1000", "西南学子", "累计获得1000经验", "growth", "🎯", "xp", 1000, 120, False, 130),
    ("xp_5000", "西南卷王", "累计获得5000经验", "growth", "🏆", "xp", 5000, 300, False, 140),
    ("hidden_full_month", "全勤王", "长期保持稳定签到", "hidden", "🌙", "sign_in_streak", 31, 160, True, 900),
]


async def ensure_achievement_seed(db: AsyncSession) -> None:
    existing = set((await db.execute(select(Achievement.id))).scalars().all())
    for aid, name, desc, category, icon, ctype, cvalue, reward, hidden, order in ACHIEVEMENTS:
        if aid in existing:
            continue
        db.add(
            Achievement(
                id=aid,
                name=name,
                description=desc,
                category=category,
                icon=icon,
                condition_type=ctype,
                condition_value=cvalue,
                xp_reward=reward,
                is_hidden=hidden,
                sort_order=order,
            )
        )
    await db.commit()


async def _metric_map(db: AsyncSession, user: User) -> dict[str, int]:
    post_likes = int(
        (await db.execute(select(func.coalesce(func.sum(Post.likes_count), 0)).where(Post.user_id == user.id))).scalar() or 0
    )
    post_count = int((await db.execute(select(func.count()).select_from(Post).where(Post.user_id == user.id))).scalar() or 0)
    friend_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Friend)
                .where(Friend.status == "accepted", (Friend.user_id == user.id) | (Friend.friend_id == user.id))
            )
        ).scalar()
        or 0
    )
    daily_correct = int(
        (
            await db.execute(
                select(func.count()).select_from(UserAnswer).where(UserAnswer.user_id == user.id, UserAnswer.is_correct == True)  # noqa: E712
            )
        ).scalar()
        or 0
    )
    flashcard_mastered = int(
        (
            await db.execute(
                select(func.count()).select_from(UserCardProgress).where(
                    UserCardProgress.user_id == user.id,
                    UserCardProgress.is_mastered == True,  # noqa: E712
                )
            )
        ).scalar()
        or 0
    )
    return {
        "pomodoro_count": user.pomodoro_count or 0,
        "sign_in_streak": user.sign_in_streak or 0,
        "xp": user.xp or 0,
        "post_count": post_count,
        "post_likes": post_likes,
        "friend_count": friend_count,
        "daily_question_correct": daily_correct,
        "flashcard_mastered": flashcard_mastered,
    }


async def _sync_unlocks(db: AsyncSession, user: User) -> None:
    await ensure_achievement_seed(db)
    achievements = (await db.execute(select(Achievement))).scalars().all()
    unlocked = set(
        (
            await db.execute(
                select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)
            )
        ).scalars().all()
    )
    metrics = await _metric_map(db, user)
    changed = False
    for item in achievements:
        if item.id in unlocked:
            continue
        if metrics.get(item.condition_type, 0) >= (item.condition_value or 1):
            db.add(UserAchievement(user_id=user.id, achievement_id=item.id))
            if item.xp_reward:
                old_xp = user.xp or 0
                user.xp = old_xp + item.xp_reward
                user.level = get_level_info(user.xp)["level"]
            changed = True
    if changed:
        await db.commit()


def _payload(item: Achievement, unlocked_ids: set[str], metrics: dict[str, int], unlocked_at: dict[str, datetime]) -> dict:
    current = metrics.get(item.condition_type, 0)
    need = max(item.condition_value or 1, 1)
    unlocked = item.id in unlocked_ids
    if item.is_hidden and not unlocked:
        return {
            "id": item.id,
            "name": "隐藏成就",
            "description": "达成后揭晓",
            "category": item.category,
            "icon": "？",
            "isHidden": True,
            "isUnlocked": False,
            "progress": 0,
            "current": 0,
            "target": need,
            "xpReward": item.xp_reward,
            "unlockedAt": None,
        }
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "category": item.category,
        "icon": item.icon,
        "isHidden": item.is_hidden,
        "isUnlocked": unlocked,
        "progress": min(1.0, current / need),
        "current": current,
        "target": need,
        "xpReward": item.xp_reward,
        "unlockedAt": unlocked_at[item.id].isoformat() if item.id in unlocked_at else None,
    }


@router.get("/achievements")
async def list_achievements(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _sync_unlocks(db, user)
    rows = (await db.execute(select(UserAchievement).where(UserAchievement.user_id == user.id))).scalars().all()
    unlocked_ids = {r.achievement_id for r in rows}
    unlocked_at = {r.achievement_id: r.unlocked_at for r in rows}
    metrics = await _metric_map(db, user)
    achievements = (
        await db.execute(select(Achievement).order_by(Achievement.sort_order.asc(), Achievement.name.asc()))
    ).scalars().all()
    return {
        "unlockedCount": len(unlocked_ids),
        "totalCount": len(achievements),
        "items": [_payload(a, unlocked_ids, metrics, unlocked_at) for a in achievements],
    }


@router.get("/achievements/unlocked")
async def unlocked_achievements(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await list_achievements(user, db)
    return {"items": [item for item in data["items"] if item["isUnlocked"]]}


@router.get("/achievements/recent")
async def recent_unlocks(
    limit: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _sync_unlocks(db, user)
    rows = (
        await db.execute(
            select(UserAchievement, Achievement)
            .join(Achievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user.id)
            .order_by(UserAchievement.unlocked_at.desc())
            .limit(limit)
        )
    ).all()
    return {
        "items": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "category": a.category,
                "xpReward": a.xp_reward,
                "unlockedAt": ua.unlocked_at.isoformat() if ua.unlocked_at else None,
            }
            for ua, a in rows
        ]
    }
