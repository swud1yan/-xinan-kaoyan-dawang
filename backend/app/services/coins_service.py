"""Coins service - monthly and purchased coin accounting."""
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

VIP_MONTHLY_COINS = {0: 100, 1: 1500, 2: 5000, 3: 12000, 17: 100, 99: 20000}

COIN_PACKS = [
    {"id": "pack_100", "name": "100研AI币", "coins": 100, "price": 6.0},
    {"id": "pack_500", "name": "500研AI币", "coins": 500, "price": 24.0},
    {"id": "pack_1500", "name": "1500研AI币", "coins": 1500, "price": 58.0},
    {"id": "pack_5000", "name": "5000研AI币", "coins": 5000, "price": 148.0},
    {"id": "pack_12000", "name": "12000研AI币", "coins": 12000, "price": 288.0},
]

COIN_PACK_MAP = {pack["id"]: pack for pack in COIN_PACKS}


async def ensure_coins_reset(db: AsyncSession, user) -> None:
    today = date.today()
    reset_date = user.coins_reset_date
    if reset_date is None or reset_date.year < today.year or reset_date.month < today.month:
        max_coins = VIP_MONTHLY_COINS.get(user.vip_level or 0, 100)
        user.monthly_coins = max_coins
        user.monthly_coins_max = max_coins
        user.coins_reset_date = datetime.now()
        await db.commit()


async def get_available_coins(user) -> dict:
    monthly = user.monthly_coins or 0
    purchased = user.purchased_coins or 0
    return {
        "monthly_coins": monthly,
        "monthly_coins_max": user.monthly_coins_max or 100,
        "purchased_coins": purchased,
        "total_coins": monthly + purchased,
    }


async def consume_coins(db: AsyncSession, user, cost: int) -> bool:
    await ensure_coins_reset(db, user)
    monthly = user.monthly_coins or 0
    purchased = user.purchased_coins or 0
    if monthly + purchased < cost:
        return False
    if monthly >= cost:
        user.monthly_coins = monthly - cost
    else:
        user.monthly_coins = 0
        user.purchased_coins = purchased - (cost - monthly)
    await db.commit()
    return True


async def add_purchased_coins(db: AsyncSession, user, amount: int) -> None:
    user.purchased_coins = (user.purchased_coins or 0) + amount
    await db.commit()


def estimate_cost(user_message: str, history_length: int, deep_think: bool) -> int:
    if deep_think:
        return 3
    if len(user_message) > 500 or history_length > 3000:
        return 2
    return 1
