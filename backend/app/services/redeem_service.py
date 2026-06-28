"""Redeem code service."""
import random
import string
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import VipOrder
from app.models.coins import RedeemCode, RedeemHistory
from app.services.coins_service import COIN_PACK_MAP, VIP_MONTHLY_COINS

VIP_PRICES = {1: 9.9, 2: 19.9, 3: 29.9, 99: 298.0}
VIP_NAMES = {1: "银卡月卡", 2: "金卡月卡", 3: "黑卡月卡", 99: "研王爷"}


def generate_code() -> str:
    p1 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"XNDW-{p1}-{p2}"


async def create_codes(db: AsyncSession, admin_id: str, product_type: str, count: int, **kwargs) -> list:
    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    codes = []
    for _ in range(count):
        code_text = generate_code()
        while (await db.execute(select(RedeemCode).where(RedeemCode.code == code_text))).scalar_one_or_none():
            code_text = generate_code()
        db.add(RedeemCode(code=code_text, product_type=product_type, created_by=admin_id, batch_id=batch_id, **kwargs))
        codes.append(code_text)
    await db.commit()
    return codes


async def redeem(db: AsyncSession, user, code_str: str) -> dict:
    normalized = code_str.upper().strip()
    result = await db.execute(select(RedeemCode).where(RedeemCode.code == normalized))
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("兑换码不存在")
    if code.is_used:
        raise ValueError("该兑换码已被使用")

    code.is_used = True
    code.used_by = user.id
    code.used_at = datetime.now()

    old_level = user.vip_level or 0
    order_amount = 0.0
    order_vip_level = 0

    if code.product_type == "coin_pack":
        pack = COIN_PACK_MAP.get(code.product_id or "")
        coins = code.coins or (pack["coins"] if pack else 0)
        product_name = pack["name"] if pack else f"{coins}研AI币"
        order_amount = float(pack["price"] if pack else 0.0)
        user.purchased_coins = (user.purchased_coins or 0) + coins
        payload = {
            "type": "coins",
            "coins_added": coins,
            "purchased_coins": user.purchased_coins,
        }
    else:
        new_level = code.vip_level or 1
        days = code.vip_days or 30
        now = datetime.now()
        start = user.vip_expire_at if user.vip_expire_at and user.vip_expire_at > now and old_level == new_level else now
        user.vip_level = new_level
        user.vip_expire_at = start + timedelta(days=days)
        user.monthly_coins = VIP_MONTHLY_COINS.get(new_level, 100)
        user.monthly_coins_max = VIP_MONTHLY_COINS.get(new_level, 100)
        user.coins_reset_date = datetime.now()
        user.deep_think_enabled = new_level == 99
        product_name = VIP_NAMES.get(new_level, f"VIP{new_level}")
        order_amount = VIP_PRICES.get(new_level, 0.0)
        order_vip_level = new_level
        payload = {
            "type": "vip",
            "vip_level": user.vip_level,
            "vip_expire_at": user.vip_expire_at.isoformat(),
            "monthly_coins": user.monthly_coins,
            "deep_think": user.deep_think_enabled,
        }

    db.add(
        RedeemHistory(
            user_id=user.id,
            code=normalized,
            product_type=code.product_type,
            product_name=product_name,
            coins_added=payload.get("coins_added", 0),
            vip_level_before=old_level,
            vip_level_after=user.vip_level or 0,
        )
    )
    db.add(
        VipOrder(
            user_id=user.id,
            vip_level=order_vip_level,
            amount=order_amount,
            payment_method="redeem_code",
            status="paid",
            expire_at=user.vip_expire_at,
        )
    )
    await db.commit()
    return payload
