"""Public feedback submission and admin management pages."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ipban import UserFeedback
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/feedback", tags=["反馈"])


class FeedbackRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    contact: str = Field("", max_length=100)


@router.post("")
async def submit_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户提交反馈"""
    fb = UserFeedback(
        user_id=user.id,
        username=user.nickname or user.username,
        content=req.content,
        contact=req.contact or None,
    )
    db.add(fb)
    await db.commit()
    return {"success": True, "message": "反馈已提交，感谢你的建议！"}


@router.get("/my")
async def my_feedbacks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fbs = (await db.execute(
        select(UserFeedback).where(UserFeedback.user_id == user.id).order_by(UserFeedback.created_at.desc()).limit(20)
    )).scalars().all()
    return [{"id": f.id, "content": f.content, "status": f.status,
             "admin_note": f.admin_note, "created_at": f.created_at.isoformat() if f.created_at else None}
            for f in fbs]
