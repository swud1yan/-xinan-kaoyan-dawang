"""Flashcard APIs."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.phase2_5 import Flashcard, FlashcardDeck, UserCardProgress
from app.models.user import User
from app.routers.auth_utils import get_current_user
from app.services.coins_service import ensure_coins_reset, get_available_coins, consume_coins

router = APIRouter(tags=["记忆闪卡"])

SEED_DECKS = {
    "政治·马原核心概念": ("politics", [
        ("实践", "实践是人类能动地改造世界的社会性的物质活动。", "认识论核心概念"),
        ("矛盾普遍性", "矛盾存在于一切事物及其发展过程始终。", "辩证法"),
        ("真理标准", "实践是检验真理的唯一标准。", "认识论"),
    ]),
    "英语·高频词汇": ("english", [
        ("abundant", "adj. 大量的，充足的", "近义词 ample"),
        ("crucial", "adj. 至关重要的", "very important"),
        ("derive", "v. 获得；源自", "derive from"),
    ]),
}


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=4)


class CreateCardRequest(BaseModel):
    deck_id: str | None = None
    deck_name: str | None = Field(None, max_length=100)
    subject: str = Field(default="custom", max_length=20)
    front: str = Field(..., min_length=1)
    back: str = Field(..., min_length=1)
    hint: str | None = None


async def ensure_flashcard_seed(db: AsyncSession) -> None:
    count = (await db.execute(select(func.count()).select_from(FlashcardDeck))).scalar() or 0
    if count:
        return
    for deck_name, (subject, cards) in SEED_DECKS.items():
        deck = FlashcardDeck(name=deck_name, subject=subject, card_count=len(cards), is_official=True, is_public=True)
        db.add(deck)
        await db.flush()
        for idx, (front, back, hint) in enumerate(cards):
            db.add(Flashcard(deck_id=deck.id, front=front, back=back, hint=hint, order=idx))
    await db.commit()


@router.get("/flashcards/decks")
async def list_decks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_flashcard_seed(db)
    stmt = select(FlashcardDeck).where(
        (FlashcardDeck.is_official == True) | (FlashcardDeck.creator_id == user.id)  # noqa: E712
    )
    decks = list((await db.execute(stmt.order_by(FlashcardDeck.is_official.desc(), FlashcardDeck.created_at.asc()))).scalars().all())
    from datetime import date
    today = date.today()
    today_count = (await db.execute(
        select(func.count()).select_from(Flashcard).join(FlashcardDeck).where(
            FlashcardDeck.creator_id == user.id,
            FlashcardDeck.is_official == False,
            func.date(Flashcard.created_at) == today
        )
    )).scalar() or 0
    return {
        "items": [
            {
                "id": d.id, "name": d.name, "subject": d.subject, "cardCount": d.card_count,
                "isOfficial": d.is_official, "isPublic": d.is_public,
            }
            for d in decks
        ],
        "todayFree": today_count,
    }


@router.get("/flashcards/decks/{deck_id}/study")
async def get_study_queue(
    deck_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    await ensure_flashcard_seed(db)
    cards = list((await db.execute(select(Flashcard).where(Flashcard.deck_id == deck_id).order_by(Flashcard.order.asc()))).scalars().all())
    now = datetime.now()
    queue = []
    for card in cards:
        progress = (await db.execute(select(UserCardProgress).where(UserCardProgress.user_id == user.id, UserCardProgress.card_id == card.id))).scalar_one_or_none()
        if not progress or progress.next_review_at <= now:
            queue.append({
                "id": card.id,
                "front": card.front,
                "back": card.back,
                "hint": card.hint,
                "isNew": progress is None,
                "repetitions": progress.repetitions if progress else 0,
            })
        if len(queue) >= limit:
            break
    return {"items": queue, "count": len(queue)}


@router.post("/flashcards/cards/{card_id}/review")
async def review_card(
    card_id: str,
    req: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = await db.get(Flashcard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="卡片不存在")
    progress = (await db.execute(select(UserCardProgress).where(UserCardProgress.user_id == user.id, UserCardProgress.card_id == card.id))).scalar_one_or_none()
    if not progress:
        progress = UserCardProgress(user_id=user.id, card_id=card.id, next_review_at=datetime.now())
        db.add(progress)

    if req.rating <= 1:
        progress.repetitions = 0
        progress.interval = 1
    else:
        progress.repetitions = (progress.repetitions or 0) + 1
        if progress.repetitions == 1:
            progress.interval = 1
        elif progress.repetitions == 2:
            progress.interval = 3
        else:
            progress.interval = max(1, round((progress.interval or 1) * (progress.ease_factor or 2.5)))
        progress.ease_factor = max(1.3, (progress.ease_factor or 2.5) + (0.1 if req.rating >= 3 else -0.2))

    progress.last_rating = req.rating
    progress.last_reviewed_at = datetime.now()
    progress.next_review_at = datetime.now() + timedelta(days=progress.interval)
    progress.is_mastered = (progress.repetitions or 0) >= 5 and req.rating >= 3
    await db.commit()
    return {"nextReviewAt": progress.next_review_at.isoformat(), "interval": progress.interval, "isMastered": progress.is_mastered}


@router.post("/flashcards/cards")
async def create_card(
    req: CreateCardRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Count today's cards
    from datetime import date
    today = date.today()
    today_count = (await db.execute(
        select(func.count()).select_from(Flashcard).join(FlashcardDeck).where(
            FlashcardDeck.creator_id == user.id,
            FlashcardDeck.is_official == False,
            func.date(Flashcard.created_at) == today
        )
    )).scalar() or 0
    free_limit = 3
    if today_count >= free_limit:
        # Charge 1 coin
        from app.services.coins_service import consume_coins, get_available_coins
        await ensure_coins_reset(db, user)
        coins = await get_available_coins(user)
        if coins["total_coins"] < 1:
            raise HTTPException(status_code=402, detail="今日免费次数(3次)已用完，且研AI币不足，请充值")
        if not await consume_coins(db, user, 1):
            raise HTTPException(status_code=402, detail="研AI币不足")
    deck = await db.get(FlashcardDeck, req.deck_id) if req.deck_id else None
    if not deck:
        deck = FlashcardDeck(name=req.deck_name or "我的闪卡", subject=req.subject, card_count=0, is_official=False, creator_id=user.id, is_public=False)
        db.add(deck)
        await db.flush()
    if deck.creator_id and deck.creator_id != user.id:
        raise HTTPException(status_code=403, detail="不能向他人的卡组添加卡片")
    card = Flashcard(deck_id=deck.id, front=req.front, back=req.back, hint=req.hint, order=deck.card_count or 0)
    deck.card_count = (deck.card_count or 0) + 1
    db.add(card)
    await db.commit()
    return {"id": card.id, "deckId": deck.id}


@router.get("/flashcards/stats")
async def flashcard_stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = list((await db.execute(select(UserCardProgress).where(UserCardProgress.user_id == user.id))).scalars().all())
    return {
        "reviewed": len(rows),
        "mastered": sum(1 for r in rows if r.is_mastered),
        "due": sum(1 for r in rows if r.next_review_at <= datetime.now()),
    }
