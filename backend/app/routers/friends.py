"""
Friends and messaging router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.social import Friend, Message
from app.routers.auth_utils import get_current_user

router = APIRouter(prefix="/friends", tags=["好友"])


class FriendRequest(BaseModel):
    dawang_id: str = Field(..., min_length=4, max_length=15)


class SendMessage(BaseModel):
    friend_id: str
    content: str = Field(..., min_length=1, max_length=2000)


def _friend_badge(u: User) -> dict:
    from app.services.xp_service import get_title
    return {
        "friendId": u.id,
        "nickname": u.nickname, "dawangId": u.dawang_id,
        "avatar": u.avatar, "school": u.school,
        "vipLevel": u.vip_level or 0,
        "level": u.level or 1,
        "levelTitle": get_title(u.xp or 0),
        "isWhitelist": u.is_whitelist or False,
    }


@router.get("")
async def list_friends(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get friend list"""
    result = await db.execute(
        select(Friend).where(
            or_(Friend.user_id == user.id, Friend.friend_id == user.id),
            Friend.status == "accepted",
        )
    )
    friends = result.scalars().all()

    data = []
    for f in friends:
        fid = f.friend_id if f.user_id == user.id else f.user_id
        f_user = await db.get(User, fid)
        if f_user:
            data.append({"id": f.id, **_friend_badge(f_user)})
    return data


@router.get("/requests")
async def pending_requests(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get pending friend requests (incoming)"""
    result = await db.execute(
        select(Friend).where(
            Friend.friend_id == user.id, Friend.status == "pending"
        )
    )
    requests = result.scalars().all()
    data = []
    for f in requests:
        from_user = await db.get(User, f.user_id)
        if from_user:
            data.append({
                "id": f.id,
                "fromUser": {"nickname": from_user.nickname, "dawangId": from_user.dawang_id,
                             "avatar": from_user.avatar, "school": from_user.school},
                "createdAt": f.created_at.isoformat() if f.created_at else None,
            })
    return data


@router.post("/request")
async def send_request(req: FriendRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Send friend request by dawang_id"""
    if req.dawang_id == user.dawang_id:
        raise HTTPException(400, "不能添加自己为好友")

    target_result = await db.execute(select(User).where(User.dawang_id == req.dawang_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "未找到该大王号")

    # Check existing
    existing = await db.execute(
        select(Friend).where(
            or_(
                and_(Friend.user_id == user.id, Friend.friend_id == target.id),
                and_(Friend.user_id == target.id, Friend.friend_id == user.id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "已经是好友或已有待处理申请")

    friend = Friend(user_id=user.id, friend_id=target.id, status="pending")
    db.add(friend)
    return {"message": "好友申请已发送"}


@router.put("/{request_id}/accept")
async def accept_request(request_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Accept friend request"""
    result = await db.execute(
        select(Friend).where(Friend.id == request_id, Friend.friend_id == user.id,
                             Friend.status == "pending")
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "申请不存在")
    req.status = "accepted"
    return {"message": "已添加好友"}


@router.delete("/{request_id}")
async def remove_friend(request_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Remove friend or reject request"""
    result = await db.execute(
        select(Friend).where(
            Friend.id == request_id,
            or_(Friend.user_id == user.id, Friend.friend_id == user.id),
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(404, "记录不存在")
    await db.delete(req)
    return {"message": "已删除"}


@router.get("/search")
async def search_by_dawang_id(q: str, db: AsyncSession = Depends(get_db)):
    """Search user by dawang_id"""
    result = await db.execute(
        select(User).where(User.dawang_id == q, User.is_banned == False)
    )
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "未找到该大王号")
    return {
        "nickname": u.nickname, "dawangId": u.dawang_id,
        "avatar": u.avatar, "school": u.school,
        "targetSchool": u.target_school,
    }


@router.get("/messages/{friend_id}")
async def get_messages(
    friend_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chat history with a friend"""
    result = await db.execute(
        select(Message).where(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == friend_id),
                and_(Message.sender_id == friend_id, Message.receiver_id == user.id),
            )
        ).order_by(Message.created_at.asc()).limit(200)
    )
    msgs = result.scalars().all()
    # Get sender info for badges
    sender_ids = list(set(m.sender_id for m in msgs))
    sender_map = {}
    for sid in sender_ids:
        su = await db.get(User, sid)
        if su:
            from app.services.xp_service import get_title
            sender_map[sid] = {
                "nickname": su.nickname, "vipLevel": su.vip_level or 0,
                "level": su.level or 1, "levelTitle": get_title(su.xp or 0),
                "isWhitelist": su.is_whitelist or False,
            }
    return [{
        "id": m.id, "senderId": m.sender_id, "receiverId": m.receiver_id,
        "content": m.content, "read": m.read,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
        "senderBadge": sender_map.get(m.sender_id),
    } for m in msgs]
