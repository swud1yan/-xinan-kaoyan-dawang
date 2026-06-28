"""Auth router - register, login, password reset, profile and AI summary."""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.auth_service import (
    change_dawang_id,
    change_password,
    check_dawang_id,
    forgot_password,
    login_user,
    register_user,
)
from app.services.coins_service import VIP_MONTHLY_COINS
from app.services.xp_service import get_level_info

router = APIRouter(prefix="/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    dawang_id: str = Field(..., min_length=4, max_length=15)
    nickname: str = Field(..., min_length=1, max_length=50)
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    phone: str | None = Field(None, min_length=11, max_length=11)
    grade: str | None = None
    major: str | None = None
    hasTarget: bool = False
    targetSchool: str | None = None
    direction: str | None = None
    currentProgress: str | None = None
    estimatedScore: str | None = None
    studyStyle: str | None = None
    undergradProvince: str | None = None
    undergradSchool: str | None = None
    undergradPrivate: bool = False


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class ForgotPasswordRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11)
    new_password: str = Field(..., min_length=6, max_length=100)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class ChangeDawangIdRequest(BaseModel):
    new_dawang_id: str = Field(..., min_length=4, max_length=15)


class CheckDawangIdRequest(BaseModel):
    dawang_id: str = Field(..., min_length=4, max_length=15)


class DebugSelfUpdateRequest(BaseModel):
    xp_delta: int = Field(0, ge=-100000, le=100000)
    monthly_coins_delta: int = Field(0, ge=-100000, le=100000)
    purchased_coins_delta: int = Field(0, ge=-100000, le=100000)
    vip_level: int | None = Field(None, ge=0, le=99)
    monthly_coins: int | None = Field(None, ge=0, le=1000000)
    purchased_coins: int | None = Field(None, ge=0, le=1000000)
    deep_think_enabled: bool | None = None


def _me_payload(user: User) -> dict:
    level_info = get_level_info(user.xp or 0)
    return {
        "id": user.id,
        "dawangId": user.dawang_id,
        "nickname": user.nickname,
        "username": user.username,
        "phone": user.phone,
        "grade": user.grade,
        "major": user.major,
        "hasTarget": user.has_target,
        "targetSchool": user.target_school,
        "direction": user.direction,
        "currentProgress": user.progress,
        "estimatedScore": user.estimated_score,
        "studyStyle": user.study_style,
        "undergradProvince": user.undergrad_province,
        "undergradSchool": user.undergrad_school,
        "undergradPrivate": user.undergrad_private,
        "avatar": user.avatar,
        "school": user.school,
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
        "isBanned": user.is_banned,
        "isWhitelist": user.is_whitelist,
        "isBanned": user.is_banned,
        "banExpireAt": user.ban_expire_at.isoformat() if user.ban_expire_at else None,
        "mutedUntil": user.muted_until.isoformat() if user.muted_until else None,
    }


@router.post("/check-dawang-id")
async def check_dawang(req: CheckDawangIdRequest, db: AsyncSession = Depends(get_db)):
    available = await check_dawang_id(db, req.dawang_id)
    return {"available": available}


@router.post("/register")
async def register(req: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    # Check IP ban
    if client_ip:
        from app.models.ipban import IpBan
        from sqlalchemy import select as sel
        ban = (await db.execute(sel(IpBan).where(IpBan.ip_address == client_ip))).scalar_one_or_none()
        if ban:
            raise HTTPException(status_code=403, detail=f"该IP地址已被封禁，无法注册。原因: {ban.reason or '违规行为'}")
    try:
        return await register_user(
            db,
            dawang_id=req.dawang_id,
            nickname=req.nickname,
            username=req.username,
            password=req.password,
            phone=req.phone,
            client_ip=client_ip,
            grade=req.grade,
            major=req.major,
            has_target=req.hasTarget,
            target_school=req.targetSchool,
            direction=req.direction,
            progress=req.currentProgress,
            estimated_score=req.estimatedScore,
            study_style=req.studyStyle,
            undergrad_province=req.undergradProvince,
            undergrad_school=req.undergradSchool,
            undergrad_private=req.undergradPrivate,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    try:
        return await login_user(db, req.username, req.password, client_ip)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/forgot-password")
async def reset_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        await forgot_password(db, req.phone, req.new_password)
        return {"message": "密码已重置"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/change-password")
async def change_pw(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await change_password(db, user.id, req.old_password, req.new_password)
        return {"message": "密码已修改"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/change-dawang-id")
async def change_did(
    req: ChangeDawangIdRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await change_dawang_id(db, user.id, req.new_dawang_id)
        return {"message": "大王号已修改"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return _me_payload(user)


@router.post("/debug-self")
async def debug_self_update(
    req: DebugSelfUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_whitelist:
        raise HTTPException(status_code=403, detail="仅白名单用户可使用测试修改")
    if req.vip_level is not None:
        user.vip_level = req.vip_level
        user.monthly_coins_max = VIP_MONTHLY_COINS.get(req.vip_level, user.monthly_coins_max or 100)
        if req.vip_level == 99:
            user.deep_think_enabled = True
    if req.deep_think_enabled is not None:
        user.deep_think_enabled = req.deep_think_enabled
    if req.monthly_coins is not None:
        user.monthly_coins = req.monthly_coins
    else:
        user.monthly_coins = max(0, (user.monthly_coins or 0) + req.monthly_coins_delta)
    if req.purchased_coins is not None:
        user.purchased_coins = req.purchased_coins
    else:
        user.purchased_coins = max(0, (user.purchased_coins or 0) + req.purchased_coins_delta)
    user.xp = max(0, (user.xp or 0) + req.xp_delta)
    user.level = get_level_info(user.xp)["level"]
    await db.commit()
    await db.refresh(user)
    return _me_payload(user)


@router.get("/user/{user_id}/profile")
async def get_user_public_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    """获取用户公开主页"""
    from sqlalchemy import select as sel
    from app.models.post import Post as P
    u = await db.get(User, user_id)
    if not u or u.is_banned:
        raise HTTPException(404, "用户不存在")
    posts = (await db.execute(
        sel(P).where(P.user_id == user_id, P.visibility == "public").order_by(P.created_at.desc()).limit(20)
    )).scalars().all()
    from app.services.xp_service import get_title
    return {
        "id": u.id,
        "nickname": u.nickname,
        "username": u.username,
        "dawangId": u.dawang_id,
        "level": u.level or 1,
        "xp": u.xp or 0,
        "levelTitle": get_title(u.xp or 0),
        "vipLevel": u.vip_level or 0,
        "isWhitelist": u.is_whitelist or False,
        "school": u.school,
        "targetSchool": u.target_school if not u.undergrad_private else None,
        "major": u.major,
        "undergradSchool": u.undergrad_school if not u.undergrad_private else None,
        "undergradProvince": u.undergrad_province if not u.undergrad_private else None,
        "pomodoroCount": u.pomodoro_count or 0,
        "signInStreak": u.sign_in_streak or 0,
        "posts": [{
            "id": p.id, "content": p.content, "likesCount": p.likes_count,
            "createdAt": p.created_at.isoformat() if p.created_at else None,
        } for p in posts],
    }


@router.put("/set-target")
async def set_target_school(
    req: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """设置目标院校和专业"""
    school_name = (req.get("target_school") or "").strip()
    major = (req.get("major") or "").strip()
    if school_name:
        user.target_school = school_name
        user.has_target = True
    if major:
        user.major = major
    await db.commit()
    return {"success": True, "targetSchool": user.target_school, "major": user.major, "hasTarget": user.has_target}


@router.post("/confirm-admitted")
async def confirm_admitted(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if (user.vip_level or 0) != 99:
        raise HTTPException(status_code=400, detail="仅研王爷用户可以确认上岸")
    user.vip_level = 17
    user.monthly_coins = VIP_MONTHLY_COINS[0]
    user.monthly_coins_max = VIP_MONTHLY_COINS[0]
    user.deep_think_enabled = False
    await db.commit()
    return {"success": True, "vipLevel": user.vip_level, "message": "已确认上岸"}


@router.get("/ai-summary")
async def get_ai_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.ai_profile import AiUserProfile

    result = await db.execute(select(AiUserProfile).where(AiUserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        return {"summary": None, "tags": [], "recommendedSchools": []}
    return {
        "summary": profile.summary,
        "tags": profile.tags.split(",") if profile.tags else [],
        "recommendedSchools": profile.recommended_schools.split(",") if profile.recommended_schools else [],
    }


@router.post("/ai-summary")
async def generate_ai_summary(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.ai_profile import AiUserProfile
    from app.services.chat_service import chat as llm_chat

    info_parts = []
    if user.grade:
        info_parts.append(f"年级: {user.grade}")
    if user.major:
        info_parts.append(f"专业: {user.major}")
    if user.has_target and user.target_school:
        info_parts.append(f"目标: {user.target_school}")
    if user.direction:
        info_parts.append(f"考研方向: {user.direction}")
    if user.progress:
        info_parts.append(f"当前进度: {user.progress}")
    if user.estimated_score:
        info_parts.append(f"预估水平: {user.estimated_score}")
    if user.study_style:
        info_parts.append(f"备考风格: {user.study_style}")

    prompt = f"""请根据以下考研用户信息，给出简短分析（100字内）：
{'; '.join(info_parts)}

请输出JSON格式：{{"summary": "用户画像总结", "tags": ["标签1","标签2","标签3"], "recommended_schools": ["推荐院校1","推荐院校2"]}}"""

    try:
        reply = await llm_chat([], prompt)
        start = reply.find("{")
        end = reply.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(reply[start:end])
        else:
            data = {"summary": reply[:100], "tags": [], "recommended_schools": []}
    except Exception:
        data = {"summary": "AI分析暂不可用", "tags": [], "recommended_schools": []}

    result = await db.execute(select(AiUserProfile).where(AiUserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile:
        profile.summary = data.get("summary", "")
        profile.tags = ",".join(data.get("tags", []))
        profile.recommended_schools = ",".join(data.get("recommended_schools", []))
    else:
        db.add(
            AiUserProfile(
                user_id=user.id,
                summary=data.get("summary", ""),
                tags=",".join(data.get("tags", [])),
                recommended_schools=",".join(data.get("recommended_schools", [])),
            )
        )
    await db.commit()
    return data
