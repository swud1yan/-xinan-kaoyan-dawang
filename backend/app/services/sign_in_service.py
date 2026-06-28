"""Sign-in rewards service."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coins import SignInRecord


def get_sign_in_reward(streak_day: int):
    if streak_day >= 365:
        return 50, "badge", "西南钉子户"
    if streak_day >= 100:
        return 50, "avatar_frame", "百日修行"
    if streak_day >= 60:
        return 45, "vip_trial", 14
    if streak_day >= 30:
        return 40, "vip_trial", 7
    if streak_day >= 21:
        return 35, "coins", 20
    if streak_day >= 14:
        return 30, "vip_trial", 2
    if streak_day >= 7:
        return 25, "vip_trial", 1
    if streak_day >= 6:
        return 22, None, None
    if streak_day >= 5:
        return 20, None, None
    if streak_day >= 4:
        return 18, None, None
    if streak_day >= 3:
        return 15, "coins", 5
    if streak_day >= 2:
        return 12, None, None
    return 10, None, None


async def calculate_streak(db: AsyncSession, user_id: str) -> int:
    today = date.today()
    result = await db.execute(
        select(SignInRecord.date)
        .where(SignInRecord.user_id == user_id, SignInRecord.date < today)
        .order_by(SignInRecord.date.desc())
    )
    signed_dates = {row[0] for row in result.all()}
    streak = 1
    check_date = today - timedelta(days=1)
    while check_date in signed_dates:
        streak += 1
        check_date -= timedelta(days=1)
    return streak
