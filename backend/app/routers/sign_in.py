"""Daily sign-in router."""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.coins import SignInRecord, XpHistory
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.coins_service import VIP_MONTHLY_COINS
from app.services.sign_in_service import calculate_streak, get_sign_in_reward
from app.services.xp_service import get_level_info

router = APIRouter(prefix="/auth", tags=["签到"])


@router.post("/sign-in")
async def daily_sign_in(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    existing = await db.execute(
        select(SignInRecord).where(
            SignInRecord.user_id == user.id,
            SignInRecord.date == today,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="今日已签到")

    streak = await calculate_streak(db, user.id)
    base_xp, bonus_type, bonus_detail = get_sign_in_reward(streak)
    bonus_xp = 500 if streak % 30 == 0 else 100 if streak % 7 == 0 else 0
    total_xp_earned = base_xp + bonus_xp

    old_info = get_level_info(user.xp or 0)
    user.xp = (user.xp or 0) + total_xp_earned
    new_info = get_level_info(user.xp)
    user.level = new_info["level"]
    user.sign_in_streak = streak
    user.last_sign_in_date = datetime.now()

    if bonus_type == "coins":
        user.purchased_coins = (user.purchased_coins or 0) + int(bonus_detail or 0)
    elif bonus_type == "vip_trial":
        days = int(bonus_detail or 1)
        now = datetime.now()
        if (user.vip_level or 0) == 0:
            user.vip_level = 1
            user.vip_expire_at = now + timedelta(days=days)
            user.monthly_coins = VIP_MONTHLY_COINS[1]
            user.monthly_coins_max = VIP_MONTHLY_COINS[1]
            user.coins_reset_date = datetime.now()
        else:
            start = user.vip_expire_at if user.vip_expire_at and user.vip_expire_at > now else now
            user.vip_expire_at = start + timedelta(days=days)

    db.add(
        SignInRecord(
            user_id=user.id,
            date=today,
            xp_earned=total_xp_earned,
            streak_day=streak,
            bonus_type=bonus_type,
        )
    )
    db.add(
        XpHistory(
            user_id=user.id,
            amount=total_xp_earned,
            action="sign_in",
            description=f"连续签到第{streak}天 +{total_xp_earned}XP",
        )
    )
    await db.commit()

    return {
        "xp_earned": total_xp_earned,
        "base_xp": base_xp,
        "bonus_xp": bonus_xp,
        "total_xp": user.xp,
        "streak": streak,
        "bonus": {"type": bonus_type, "detail": bonus_detail} if bonus_type else None,
        "leveled_up": new_info["level"] > old_info["level"],
        "new_level": new_info["level"],
        "new_title": new_info["title"],
    }


@router.get("/sign-in/status")
async def sign_in_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    record = await db.execute(
        select(SignInRecord).where(
            SignInRecord.user_id == user.id,
            SignInRecord.date == today,
        )
    )
    today_signed = record.scalar_one_or_none() is not None

    month_start = today.replace(day=1)
    month_records = await db.execute(
        select(SignInRecord)
        .where(SignInRecord.user_id == user.id, SignInRecord.date >= month_start)
        .order_by(SignInRecord.date.asc())
    )
    month_data = month_records.scalars().all()

    streak = user.sign_in_streak or 0
    next_bonus_day = ((streak // 7) + 1) * 7
    next_xp, next_bonus, next_detail = get_sign_in_reward(next_bonus_day)

    return {
        "today_signed": today_signed,
        "streak": streak,
        "this_month_days": len(month_data),
        "this_month_records": [
            {"date": r.date.isoformat(), "xp": r.xp_earned}
            for r in month_data
        ],
        "next_bonus": {
            "day": next_bonus_day,
            "remaining_days": max(0, next_bonus_day - streak),
            "xp": next_xp,
            "extra": next_detail if next_bonus else None,
        },
    }
