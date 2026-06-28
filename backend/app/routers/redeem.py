"""Redeem code router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.coins import RedeemHistory
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.coins_service import COIN_PACKS
from app.services.redeem_service import redeem as do_redeem

router = APIRouter(prefix="/redeem", tags=["兑换"])


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=10, max_length=20)


@router.post("/use")
async def use_code(
    req: RedeemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await do_redeem(db, user, req.code)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RedeemHistory)
        .where(RedeemHistory.user_id == user.id)
        .order_by(RedeemHistory.created_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id,
            "code": r.code,
            "productType": r.product_type,
            "productName": r.product_name,
            "coinsAdded": r.coins_added,
            "vipLevelBefore": r.vip_level_before,
            "vipLevelAfter": r.vip_level_after,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/products")
async def products():
    return {
        "vip_plans": [
            {"id": "silver", "name": "银卡月卡", "vip_level": 1, "price": 9.9, "days": 30, "coins_per_month": 1500},
            {"id": "gold", "name": "金卡月卡", "vip_level": 2, "price": 19.9, "days": 30, "coins_per_month": 5000},
            {"id": "black", "name": "黑卡月卡", "vip_level": 3, "price": 29.9, "days": 30, "coins_per_month": 12000},
            {"id": "yanwang", "name": "研王爷", "vip_level": 99, "price": 298, "days": 730, "coins_per_month": 20000, "deep_think": True},
        ],
        "coin_packs": COIN_PACKS,
    }
