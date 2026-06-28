"""AI chat routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.chat import ChatMessage
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.chat_service import chat
from app.services.coins_service import consume_coins, ensure_coins_reset, estimate_cost, get_available_coins

router = APIRouter(prefix="/chat", tags=["AI 陪聊"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] | None = None
    deep_think: bool = False


class ChatResponse(BaseModel):
    reply: str
    coins_used: int
    coins_remaining: int
    monthly_remaining: int
    purchased_remaining: int


class HistoryItem(BaseModel):
    role: str
    content: str
    createdAt: str | None = None


@router.post("/send", response_model=ChatResponse)
async def send_message(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(40)
    )
    history = result.scalars().all()
    history_dicts = [{"role": h.role, "content": h.content} for h in history]
    history_length = sum(len(h["content"]) for h in history_dicts)

    await ensure_coins_reset(db, user)
    deep_think = bool(req.deep_think and user.deep_think_enabled)
    if req.deep_think and not deep_think:
        raise HTTPException(status_code=403, detail="深度思考模式仅研王爷可用")

    cost = estimate_cost(req.message, history_length, deep_think)
    coins = await get_available_coins(user)
    if coins["total_coins"] < cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "研AI币不足",
                "monthly_coins": coins["monthly_coins"],
                "purchased_coins": coins["purchased_coins"],
                "cost": cost,
                "message": "研AI币不足，请充值或等待下月重置。",
            },
        )

    try:
        reply = await chat(history_dicts, req.message)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")

    if not await consume_coins(db, user, cost):
        raise HTTPException(status_code=402, detail="研AI币不足")

    # Check token limit
    token_limit = user.token_limit or 0
    token_used = user.token_used or 0
    if token_limit > 0 and token_used >= token_limit:
        raise HTTPException(status_code=429, detail="API Token额度已用完，请联系管理员提升额度")

    db.add(ChatMessage(user_id=user.id, role="user", content=req.message))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply))
    tokens_used = len(req.message) + len(reply)
    user.token_used = (user.token_used or 0) + tokens_used
    await db.commit()

    coins_info = await get_available_coins(user)
    return {
        "reply": reply,
        "coins_used": cost,
        "coins_remaining": coins_info["total_coins"],
        "monthly_remaining": coins_info["monthly_coins"],
        "purchased_remaining": coins_info["purchased_coins"],
    }


@router.get("/coins/status")
async def coins_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ensure_coins_reset(db, user)
    return await get_available_coins(user)


@router.get("/history", response_model=list[HistoryItem])
async def get_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(100)
    )
    messages = result.scalars().all()
    return [
        {
            "role": m.role,
            "content": m.content,
            "createdAt": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.delete("/history")
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatMessage).where(ChatMessage.user_id == user.id))
    messages = result.scalars().all()
    for message in messages:
        await db.delete(message)
    await db.commit()
    return {"message": "聊天历史已清空"}
