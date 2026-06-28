"""XP and leveling service."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coins import XpHistory
from app.models.user import User

XP_RULES = {
    "sign_in": {"base": 10, "daily_limit": 1},
    "post": {"base": 20, "daily_limit": 5},
    "comment": {"base": 5, "daily_limit": 20},
    "like_give": {"base": 2, "daily_limit": 30},
    "like_receive": {"base": 3, "daily_limit": None},
    "post_featured": {"base": 100, "daily_limit": None},
    "upload": {"base": 50, "daily_limit": 5},
    "invite": {"base": 200, "daily_limit": None},
    "profile": {"base": 10, "daily_limit": None},
    "pomodoro_25": {"base": 15, "daily_limit": 10},
    "pomodoro_45": {"base": 30, "daily_limit": 5},
    "daily_question": {"base": 5, "daily_limit": 1},
}

TITLES = [
    (1, "西南娃娃"),
    (6, "西南萌新"),
    (11, "西南学童"),
    (16, "西南少年"),
    (21, "西南学子"),
    (26, "西南书生"),
    (31, "西南秀才"),
    (36, "西南举人"),
    (41, "西南进士"),
    (46, "西南探花"),
    (51, "西南榜眼"),
    (56, "西南状元"),
    (61, "西南学霸"),
    (66, "西南卷王"),
    (71, "西南学神"),
    (76, "西南小王"),
    (81, "西南大王"),
    (86, "西南霸王"),
    (91, "西南圣王"),
    (96, "西南皇帝"),
]


def xp_for_level(level: int) -> int:
    return int(100 * (1.15 ** (level - 1)))


def total_xp_for_level(level: int) -> int:
    return sum(xp_for_level(i) for i in range(1, level))


def get_title(level: int) -> str:
    for min_level, title in reversed(TITLES):
        if level >= min_level:
            return title
    return TITLES[0][1]


def get_level_info(xp: int) -> dict:
    xp = max(0, xp or 0)
    level = 1
    while level < 100 and xp >= total_xp_for_level(level + 1):
        level += 1
    current = total_xp_for_level(level)
    next_level = total_xp_for_level(level + 1)
    return {
        "level": level,
        "title": get_title(level),
        "progress": (xp - current) / max(1, next_level - current),
        "xp": xp,
        "xp_to_next": max(0, next_level - xp),
    }


async def add_xp(db: AsyncSession, user_id: str, action: str, related_id: str | None = None) -> dict:
    rule = XP_RULES.get(action)
    if not rule:
        return {"xp_added": 0}

    if rule["daily_limit"]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await db.execute(
            select(func.count())
            .select_from(XpHistory)
            .where(
                XpHistory.user_id == user_id,
                XpHistory.action == action,
                XpHistory.created_at >= today,
            )
        )
        if (count.scalar() or 0) >= rule["daily_limit"]:
            return {"xp_added": 0, "reason": "daily_limit"}

    user = await db.get(User, user_id)
    if not user:
        return {"xp_added": 0, "reason": "user_not_found"}

    old_xp = user.xp or 0
    old_info = get_level_info(old_xp)
    user.xp = old_xp + rule["base"]
    new_info = get_level_info(user.xp)
    user.level = new_info["level"]

    db.add(
        XpHistory(
            user_id=user_id,
            amount=rule["base"],
            action=action,
            description=f"{action} +{rule['base']}XP",
            related_id=related_id,
        )
    )
    await db.commit()

    leveled_up = new_info["level"] > old_info["level"]
    return {
        "xp_added": rule["base"],
        "total_xp": user.xp,
        "leveled_up": leveled_up,
        "new_level": new_info["level"] if leveled_up else None,
        "new_title": new_info["title"] if leveled_up else None,
        "level": new_info["level"],
        "title": new_info["title"],
    }
