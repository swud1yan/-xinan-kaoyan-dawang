"""Phase 4 study partner matching APIs."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/match", tags=["Match"])


class MatchSettingsRequest(BaseModel):
    targetSchool: str | None = Field(None, max_length=100)
    major: str | None = Field(None, max_length=100)
    direction: str | None = Field(None, max_length=50)
    studyStyle: str | None = Field(None, max_length=20)


def _settings(user: User) -> dict:
    return {
        "targetSchool": user.target_school,
        "major": user.major,
        "direction": user.direction,
        "studyStyle": user.study_style,
    }


@router.get("/settings")
async def get_match_settings(user: User = Depends(get_current_user)):
    return _settings(user)


@router.put("/settings")
async def update_match_settings(
    req: MatchSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.targetSchool is not None:
        user.target_school = req.targetSchool
        user.has_target = bool(req.targetSchool)
    if req.major is not None:
        user.major = req.major
    if req.direction is not None:
        user.direction = req.direction
    if req.studyStyle is not None:
        user.study_style = req.studyStyle
    await db.commit()
    return _settings(user)


@router.get("/recommendations")
async def match_recommendations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    clauses = [User.id != user.id, User.is_banned == False]
    preference = []
    if user.target_school:
        preference.append(User.target_school == user.target_school)
    if user.major:
        preference.append(User.major == user.major)
    if user.direction:
        preference.append(User.direction == user.direction)
    if user.undergrad_school and not user.undergrad_private:
        preference.append(User.undergrad_school == user.undergrad_school)
    stmt = select(User).where(*clauses)
    if preference:
        stmt = stmt.where(or_(*preference))
    candidates = (await db.execute(stmt.order_by(User.level.desc(), User.xp.desc()).limit(30))).scalars().all()
    items = []
    for u in candidates:
        same = []
        source_parts = []
        if user.target_school and u.target_school == user.target_school:
            same.append("目标院校")
            source_parts.append(f"TA和你同样目标{u.target_school}")
        if user.major and u.major == user.major:
            same.append("专业")
            source_parts.append(f"TA和你同样目标{u.major}专业")
        if user.direction and u.direction == user.direction:
            same.append("方向")
        if user.study_style and u.study_style == user.study_style:
            same.append("学习节奏")
        if user.undergrad_school and u.undergrad_school == user.undergrad_school and not user.undergrad_private:
            same.append("校友")
            source_parts.append(f"TA和你同样是{user.undergrad_school}的校友")
        match_source = "、".join(source_parts[:2]) if source_parts else None
        score = 50 + len(same) * 12 + min((u.level or 1), 30) // 3
        items.append(
            {
                "userId": u.id,
                "nickname": u.nickname,
                "dawangId": u.dawang_id,
                "level": u.level or 1,
                "targetSchool": u.target_school,
                "major": u.major,
                "studyStyle": u.study_style,
                "matchSource": match_source,
                "matchScore": min(score, 98),
                "reasons": same or ["同在备考路上"],
            }
        )
    return {"items": items}
