"""
Shared auth dependency - avoids circular imports
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import get_user_by_id
from app.utils.security import decode_token
from app.models.user import User


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract current user from Bearer token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="账号已被封禁")
    return user
