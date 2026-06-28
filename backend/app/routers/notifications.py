"""Notification router - list, read, delete."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import UserNotification
from app.models.user import User
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/notifications", tags=["通知"])


async def create_notification(db: AsyncSession, user_id: str, type_: str, title: str, body: str, data: dict | None = None):
    """创建通知（供其他模块调用）"""
    notif = UserNotification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        data=json.dumps(data, ensure_ascii=False) if data else None,
    )
    db.add(notif)
    await db.commit()
    return notif


async def broadcast_announcement(db: AsyncSession, title: str, body: str, announcement_id: str = None):
    """向所有用户广播公告通知"""
    from sqlalchemy import select as sel
    users = (await db.execute(sel(User.id))).scalars().all()
    for uid in users:
        db.add(UserNotification(
            user_id=uid,
            type="announcement",
            title=title,
            body=body,
            data=json.dumps({"announcement_id": announcement_id}, ensure_ascii=False) if announcement_id else None,
        ))
    await db.commit()


@router.get("")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 30,
):
    """获取用户通知列表"""
    stmt = (
        select(UserNotification)
        .where(UserNotification.user_id == user.id, UserNotification.is_deleted == False)
        .order_by(UserNotification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    notifs = (await db.execute(stmt)).scalars().all()
    unread_count = (
        await db.execute(
            select(func.count()).select_from(UserNotification).where(
                UserNotification.user_id == user.id,
                UserNotification.is_read == False,
                UserNotification.is_deleted == False,
            )
        )
    ).scalar() or 0

    return {
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "data": json.loads(n.data) if n.data else None,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
        "unread_count": unread_count,
    }


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记单条通知为已读"""
    n = await db.get(UserNotification, notif_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404)
    n.is_read = True
    await db.commit()
    return {"success": True}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """标记所有通知为已读"""
    await db.execute(
        select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.is_read == False,
        )
    )
    notifs = (await db.execute(
        select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.is_read == False,
        )
    )).scalars().all()
    for n in notifs:
        n.is_read = True
    await db.commit()
    return {"success": True}


@router.delete("/{notif_id}")
async def delete_notification(
    notif_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """软删除通知"""
    n = await db.get(UserNotification, notif_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404)
    n.is_deleted = True
    await db.commit()
    return {"success": True}


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取未读通知数量"""
    count = (
        await db.execute(
            select(func.count()).select_from(UserNotification).where(
                UserNotification.user_id == user.id,
                UserNotification.is_read == False,
                UserNotification.is_deleted == False,
            )
        )
    ).scalar() or 0
    return {"unread_count": count}
