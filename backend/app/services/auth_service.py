"""
Auth service - registration, login, password reset, AI summary
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.services.coins_service import VIP_MONTHLY_COINS
from app.services.xp_service import get_level_info
from app.utils.security import hash_password, verify_password, create_token


async def register_user(
    db: AsyncSession,
    dawang_id: str,
    nickname: str,
    username: str,
    password: str,
    phone: str | None = None,
    client_ip: str = "",
    grade: str | None = None,
    major: str | None = None,
    has_target: bool = False,
    target_school: str | None = None,
    direction: str | None = None,
    progress: str | None = None,
    estimated_score: str | None = None,
    study_style: str | None = None,
    undergrad_province: str | None = None,
    undergrad_school: str | None = None,
    undergrad_private: bool = False,
) -> dict:
    # Check uniqueness
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValueError("用户名已存在")
    existing = await db.execute(select(User).where(User.dawang_id == dawang_id))
    if existing.scalar_one_or_none():
        raise ValueError("大王号已被占用")
    if phone:
        existing = await db.execute(select(User).where(User.phone == phone))
        if existing.scalar_one_or_none():
            raise ValueError("手机号已被绑定")

    user = User(
        dawang_id=dawang_id, nickname=nickname, username=username,
        password_hash=hash_password(password), phone=phone,
        grade=grade, major=major, has_target=has_target,
        target_school=target_school, direction=direction,
        progress=progress, estimated_score=estimated_score,
        study_style=study_style,
        undergrad_province=undergrad_province, undergrad_school=undergrad_school,
        undergrad_private=undergrad_private,
        xp=0, level=1, vip_level=0,
        monthly_coins=VIP_MONTHLY_COINS[0], monthly_coins_max=VIP_MONTHLY_COINS[0],
        purchased_coins=0, coins_reset_date=datetime.now(timezone.utc),
        deep_think_enabled=False, sign_in_streak=0, pomodoro_count=0,
        registered_ip=client_ip, last_login_ip=client_ip,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    token = create_token(user.id, user.username)
    return {"user": _user_to_dict(user), "token": token}


async def login_user(db: AsyncSession, username: str, password: str, client_ip: str = "") -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    if user.is_banned:
        raise ValueError("账号已被封禁")

    user.last_login_ip = client_ip
    user.last_login_at = datetime.now(timezone.utc)
    token = create_token(user.id, user.username)
    return {"user": _user_to_dict(user), "token": token}


async def check_dawang_id(db: AsyncSession, dawang_id: str) -> bool:
    result = await db.execute(select(User).where(User.dawang_id == dawang_id))
    return result.scalar_one_or_none() is None


async def forgot_password(db: AsyncSession, phone: str, new_password: str) -> bool:
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("未找到该手机号绑定的账号")
    user.password_hash = hash_password(new_password)
    return True


async def change_password(db: AsyncSession, user_id: str, old_password: str, new_password: str) -> bool:
    user = await db.get(User, user_id)
    if not user or not verify_password(old_password, user.password_hash):
        raise ValueError("原密码错误")
    user.password_hash = hash_password(new_password)
    return True


async def change_dawang_id(db: AsyncSession, user_id: str, new_dawang_id: str) -> bool:
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("用户不存在")
    # Check once per month
    if user.dawang_id_updated_at:
        if datetime.now(timezone.utc) - user.dawang_id_updated_at < timedelta(days=30):
            raise ValueError("大王号每月只能修改一次")
    # Check uniqueness
    existing = await db.execute(select(User).where(User.dawang_id == new_dawang_id))
    if existing.scalar_one_or_none():
        raise ValueError("该大王号已被占用")
    user.dawang_id = new_dawang_id
    user.dawang_id_updated_at = datetime.now(timezone.utc)
    return True


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def _user_to_dict(user: User) -> dict:
    level_info = get_level_info(user.xp or 0)
    return {
        "id": user.id, "dawangId": user.dawang_id, "nickname": user.nickname,
        "username": user.username, "phone": user.phone,
        "grade": user.grade, "major": user.major,
        "hasTarget": user.has_target, "targetSchool": user.target_school,
        "direction": user.direction, "currentProgress": user.progress,
        "estimatedScore": user.estimated_score, "studyStyle": user.study_style,
        "undergradProvince": user.undergrad_province,
        "undergradSchool": user.undergrad_school,
        "undergradPrivate": user.undergrad_private,
        "avatar": user.avatar, "school": user.school,
        "xp": user.xp or 0,
        "level": user.level or level_info["level"],
        "levelTitle": level_info["title"],
        "xpProgress": level_info["progress"],
        "xpToNext": level_info["xp_to_next"],
        "vipLevel": user.vip_level or 0,
        "vipExpireAt": user.vip_expire_at.isoformat() if user.vip_expire_at else None,
        "monthlyCoins": user.monthly_coins or 0,
        "monthlyCoinsMax": user.monthly_coins_max or VIP_MONTHLY_COINS.get(user.vip_level or 0, 100),
        "purchasedCoins": user.purchased_coins or 0,
        "deepThinkEnabled": bool(user.deep_think_enabled),
        "signInStreak": user.sign_in_streak or 0,
        "pomodoroCount": user.pomodoro_count or 0,
    }
