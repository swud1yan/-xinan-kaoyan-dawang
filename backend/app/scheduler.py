"""Background scheduler jobs."""
import logging
from datetime import date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.score_line import ScoreLine
from app.models.user import User
from app.services.coins_service import VIP_MONTHLY_COINS

logger = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler()


async def refresh_score_lines_job():
    """Daily best-effort score-line refresh."""
    from app.services.scraper import scrape_all

    logger.info("score-line refresh started")
    try:
        new_data = await scrape_all()
        if not new_data:
            logger.info("score-line refresh finished: no new data")
            return
        async with AsyncSessionLocal() as session:
            for item in new_data:
                existing = await session.execute(
                    select(ScoreLine).where(
                        ScoreLine.school_name == item.get("school_name"),
                        ScoreLine.program_name == item.get("program_name"),
                        ScoreLine.year == item.get("year"),
                    )
                )
                if not existing.scalar_one_or_none():
                    session.add(ScoreLine(**item))
            await session.commit()
        logger.info("score-line refresh finished: %s candidate rows", len(new_data))
    except Exception as e:
        logger.exception("score-line refresh failed: %s", e)


async def monthly_coins_reset():
    """Reset monthly VIP coins on the first day of every month."""
    today = date.today()
    if today.day != 1:
        return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            max_coins = VIP_MONTHLY_COINS.get(user.vip_level or 0, VIP_MONTHLY_COINS[0])
            user.monthly_coins = max_coins
            user.monthly_coins_max = max_coins
            user.coins_reset_date = datetime.now()
        await session.commit()
    logger.info("monthly coins reset finished")


async def check_vip_expiry():
    """Downgrade expired monthly VIP users. Yanwang users do not auto-expire here."""
    now = datetime.now()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.vip_level.in_([1, 2, 3]),
                User.vip_expire_at.is_not(None),
                User.vip_expire_at < now,
            )
        )
        users = result.scalars().all()
        for user in users:
            user.vip_level = 0
            user.vip_expire_at = None
            user.monthly_coins_max = VIP_MONTHLY_COINS[0]
            user.monthly_coins = min(user.monthly_coins or 0, VIP_MONTHLY_COINS[0])
            user.deep_think_enabled = False
        await session.commit()
    if users:
        logger.info("vip expiry check downgraded %s users", len(users))


def init_scheduler():
    """Start background jobs."""
    scheduler.add_job(
        refresh_score_lines_job,
        trigger=CronTrigger(hour=2, minute=7),
        id="refresh_score_lines",
        name="score-line daily refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        monthly_coins_reset,
        trigger=CronTrigger(hour=0, minute=0),
        id="monthly_coins_reset",
        name="monthly coins reset",
        replace_existing=True,
    )
    scheduler.add_job(
        check_vip_expiry,
        trigger=CronTrigger(hour=0, minute=5),
        id="check_vip_expiry",
        name="vip expiry check",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started")


def shutdown_scheduler():
    """Shutdown background jobs."""
    scheduler.shutdown(wait=False)
    logger.info("scheduler stopped")
